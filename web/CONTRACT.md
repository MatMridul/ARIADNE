# ARIADNE — Web API Contract

> **Status:** Design (F0 output). Implement exactly this in a thin FastAPI app
> (`web/api/`, not yet scaffolded). The API is a **serialization boundary only**:
> it calls the existing core and reshapes its output to JSON. It must not add
> domain logic (vision §16).
>
> **Source of truth for every field:** the functions in `src/ariadne/`. Each field
> below cites the exact producer. Fields that the current backend does **not**
> produce are called out in **⚠️ NOT-BACKABLE** / **⚠️ DERIVED** notes so downstream
> agents never render fabricated numbers (vision §20).

## Conventions
- Base path `/api`. JSON only. All money is in rupees (float), matching
  `SimConfig.avg_amount` units.
- Errors: `{ "error": string, "detail": string }` with a 4xx/5xx status.
- Determinism: identical request bodies return identical responses (the core is
  seed-deterministic). Safe to cache by request hash.
- The core entry points wrapped: `default_graph()` (`model/graph.py`),
  `run_once(...)` (`eval/run.py`), `discrimination_result(...)` / `run_sweep(...)`
  (`eval/sweep.py`), `window_stats(...)` (`observe/aggregate.py`),
  `detect(...)` (`diagnosis/detect.py`), `attribute(...)` (`diagnosis/attribute.py`),
  `select_action(...)` (`decide/policy.py`), `money_recovered(...)` (`eval/metrics.py`).

## Incident type enum (shared by all endpoints)
Maps 1:1 to `IncidentType` in `simulator/incidents.py` (value → meaning):

| API `incident_type` | enum value | Meaning |
|---|---|---|
| `A_shared_bank` | `SHARED_BANK` | One bank down, multiple PSPs affected (thesis / hero) |
| `B_single_psp` | `SINGLE_PSP` | One PSP down — control, no over-attribution to bank |
| `C_method` | `METHOD` | One payment method down across PSPs |
| `D_ambiguous` | `NONE` | Noise dip, NO real cause → correct answer is do_nothing |
| `E_coincidental` | `COINCIDENTAL` | Two PSPs on **different** banks drop by chance (anti-triviality) |

---

## `GET /api/topology`
Static 3/3/2 dependency graph. Wraps `default_graph()`.

**Response**
```json
{
  "merchant": { "id": "merchant", "label": "Merchant" },
  "methods": [
    { "id": "upi", "label": "UPI" },
    { "id": "card", "label": "Card" },
    { "id": "netbanking", "label": "Netbanking" }
  ],
  "psps": [
    { "id": "psp_1", "label": "PSP-1", "bank_id": "bank_A" },
    { "id": "psp_2", "label": "PSP-2", "bank_id": "bank_A" },
    { "id": "psp_3", "label": "PSP-3", "bank_id": "bank_B" }
  ],
  "banks": [
    { "id": "bank_A", "label": "Bank-A", "role": "acquirer", "shared": true,  "psps": ["psp_1","psp_2"] },
    { "id": "bank_B", "label": "Bank-B", "role": "acquirer", "shared": false, "psps": ["psp_3"] }
  ],
  "routing": [
    { "method": "upi",        "psp_id": "psp_1", "weight": 1.0 },
    { "method": "upi",        "psp_id": "psp_2", "weight": 1.0 },
    { "method": "upi",        "psp_id": "psp_3", "weight": 1.0 },
    { "method": "card",       "psp_id": "psp_1", "weight": 1.0 }
    /* ...one row per (method, psp) with positive weight; 3 methods x 3 PSPs = 9 rows */
  ],
  "shared_banks": { "bank_A": ["psp_1", "psp_2"] }
}
```
**Field provenance**
- `psps[].bank_id` ← `PaymentGraph.settles_via`.
- `banks[].role` ← `Bank.role`. `banks[].psps` ← `graph.psps_for_bank(bank_id)`.
- `banks[].shared` ← `bank_id in graph.shared_banks()` (len(psps) > 1).
- `routing[]` ← `PaymentGraph.routing` (emit `(method, psp_id, weight)` for weight > 0).
- `shared_banks` ← `graph.shared_banks()` directly.
- `methods[]` ← `Method` enum. `merchant` is a **⚠️ DERIVED presentation node** — the
  core has no Merchant entity; it is the fixed root of the vision's
  Merchant→Method→PSP→Bank layout. Safe (a label, no metric attached).

---

## `POST /api/simulate`
Run ONE scenario end-to-end and return the per-window story + attribution + action +
counterfactual + baseline comparison. This is the Command Center / Incident engine.

**Request**
```json
{
  "incident_type": "A_shared_bank",
  "seed": 7,
  "intervention_threshold": 0.70,
  "system": "ariadne"
}
```
- `incident_type`: enum above. For `A_shared_bank` target is `bank_A`; `B_single_psp`
  target `psp_1`; `C_method` target `card`; `E_coincidental` targets `psp_1`+`psp_3`;
  `D_ambiguous` no target. (Server picks canonical targets, matching
  `discrimination_result` / `scenario_batch`.)
- `system`: `"ariadne"` | `"baseline"`.
- `intervention_threshold`: float, the risk dial (`select_action`).

**How the server builds this** (must re-run the loop and *capture* per-window state,
because `run_once` returns only aggregate `RunMetrics` — see NOT-BACKABLE note):
`make_incident(...)` → `generate(graph, cfg, incident)` → for each window
`window_stats` → `detect` → `attribute` (or `baseline_attribute`) → `select_action`;
then `money_recovered(...)` on the representative action. Run twice
(`system` = requested, plus `baseline`) for the comparison block.

**Response**
```json
{
  "incident": {
    "incident_type": "A_shared_bank",
    "target_id": "bank_A",
    "secondary_target_id": null,
    "start_window": 5, "end_window": 9,
    "severity": 0.21,
    "n_windows": 20
  },
  "windows": [
    {
      "window": 0,
      "detection": { "triggered": false, "dropped_nodes": [] },
      "nodes": [
        { "node_id": "psp_1", "node_kind": "psp",    "success_rate": 0.969, "baseline_rate": 0.969, "delta": 0.0,   "volume": 167, "avg_latency_ms": 121.4 },
        { "node_id": "upi",   "node_kind": "method",  "success_rate": 0.971, "baseline_rate": 0.971, "delta": 0.0,   "volume": 500, "avg_latency_ms": 120.2 }
      ]
    }
  ],
  "attribution": {
    "root_cause_id": "bank_A",
    "root_cause_kind": "bank",
    "confidence": 0.94,
    "evidence_path": [
      "bank bank_A settles ['psp_1', 'psp_2']",
      "coverage=1.00 (all its PSPs down)",
      "specificity=1.00 (down PSPs are its own)",
      "confidence=coverage*specificity=0.94"
    ],
    "claim_type": "hypothesis",
    "psp_causes": ["psp_1", "psp_2"]
  },
  "action": {
    "kind": "reroute",
    "params": { "method": "upi", "from_psp": "psp_1", "to_psp": "psp_3" },
    "decision_id": "reroute-ab12cd34ef56",
    "confidence": 0.94,
    "expected_recovery": 41250.0,
    "evidence_path": ["...", "reroute bad PSPs ['psp_1', 'psp_2'] -> healthy psp_3"]
  },
  "money_recovered": 38900.0,
  "comparison": {
    "ariadne":  { "root_cause_id": "bank_A", "root_cause_kind": "bank", "confidence": 0.94, "money_recovered": 38900.0 },
    "baseline": { "root_cause_id": "psp_1",  "root_cause_kind": "psp",  "confidence": 0.61, "money_recovered": 12100.0 }
  }
}
```
**Field provenance**
- `incident.*` ← the `Incident` built by `make_incident` (`incident_type` serialized
  as the enum value string; `secondary_*` populated only for `E_coincidental`).
  `n_windows` ← `SimConfig.n_windows` (20).
- `windows[].detection` ← `Detection.triggered` / `.dropped_nodes` per window.
- `windows[].nodes[]` ← `NodeStats` (`node_id`, `node_kind`, `success_rate`,
  `baseline_rate`, `delta`, `volume`, `avg_latency_ms`) from `window_stats`. Only
  `psp` and `method` kinds exist — **bank health is derived, never a NodeStats row**
  (see `observe/aggregate.py` docstring). The graph animation must derive bank state
  from its PSPs' deltas client-side, exactly as `attribute()` does server-side.
- `attribution.*` ← the `Attribution` returned by `attribute` for the incident-active
  window (representative window = the one whose `active_true_causes` is non-empty and
  matches the reported attribution; server picks the window with the strongest
  detection, or the incident midpoint). All fields are real:
  `root_cause_id`, `root_cause_kind` (`bank|psp|method|none`), `confidence`,
  `evidence_path` (list of strings — render verbatim, it is the "why"), `claim_type`
  (always `"hypothesis"`), `psp_causes`.
- `action.*` ← the `Action` from `select_action` for that window: `kind`
  (`reroute|disable_method|retry_fallback|do_nothing`), `params`, `decision_id`,
  `confidence`, `expected_recovery` (money, an ESTIMATE from observed stats),
  `evidence_path`.
- `money_recovered` ← `money_recovered(base_graph, cfg, incident, action)` — the REAL
  shared-seed counterfactual `revenue(action) - revenue(no_action)`. **May be
  negative** (an action that hurt); render honestly, do not clip (metrics.py docstring).
- `comparison.ariadne` / `comparison.baseline` ← two `run`s (same seed/incident,
  `system` swapped). `money_recovered` per side is that side's real counterfactual.

**⚠️ NOT-BACKABLE without a small backend add:** `run_once` currently returns only
aggregate `RunMetrics` and does **not** expose the per-window `NodeStats`,
`Detection`, `Attribution`, or `Action` — they are computed inside its loop and
discarded. The simulate endpoint therefore must **re-run the same loop in the API
layer** (calling the same core functions) to capture them, OR the core adds a
`run_once_trace(...)` that returns the per-window records. Either way, every field
above is produced by an existing core function — **nothing here is fabricated**, but
the wiring to surface per-window records is new API-layer glue (allowed: it calls the
core, adds no logic). Downstream: build against this shape; the API author supplies
the trace loop.

---

## `GET /api/evaluation`
The discrimination result + recovery-vs-risk frontier, real numbers. Wraps
`run_sweep(...)` (which internally calls `discrimination_result`).

**Query params:** `?seeds=1..20` (optional; default `DEFAULT_SEEDS` = 1..20),
`?thresholds=0.55,0.70,0.85` (optional; default).

**Response** (shape mirrors `run_sweep` output exactly)
```json
{
  "seeds": [1,2,3,"...",20],
  "thresholds": [0.55, 0.70, 0.85],
  "discrimination": {
    "incident_A_shared_bank": {
      "ariadne":  { "root_cause_accuracy": 0.87, "root_cause_accuracy_conditional": 0.90, "root_cause_accuracy_unconditional": 0.87, "rca_unconditional_per_seed": [0.9,0.8,"..."], "money_recovered": 35200.0, "money_per_seed": [38900.1,"..."] },
      "baseline": { "root_cause_accuracy": 0.0,  "root_cause_accuracy_conditional": 0.0,  "root_cause_accuracy_unconditional": 0.0,  "rca_unconditional_per_seed": [0.0,"..."],  "money_recovered": 12100.0, "money_per_seed": [12100.0,"..."] }
    },
    "incident_B_single_psp":  { "ariadne": { "..." }, "baseline": { "..." } },
    "incident_E_coincidental":{ "ariadne": { "..." }, "baseline": { "..." } },
    "A_ariadne_beats_baseline_rca": true,
    "A_ariadne_beats_baseline_money": true,
    "B_no_regression": true,
    "E_ariadne_not_over_attributes": true
  },
  "frontier": {
    "ariadne": [
      { "threshold": 0.55, "money_recovered": 31000.0, "money_per_seed": ["..."], "false_intervention_cost": 900.0, "false_interventions_total": 4, "unsafe_action_rate": 0.0, "executed_actions": 120, "unaudited_actions": 0, "do_nothing_correct_rate": 0.9988, "do_nothing_scored": 800, "do_nothing_misses": 1 }
    ],
    "baseline": [ { "threshold": 0.55, "..." } ]
  }
}
```
**Field provenance** — every field is a direct pass-through of `run_sweep`'s return:
- `discrimination` ← `discrimination_result(seeds, 0.70)`; the four booleans and the
  three per-incident `{ariadne,baseline}` blocks are exactly its keys.
- `frontier.<system>[]` ← `run_sweep` frontier points: `threshold`, `money_recovered`,
  `money_per_seed`, `false_intervention_cost`, `false_interventions_total`,
  `unsafe_action_rate`, `executed_actions`, `unaudited_actions`,
  `do_nothing_correct_rate`, `do_nothing_scored`, `do_nothing_misses`.
- All numbers are REAL (measured across seeds). No fabricated fields. Render RCA both
  ways (unconditional is the honest headline; conditional shown for continuity —
  matches `reporting/frontier.py:write_report`).

---

## `GET /api/incidents`
The catalog of incident types the operator can simulate. **⚠️ DERIVED / static:** the
backend has **no incident store or history** — it generates incidents on demand from
`(type, seed)`. This endpoint returns the enum catalog, NOT a live incident feed.

**Response**
```json
{
  "incident_types": [
    { "id": "A_shared_bank",  "label": "Shared bank outage",      "target": "bank_A",         "is_thesis": true,  "expected_correct_behavior": "attribute to shared bank" },
    { "id": "B_single_psp",   "label": "Single PSP outage",       "target": "psp_1",          "is_thesis": false, "expected_correct_behavior": "blame one PSP, not the bank" },
    { "id": "C_method",       "label": "Payment method fault",     "target": "card",           "is_thesis": false, "expected_correct_behavior": "blame the method" },
    { "id": "D_ambiguous",    "label": "Ambiguous noise dip",      "target": null,             "is_thesis": false, "expected_correct_behavior": "do nothing" },
    { "id": "E_coincidental", "label": "Coincidental dual outage", "target": "psp_1 + psp_3",  "is_thesis": false, "expected_correct_behavior": "blame two PSPs independently, no bank" }
  ]
}
```
**Provenance:** `id`/`target` ← `IncidentType` + the canonical targets used in
`scenario_batch` / `discrimination_result`. `label` and `expected_correct_behavior`
are **⚠️ DERIVED presentation strings** (human-readable glosses of the enum
docstrings) — safe, no metric attached. There is **no** "active incidents" list in
the vision's live sense; if the Command Center wants a live feed, it drives it from
`POST /api/simulate` results, and the UI must disclose these are simulated scenarios
(vision §20), not a production incident stream.

---

## `GET /api/audit`
Audit trail of executed actions. **⚠️ PARTIALLY NOT-BACKABLE — read carefully.**

The backend has **no persisted audit log**. What *is* real: every `Action` carries
audit fields (`decision_id`, `evidence_path`, `confidence`) and `metrics.py:
is_action_audited` enforces them. So an audit *entry* is fully backable **per action
produced by a simulate call** — but there is no store of past actions across requests.

**Recommended honest implementation:** `GET /api/audit?seed=&incident_type=&threshold=`
re-runs that one scenario and returns the audit entries for the actions it produced.
It is a *derivation of a specific run*, not a historical ledger.

**Response**
```json
{
  "source": "derived-from-run",
  "scenario": { "incident_type": "A_shared_bank", "seed": 7, "intervention_threshold": 0.70, "system": "ariadne" },
  "entries": [
    {
      "window": 6,
      "decision_id": "reroute-ab12cd34ef56",
      "action_kind": "reroute",
      "params": { "method": "upi", "from_psp": "psp_1", "to_psp": "psp_3" },
      "confidence": 0.94,
      "evidence_path": ["bank bank_A settles ['psp_1','psp_2']", "..."],
      "audited": true
    }
  ]
}
```
**Provenance:** `decision_id`, `action_kind`, `params`, `confidence`, `evidence_path`
← `Action`. `audited` ← `is_action_audited(action)`. `window` ← loop index.
- **⚠️ NOT-BACKABLE:** wall-clock timestamps, an operator/user identity, cross-session
  history, and "executed vs proposed" status. The core does not persist or timestamp
  actions and has no user model. Do **not** render a fake timeline with clock times or
  usernames. If a `timestamp` column is shown, it must be labeled a simulation window
  index, not real time. `source: "derived-from-run"` must be surfaced in the UI so the
  audit page honestly discloses it reflects the current simulated run.

---

## Summary: fields flagged as not fully backable
| Endpoint | Field(s) | Status | Guidance |
|---|---|---|---|
| `/api/topology` | `merchant` node | DERIVED (label only) | Safe — presentation root, no metric |
| `/api/simulate` | per-window `nodes[]`, `detection`, `attribution`, `action` | BACKABLE but not currently *returned* by `run_once` | API re-runs the core loop (or core adds `run_once_trace`) to capture them; nothing fabricated |
| `/api/simulate` | bank node health | DERIVED | No bank NodeStats row exists; derive from PSP deltas client-side |
| `/api/incidents` | `label`, `expected_correct_behavior`, "active feed" | DERIVED / static | Enum catalog, not a live incident stream; disclose "simulated" |
| `/api/audit` | timestamps, user identity, cross-session history, exec status | NOT-BACKABLE | Do not fabricate; audit is derived-from-run, window index not wall-clock |

Everything else maps 1:1 to a real core producer cited inline above.
