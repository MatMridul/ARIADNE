# ARIA

**Adaptive Revenue Intelligence & Action** — an [ATLAS-class](https://github.com/MatMridul/ATLAS) system for payment revenue recovery.

> **Status: built, tested, and evaluated end-to-end.** The Shared Dependency
> Discrimination result and the recovery-vs-risk frontier are reproduced under
> `reports/`. A topology-ingestion boundary (Connect) maps a merchant's payment
> infrastructure into the graph, and an operator web console (Command Center, live
> payment topology, incident/RCA, evaluation, audit) runs on top of the same engine.
> 74 automated tests pass (62 core + 12 ingestion).

---

## What ARIA is

ARIA is a payment infrastructure intelligence system that **maps payment
dependencies, observes degradation, traces failures to their underlying causes,
executes bounded recovery actions, and measures recovered revenue.** It models a
merchant's payment ecosystem as a dependency graph (method → PSP → bank) and, when
revenue is at risk, traces the failure back through that graph to its root cause and
out to a bounded recovery action — with per-edge evidence, confidence, and an audit
trail.

The loop:

```
simulate → aggregate → detect → attribute → decide → re-simulate outcome → score
```

## The operator experience

ARIA ships an operator web console (a financial-systems instrument, not a generic
dashboard) on top of the same engine. Its surfaces:

- **Connect** — a topology-ingestion front door: paste/validate a payment-topology
  manifest (methods, PSPs, banks, and method→PSP→bank routes); ARIA validates it and
  normalizes it into its dependency graph, surfacing detected shared dependencies.
- **Command Center** — the living payment network as the primary object: watch
  degradation propagate, the shared bank light up as root cause with evidence and
  confidence, a bounded recovery action, and the measured outcome, along a
  DETECTED → DIAGNOSED → INTERVENTION → RECOVERED sequence.
- **Topology** — the full dependency graph with per-window playback of an incident.
- **Incidents & RCA** — the incident story: degradation → shared-dependency reasoning
  → attribution → recovery console → measured outcome.
- **Evaluation** — ARIA vs the graph-blind baseline: the discrimination result, the
  recovery-vs-risk frontier, safety metrics, and per-seed variance (honest, no
  cherry-picking).
- **Audit** — every action's decision id, evidence path, and confidence
  (derived-from-run; window index, not wall-clock).

The CLI/eval path is the engineering interface; the web console is the operator
interface. Both run on the same deterministic core.

## The thesis (and how it is tested)

> Does explicitly modeling the interconnected payment ecosystem let a system diagnose
> and recover revenue better than treating every component independently?

ARIA is compared against a **fair graph-blind baseline** that sees the exact same
per-PSP/per-method observations but lacks the dependency graph. The falsifiable test
is the **shared-bank incident (A)**: two PSPs settle via one bank, so a bank fault
surfaces as correlated PSP failures. ARIA derives bank health from the PSP
observations via the graph; the baseline can only see independent PSP faults.

Incident **E (coincidental)** — two PSPs on *different* banks failing together — is
the anti-triviality control: the correct answer there is two independent faults, so a
system that merely *counts* correlated failures fails E. Passing both A and E proves
ARIA reasons over topology, not correlation.

**Headline result** (`reports/run_report.md`):

| Incident | Metric | ARIA | Baseline |
|----------|--------|------|----------|
| A shared-bank | root-cause accuracy | **~0.94** | 0.00 |
| A shared-bank | money recovered | **higher** | lower |
| B single-PSP  | root-cause accuracy | matches baseline (no regression) | — |
| E coincidental| root-cause accuracy | matches baseline (no over-attribution) | — |

The recovery-vs-risk frontier (`reports/frontier.png`) plots money recovered vs.
false-intervention cost across intervention thresholds 0.55 / 0.70 / 0.85 for both
systems — the merchant chooses how aggressive ARIA should be.

## Why the decision path is deterministic (not an LLM)

The money-moving decision path — detection, attribution, action selection — is a
**deterministic scoring function over the graph, not an LLM.** This is a deliberate
design choice for **reproducibility** (same seed → identical results), **explainability**
(every attribution carries a verbatim evidence path: `coverage × specificity`),
**safety** (bounded, auditable actions with a `do_nothing` default), and **honest
evaluation** (the discrimination result is measured, not asserted). A natural-language
layer could sit *on top* to explain the system, but it does not replace the reasoning.

## The DR-002 failure-and-recovery story

An acceptance audit found the attribution engine could **mis-route incident E to a
"method" fault** ~93% of the time — a bug that would have quietly broken the
anti-triviality guard the whole thesis depends on. The fix (recorded in
[`docs/decisions/DR-002`](docs/decisions/DR-002-attribution-branch-disambiguation.md))
added a **method-concentration gate**: a method explanation is only preferred when
failure is concentrated in one method, whereas independent-PSP faults spread evenly.
The threshold (`0.06`) was then **validated on held-out seeds 26–55** — disjoint from
both the seeds that chose it (1–25) and the evaluation seeds (1–20): 0/12
E-misattribution out-of-sample, a clean separating gap, and the A-win/E-tie thesis
preserved. DR-002 is Accepted with that held-out evidence recorded honestly.

## Design invariants (enforced, not aspirational)

- **Python 3.11 standard library only** for core logic. `pytest` (dev) and
  `matplotlib` (only in `reporting/`) are the sole exceptions.
- **The diagnoser never sees ground truth.** `diagnosis/` and `baseline/` import
  nothing from `simulator/`; only `eval/` reads `GroundTruth`.
- **Identical raw inputs.** ARIA and the baseline receive the same PSP/method stats;
  ARIA's bank health is *derived* via the graph, never handed in.
- **Shared-seed counterfactual.** `money_recovered = revenue(action) − revenue(no_action)`
  under the same seed/draws; only the config differs. Negative values are legal and reported.
- **Attribution confidence = coverage × specificity, S_MIN = 0.8** (pinned, DR-001).
- **No cross-incident learning.** Each incident is diagnosed from its own window only.
- **Determinism.** Same seed → identical results.

Recovery amounts and the payment environment are **simulated**; recovery is measured
as a **shared-seed counterfactual**, not real money moved. There is no production
deployment, live merchant integration, or external database — the system runs
in-process against a deterministic simulator.

## Architecture: ATLAS → ARIA

**ATLAS** is the reusable system *class* (the architectural thesis: relational
reasoning over a dependency graph with evidence, bounded action, and honest
evaluation). **ARIA** is the concrete product *instantiation* of that class for the
payment revenue-recovery domain. ATLAS provides the pattern; ARIA is the application.

## Layout

```
src/ariadne/        Python core (package name retained as a technical identifier)
  model/            entities + PaymentGraph (static topology; health is derived) + manifest ingestion
  simulator/        honest-adversary generator (the ONLY holder of ground truth)
  observe/          raw txns → per-window NodeStats
  diagnosis/        ARIA's relational attribution (detect + attribute)
  baseline/         the fair graph-blind monitor (no graph)
  decide/           bounded actions + policy (reroute / disable_method / retry_fallback / do_nothing)
  eval/             the scoring harness (reads ground truth) + scenarios + sweep + cache
  reporting/        the recovery-vs-risk frontier plot (matplotlib, isolated)
web/                operator web console (Vite + React + TS) + thin FastAPI over the core
  api/              FastAPI: /api/topology, /api/topology/import, /api/simulate, /api/evaluation, /api/incidents, /api/audit
  src/              onboarding (Connect) · shell · topology graph · incident/RCA · evaluation · design system · lib (typed client)
```

> The Python package is named `ariadne` — a **technical identifier** kept stable to
> avoid breaking imports and the API contract. The public product name is **ARIA**.

## Running

### Core: tests + evaluation
```bash
# tests (stdlib + pytest only)
python -m pytest -q

# reproduce the discrimination result + frontier (needs matplotlib)
python -c "import sys; sys.path.insert(0,'src'); \
from ariadne.eval.sweep import run_sweep; \
from ariadne.reporting.frontier import plot_frontier, write_report; \
r=run_sweep(seeds=[1,2,3,4,5]); plot_frontier(r,'reports/frontier.png'); write_report(r,'reports/run_report.md')"
```

### Web console
```bash
pip install -e . ; pip install fastapi "uvicorn[standard]"
cd web ; npm install ; npm run build ; cd ..
python -m uvicorn web.api.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

**Canonical demo:** incident `A_shared_bank`, seed `7`. ARIA attributes the shared
bank (`bank_A`) with confidence 1.0 and recommends a bounded reroute; the graph-blind
baseline blames individual PSPs from the identical observations — the thesis made
visible.

## Governance

Design decisions are recorded under [`docs/decisions/`](docs/decisions/) (two-pass
Proposed→closed, immutable history). The build contract is in
[`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md); the domain model in
[`docs/adapter.md`](docs/adapter.md); scope tiers in [`docs/SCOPE.md`](docs/SCOPE.md).

## License

Deferred.
