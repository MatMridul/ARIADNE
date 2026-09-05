# ARIA — Build Spec (microscopic)

> This is the implementation contract. A build session should be able to produce
> ARIA from this file with near-zero judgment calls. It implements
> [`adapter.md`](adapter.md). Where a choice is still open, this spec makes the
> smallest reasonable decision and marks it `[DECISION → DR]`.
>
> **Guiding philosophy: make the build model decide function bodies, not designs.**
> Every design, scope, and sequencing decision is made here (or in a DR) so the
> build session only implements — it never has to choose an architecture.
>
> **Stack:** Python 3.11+, **standard library only** for core logic. `pytest` for
> tests (dev dependency). `matplotlib` allowed **only** for the final frontier
> plot (isolated in `reporting/`). No graph DB, no ML framework, no LLM, no web
> framework. If you think you need one, stop and write a DR first.

---

## 1. Guiding rules for the build (read every turn)

1. **The graph must earn its place.** Every graph feature must enable a decision
   the non-relational baseline cannot make. If it doesn't, cut it.
2. **Observed vs. derived is sacred.** Raw transactions are observed. Node health,
   attribution, recovery estimates are derived and MUST carry `claim_type`,
   evidence, and confidence.
3. **The diagnoser never sees ground truth.** `diagnosis/` and `baseline/` code
   must never import from or read the simulator's injected-incident parameters.
   Ground truth is available ONLY to the evaluation harness for scoring.
4. **Determinism.** Everything is seeded. Same seed → same transactions → same
   results. The simulator takes a `seed`; the eval sweeps seeds for variance.
5. **Small, tested modules.** Each module in §3 gets a matching test file. No
   module over ~200 lines; split if it grows.
6. **Unknown > fabricated.** Never invent a number the simulator didn't produce.
7. **No cross-incident learning in v1 (hostile-review fix #6).** Each incident is
   diagnosed ONLY from its own window's observations. The diagnoser keeps NO state
   across incidents and does not adapt from past incidents' outcomes within a run.
   This closes the "feedback loop teaches itself the answer" hole: nothing ARIA
   sees about how an incident resolved is allowed to feed back into how it diagnoses
   the next one. (Adaptation/learning is explicitly Tier 3 / out of scope — SCOPE.md.)

---

## 2. Repository layout

```
ARIA/
├── README.md
├── docs/
│   ├── adapter.md              # the domain adapter (done)
│   ├── BUILD_SPEC.md           # this file
│   └── decisions/              # DRs
├── .kiro/steering/             # build-session guardrails (see steering files)
├── src/ariadne/
│   ├── __init__.py
│   ├── model/                  # the domain graph + entities (no reasoning)
│   │   ├── entities.py
│   │   └── graph.py
│   ├── simulator/              # ground-truth generator (honest adversary)
│   │   ├── config.py
│   │   ├── incidents.py
│   │   └── engine.py
│   ├── observe/                # aggregation of raw txns → window snapshots
│   │   └── aggregate.py
│   ├── diagnosis/              # ARIA's relational reasoning
│   │   ├── detect.py
│   │   └── attribute.py
│   ├── baseline/               # the fair non-relational alternative
│   │   └── independent.py
│   ├── decide/                 # action selection + bounded action model
│   │   ├── actions.py
│   │   └── policy.py
│   ├── eval/                   # the honest scoring harness (sees ground truth)
│   │   ├── scenarios.py
│   │   ├── metrics.py
│   │   └── run.py
│   └── reporting/
│       └── frontier.py         # the recovery-vs-risk plot (matplotlib)
└── tests/
    └── test_*.py               # one per module
```

## 3. Modules — data structures and function signatures

Types are given as dataclasses. Signatures are the contract; bodies are the build.

### 3.1 `model/entities.py`

```python
from dataclasses import dataclass, field
from enum import Enum

class Method(str, Enum):
    UPI = "upi"; CARD = "card"; NETBANKING = "netbanking"

class Health(str, Enum):
    HEALTHY = "healthy"; DEGRADED = "degraded"; DOWN = "down"

@dataclass(frozen=True)
class PSP:
    psp_id: str
    name: str

@dataclass(frozen=True)
class Bank:
    bank_id: str
    name: str
    role: str  # "issuer" | "acquirer"

@dataclass
class Transaction:
    txn_id: str
    timestamp: float
    method: Method
    psp_id: str
    bank_id: str
    amount: float
    success: bool
    failure_code: str | None   # None on success
    latency_ms: float
    cohort: str                # customer cohort label
    geography: str
```

### 3.2 `model/graph.py`

The graph is a plain dict-backed structure (stdlib only). It holds the *static*
topology (what routes to what); it does NOT hold health (health is derived).

```python
@dataclass
class PaymentGraph:
    psps: dict[str, PSP]
    banks: dict[str, Bank]
    # method -> list of (psp_id, routing_weight); mutable (reroute changes it)
    routing: dict[Method, list[tuple[str, float]]]
    # psp_id -> bank_id it settles via
    settles_via: dict[str, str]

    def banks_for_method(self, m: Method) -> set[str]: ...
    def psps_for_bank(self, bank_id: str) -> list[str]:
        """The shared-dependency lookup: which PSPs settle via this bank."""
    def shared_banks(self) -> dict[str, list[str]]:
        """bank_id -> PSPs, for banks used by >1 PSP. The load-bearing edge."""
    def reroute(self, m: Method, from_psp: str, to_psp: str) -> "PaymentGraph":
        """Return a NEW graph with routing weight moved. Immutable-style for rollback."""

def default_graph() -> PaymentGraph:
    """3 methods, 3 PSPs, 2 banks — bank_A shared by PSP-1 & PSP-2 (the shared
    dependency), bank_B used only by PSP-3.  [DECISION → DR-001: graph size]"""
```

### 3.3 `simulator/config.py`

```python
@dataclass
class SimConfig:
    seed: int
    n_windows: int = 20              # time windows in a run
    txns_per_window: int = 500
    base_success: dict[Method, float] = ...   # e.g. upi 0.97, card 0.95, nb 0.93
    noise_std: float = 0.01          # per-window jitter on success rate
    cohorts: tuple[str, ...] = ("new", "returning", "high_value")
    geographies: tuple[str, ...] = ("north", "south", "east", "west")
```

### 3.4 `simulator/incidents.py`

The four incident types. Each is a function that, given the base per-path success
rate, returns a *modified* success rate for the affected paths during the incident
window(s). Ground truth = which node was hit + when.

```python
class IncidentType(str, Enum):
    SHARED_BANK  = "A_shared_bank"       # hero / thesis test — one bank, many PSPs
    SINGLE_PSP   = "B_single_psp"        # control — no over-attribution
    METHOD       = "C_method"            # method-level fault
    NONE         = "D_ambiguous"         # noise dip, NO real cause
    COINCIDENTAL = "E_coincidental"      # TWO PSPs on DIFFERENT banks drop at the
                                         # same time by chance — correct answer is
                                         # TWO independent faults, NOT a shared cause

@dataclass
class Incident:
    incident_type: IncidentType
    target_id: str | None    # bank_id / psp_id / method / None for D
    # for COINCIDENTAL: two independent PSP targets, different banks
    secondary_target_id: str | None = None
    start_window: int = 0
    end_window: int = 0
    severity: float = 0.0    # drop applied to affected paths' success rate

@dataclass
class GroundTruth:
    """ONLY the eval harness may read this. diagnosis/ and baseline/ must not."""
    incident: Incident
    affected_psps: list[str]     # computed from the graph at injection time
    affected_methods: list[Method]
    # true root cause(s): one node for A/B/C; TWO independent PSPs for E; none for D
    true_causes: list[str]
```

> **Why incident E exists (hostile-review fix #2/#4):** without it, "blame the bank
> whenever ≥2 PSPs drop together" is a trivial failure-*counting* rule that wins
> with no real reasoning. E is the case where two PSPs drop together but sit on
> *different* banks — so the correct answer is two independent PSP faults. Only a
> system that actually reasons over the topology (not one that counts correlated
> failures) gets both A and E right. ARIA must distinguish A (one shared bank)
> from E (two coincidental independent faults); the baseline naturally treats both
> as independent PSP faults — so E is where ARIA must NOT over-attribute to a
> bank, the mirror of B.

### 3.5 `simulator/engine.py`

```python
def generate(graph: PaymentGraph, cfg: SimConfig,
             incident: Incident) -> tuple[list[Transaction], GroundTruth]:
    """Deterministic given cfg.seed. Produces per-window transactions with realistic
    noise; during [start_window, end_window] the injected incident lowers the
    success rate on exactly the paths it should affect (SHARED_BANK lowers ALL PSPs
    that settle via target bank → the correlated-failure signal). Returns the txn
    log the reasoner sees, plus GroundTruth the reasoner must NOT see."""
```

Honest-adversary requirements enforced here (hostile-review fixes #7/#8):
- Incident D applies only random noise (no target).
- **Incident onset window, duration, and severity are randomized per seed** within
  bounded ranges — there is no fixed schedule (e.g. never "always starts at window
  10") that a reasoner could learn as a tell.
- **Severity ranges overlap the noise band** for a fraction of cases, so some
  incidents are genuinely ambiguous and the honest answer is low-confidence /
  do_nothing.
- Base success rates vary by cohort/geography so a naive "everything dropped"
  reading is wrong.
- For COINCIDENTAL (E), the two PSP faults are drawn independently (independent
  onset/severity) so they are not secretly synchronized in a way a counter could
  exploit.

### 3.6 `observe/aggregate.py`

```python
@dataclass
class NodeStats:
    node_id: str
    node_kind: str       # "psp" | "method" | "bank(derived)"
    success_rate: float
    volume: int
    avg_latency_ms: float
    baseline_rate: float # rolling historical baseline
    delta: float         # success_rate - baseline_rate

def window_stats(txns: list[Transaction], graph: PaymentGraph,
                 window: int) -> dict[str, NodeStats]:
    """Aggregate one window into per-PSP and per-method stats (both ARIA and the
    baseline get these). Bank-level stats are DERIVED by ARIA only, in diagnosis."""
```

> **Identical raw inputs (hostile-review fix #3).** ARIA and the baseline receive
> the *exact same* `NodeStats` for PSPs and methods — the same rates, baselines,
> latency, and volume. ARIA's bank-level health is **computed by ARIA from
> those same PSP-level inputs** via the graph; it is NOT an extra observation handed
> to ARIA and withheld from the baseline. The only difference between the two
> systems is that ARIA holds the dependency graph and the baseline does not. No
> other input differs. This is what keeps the comparison a clean controlled
> experiment — relational reasoning vs. independent monitoring, nothing else.

### 3.7 `diagnosis/detect.py`

```python
@dataclass
class Detection:
    triggered: bool
    dropped_nodes: list[str]   # nodes whose delta breaches the detection threshold
    window: int

def detect(stats: dict[str, NodeStats], detect_threshold: float) -> Detection:
    """Deterministic threshold on delta vs. baseline. Shared by ARIA and baseline."""
```

### 3.8 `diagnosis/attribute.py` — the core relational reasoning

```python
@dataclass
class Attribution:
    root_cause_id: str          # the node ARIA blames (may be a bank)
    root_cause_kind: str        # "bank" | "psp" | "method" | "none"
    confidence: float           # 0..1
    evidence_path: list[str]    # the observations/edges supporting it
    claim_type: str = "hypothesis"

def attribute(stats, graph: PaymentGraph, detection: Detection) -> Attribution:
    """For each candidate upstream node (incl. DERIVED bank health from the PSPs that
    settle via it), score how well 'this ONE shared node is unhealthy' explains the
    observed failure pattern versus 'these PSPs are independently unhealthy'.

    Shared-cause score — CONCRETE FORM [DECISION → DR-001, pinned so the build
    does not invent it]. Let the "down set" D = PSPs whose delta breaches the
    detect threshold. For each bank X with PSP-set P(X) from graph.psps_for_bank(X):
      - coverage(X)   = |D ∩ P(X)| / |P(X)|   (of X's PSPs, how many are down)
      - specificity(X)= 1 − (|D − P(X)| / |D|) (of the down PSPs, how many are X's)
      A bank is a strong shared-cause candidate when coverage(X) = 1.0 (ALL its PSPs
      down) AND specificity(X) is high (down PSPs don't spill onto other banks).

    Decision rule:
      - Best bank has coverage == 1.0 AND specificity >= S_MIN → blame the BANK.
        confidence = coverage(X) * specificity(X)              (both in 0..1)
      - Else if exactly the down PSPs each sit on DIFFERENT banks (no bank has
        coverage 1.0 with >1 PSP) → blame each down PSP INDEPENDENTLY (incident E /
        B case). confidence = mean per-PSP delta magnitude normalized to 0..1.
      - Else if a single method is down across PSPs → blame the METHOD.
      - Else (nothing breaches, or fits noise) → root_cause_kind 'none',
        confidence = 0 (drives do_nothing).

    S_MIN is a named constant (start 0.8) [DECISION → DR-001]. This formula is the
    thing that separates A (one bank, coverage 1.0, high specificity) from E (two
    PSPs on different banks — NO bank reaches coverage 1.0 with >1 PSP, so they are
    correctly blamed independently). Confidence is therefore a real, bounded number,
    not a hand-wave. Returns an evidence path naming the transactions/edges used."""
```

### 3.9 `baseline/independent.py` — the fair non-relational alternative

```python
def baseline_attribute(stats, detect_threshold: float) -> Attribution:
    """Strongest reasonable NON-relational diagnoser. Sees the SAME per-PSP and
    per-method NodeStats (rates, baselines, latency, volume). Has NO graph: cannot
    know two PSPs share a bank. Blames each independently-dropped node on ITSELF.
    On a shared-bank incident it therefore reports several independent PSP faults
    (root_cause_kind 'psp', possibly several) rather than one bank — this is exactly
    the discrimination gap the thesis tests. Must be a genuine best-effort monitor,
    NOT a strawman: it uses baselines and thresholds competently."""
```

### 3.10 `decide/actions.py`

```python
@dataclass
class Action:
    kind: str   # "reroute" | "disable_method" | "retry_fallback" | "do_nothing"
    params: dict
    decision_id: str
    evidence_path: list[str]
    confidence: float
    expected_recovery: float

# Each builder validates its bounds (adapter §6) and refuses out-of-bounds actions.
def reroute(...) -> Action: ...
def disable_method(...) -> Action: ...
def retry_fallback(...) -> Action: ...
def do_nothing(reason: str, confidence: float) -> Action: ...
```

### 3.11 `decide/policy.py`

```python
def select_action(attr: Attribution, graph: PaymentGraph, stats,
                  intervention_threshold: float) -> Action:
    """If attr.confidence < intervention_threshold → do_nothing (the safety default).
    Else choose the bounded action with best expected_recovery for the diagnosed
    cause (reroute traffic away from the bad node to a healthy sibling; disable a
    method only if a fault is method-level and a fallback exists; never disable the
    last working method; never reroute onto a node the graph shows is also bad).
    The intervention_threshold is the risk-appetite dial — NOT hardcoded."""
```

### 3.12 `eval/scenarios.py`

```python
def scenario_batch(seed: int) -> list[tuple[Incident, SimConfig]]:
    """A reproducible batch mixing all FIVE incident types (A shared-bank,
    B single-PSP, C method, D noise/no-cause, E coincidental-different-banks) plus
    clean windows, so 'money recovered across a batch' (Track 03 bar) is measurable
    and both do-nothing (D) and don't-over-attribute (B, E) behaviors are exercised.
    Onset/duration/severity randomized per seed (see engine)."""
```

### 3.13 `eval/metrics.py`

```python
@dataclass
class RunMetrics:
    detection_precision: float; detection_recall: float; detection_latency: float
    root_cause_accuracy: float       # vs GroundTruth
    path_accuracy: float
    calibration_error: float
    money_recovered: float           # realized, post-intervention
    expected_vs_realized_gap: float
    false_intervention_cost: float   # acted when it shouldn't have (esp. incident D)
    unsafe_action_rate: float
    do_nothing_correct_rate: float   # headline safety number (incident D)
```

`money_recovered` is computed by re-simulating the affected windows under the
chosen action's changed config and comparing captured revenue to the no-action
counterfactual — both against the same ground-truth incident.

> **Shared-seed counterfactual (hostile-review fix #5 — mandatory).** The
> action-applied re-simulation and the no-action counterfactual MUST use the
> **same seed and therefore the same underlying demand and per-transaction failure
> draws**, differing ONLY in the routing/method config the action changed. This
> isolates the action's true causal effect; if the two runs used different random
> draws, `money_recovered` would include random noise and a useless action could
> show phantom recovery. `money_recovered = revenue(action, seed=k) −
> revenue(no_action, seed=k)` for the same k. A negative value is legal and must be
> reported (an action that made things worse).

### 3.14 `eval/run.py` — the harness (the ONLY place ground truth is read)

```python
def run_once(system: str, intervention_threshold: float,
             seed: int) -> RunMetrics:
    """system in {"ariadne", "baseline"}. Runs the batch, drives detect→attribute→
    decide→(re-simulate outcome)→score. Reads GroundTruth ONLY for scoring."""

def run_sweep(seeds: list[int],
              thresholds: list[float] = (0.55, 0.70, 0.85)) -> dict:
    """Runs BOTH systems across all thresholds and seeds. Produces:
      1. The Shared Dependency Discrimination result: ariadne vs baseline on
         incident A (must show measurable improvement) AND on incident B (must not
         regress).
      2. The recovery-vs-false-intervention-cost frontier per system across
         thresholds (fed to reporting/frontier.py)."""
```

### 3.15 `reporting/frontier.py`

```python
def plot_frontier(sweep_result: dict, out_path: str) -> None:
    """Scatter/line: x = false_intervention_cost, y = money_recovered, one point per
    threshold, one series for ariadne and one for baseline. Saves PNG. The headline
    figure: 'here is the recovery-vs-risk frontier; the merchant chooses.'"""
```

## 4. The loop (how the pieces connect)

```
simulator.generate → observe.aggregate → diagnosis.detect
   → diagnosis.attribute (ARIA)  |  baseline.baseline_attribute (baseline)
   → decide.select_action (uses intervention_threshold)
   → simulator re-run affected windows under the action → observe outcome
   → eval.metrics (scored against GroundTruth)
   → eval.run_sweep aggregates → reporting.frontier
```

## 5. Tests (minimum bar — one file per module)

- `test_graph.py`: `psps_for_bank` / `shared_banks` return the shared PSPs correctly.
- `test_simulator.py`: same seed → identical txns; a SHARED_BANK incident actually
  lowers success across all PSPs on that bank and nowhere else.
- `test_attribute.py`: **the thesis test in miniature** — on a synthetic
  shared-bank window ARIA returns `root_cause_kind == "bank"`; on a single-PSP
  window it returns `"psp"` (no over-attribution); on a noise window it returns
  `"none"`; **on a COINCIDENTAL window (two PSPs on different banks down together)
  it returns two INDEPENDENT PSP causes, NOT a bank** — proving ARIA reasons over
  topology rather than merely counting correlated failures.
- `test_baseline.py`: on the same shared-bank window the baseline returns multiple
  independent PSP faults (never a bank) — proving the discrimination gap exists;
  on the coincidental window the baseline is CORRECT (independent PSPs), so the
  A-vs-E contrast is exactly what isolates ARIA's real advantage.
- `test_policy.py`: below threshold → do_nothing; never disables the last method;
  never reroutes onto a bad node.
- `test_metrics.py`: money_recovered and false_intervention_cost compute correctly
  on a hand-built fixture.
- `test_run.py`: `run_sweep` produces the A-improvement + B-no-regression result
  and a frontier with one point per threshold.

## 6. Definition of done (maps to ATLAS INSTANTIATION_GUIDE)

- [ ] Graph models entities + typed relationships + provenance; health is derived.
- [ ] Multi-hop attribution works (bank blamed via its PSPs, not a single lookup).
- [ ] Reasoning results carry evidence, confidence, claim_type.
- [ ] Every action is bounded, audited, stoppable; do_nothing is first-class.
- [ ] Full loop evaluated with ground truth incl. safety metrics.
- [ ] Shared Dependency Discrimination Test passes OR is honestly reported as
      not-supported (either is a valid result).
- [ ] The recovery-vs-risk frontier plot is produced.
- [ ] Material design choices recorded as DRs (graph size, attribution math,
      baseline-also-acts).
- [ ] Value demonstrably comes from the modeled relationships, not from an
      anomaly detector that ignores them.

## 7. Open decisions carried into DRs

- **DR-001 (ARIA design):** graph size (3/3/2), exact attribution scoring form,
  and whether the baseline also acts (recommended: yes, for apples-to-apples
  money-recovered).
- **DR-002 (ATLAS class):** promote the Shared Dependency Discrimination Test into
  the ATLAS class evaluation principles.
