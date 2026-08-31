# ARIADNE

**Merchant Revenue Recovery Intelligence** — an [ATLAS-class](https://github.com/MatMridul/ATLAS) system for the merchant payment ecosystem.

> **Status: Tier-1 + Tier-2 built and green.** Full loop implemented, tested, and
> evaluated end-to-end. The Shared Dependency Discrimination result and the
> recovery-vs-risk frontier are reproduced under `reports/`.

---

## What ARIADNE is

ARIADNE models a merchant's payment ecosystem as a dependency graph (method → PSP →
bank) and, when revenue is at risk, **traces the failure back through that graph to
its root cause and out to a bounded recovery action** — with per-edge evidence,
confidence, and an audit trail. The name is Ariadne's thread: a guide out of the
payment labyrinth.

The loop:

```
simulate → aggregate → detect → attribute → decide → re-simulate outcome → score
```

## The thesis (and how it is tested)

> Does explicitly modeling the interconnected payment ecosystem let an AI diagnose
> and recover revenue better than treating every component independently?

ARIADNE is compared against a **fair non-relational baseline** that sees the exact
same per-PSP/per-method observations but lacks the dependency graph. The falsifiable
test is the **shared-bank incident (A)**: two PSPs settle via one bank, so a bank
fault surfaces as correlated PSP failures. ARIADNE derives bank health from the PSP
observations via the graph; the baseline can only see independent PSP faults.

Incident **E (coincidental)** — two PSPs on *different* banks failing together — is
the anti-triviality control: the correct answer there is two independent faults, so
a system that merely *counts* correlated failures fails E. Passing both A and E
proves ARIADNE reasons over topology, not correlation.

**Headline result** (`reports/run_report.md`, seeds 1–5):

| Incident | Metric | ARIADNE | Baseline |
|----------|--------|---------|----------|
| A shared-bank | root-cause accuracy | **0.95** | 0.00 |
| A shared-bank | money recovered | **₹120k** | ₹87k |
| B single-PSP  | root-cause accuracy | 0.95 | 0.95 (no regression) |
| E coincidental| root-cause accuracy | 0.95 | 0.95 (no over-attribution) |

The recovery-vs-risk frontier (`reports/frontier.png`) plots money recovered vs.
false-intervention cost across intervention thresholds 0.55 / 0.70 / 0.85 for both
systems — the merchant chooses how aggressive ARIADNE should be.

## Design invariants (enforced, not aspirational)

- **Python 3.11 standard library only** for core logic. `pytest` (dev) and
  `matplotlib` (only in `reporting/`) are the sole exceptions.
- **The diagnoser never sees ground truth.** `diagnosis/` and `baseline/` import
  nothing from `simulator/`; only `eval/` reads `GroundTruth`.
- **Identical raw inputs.** ARIADNE and the baseline receive the same PSP/method
  stats; ARIADNE's bank health is *derived* via the graph, never handed in.
- **Shared-seed counterfactual.** `money_recovered = revenue(action) − revenue(no_action)`
  under the same seed/draws; only the config differs. Negative values are legal and reported.
- **Attribution confidence = coverage × specificity, S_MIN = 0.8** (pinned, DR-001).
- **No cross-incident learning.** Each incident is diagnosed from its own window only.
- **Determinism.** Same seed → identical results.

## Layout

```
src/ariadne/
  model/       entities + PaymentGraph (static topology; health is derived)
  simulator/   honest-adversary generator (the ONLY holder of ground truth)
  observe/     raw txns → per-window NodeStats
  diagnosis/   ARIADNE's relational attribution (detect + attribute)
  baseline/    the fair non-relational monitor (no graph)
  decide/      bounded actions + policy (reroute / disable_method / retry_fallback / do_nothing)
  eval/        the scoring harness (reads ground truth) + scenarios + sweep
  reporting/   the recovery-vs-risk frontier plot (matplotlib, isolated)
```

## Running

```bash
# tests (stdlib + pytest only)
python -m pytest -q

# reproduce the discrimination result + frontier (needs matplotlib)
python -c "import sys; sys.path.insert(0,'src'); \
from ariadne.eval.sweep import run_sweep; \
from ariadne.reporting.frontier import plot_frontier, write_report; \
r=run_sweep(seeds=[1,2,3,4,5]); plot_frontier(r,'reports/frontier.png'); write_report(r,'reports/run_report.md')"
```

## Governance

Design decisions are recorded under [`docs/decisions/`](docs/decisions/) (two-pass
Proposed→closed, immutable history). The build contract is in
[`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md); the domain model in
[`docs/adapter.md`](docs/adapter.md); scope tiers in [`docs/SCOPE.md`](docs/SCOPE.md).

## Relationship to ATLAS

ATLAS is the reusable *class*; ARIADNE is a concrete *instantiation* for the merchant
payment domain.

## License

Deferred.
