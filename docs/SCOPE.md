# ARIADNE — Minimal Scope Contract (the budget ceiling)

> This is not a wishlist — it is a **ceiling**. If the hostile review or the build
> surfaces "we need X to be rigorous," X must be sorted into one of the three tiers
> below before it is built. The danger after review is not a flaw; it is **scope
> explosion** — rebuilding ATLAS inside a hackathon submission. Anything not in
> Tier 1 does not ship in v1 unless it is explicitly promoted here, in writing.

The organizing question for every proposed feature:

> **Is this REQUIRED to prove the thesis / satisfy Track 03, a NICE engineering
> enhancement, or ABSOLUTELY NOT v1?**

---

## Tier 1 — REQUIRED for v1 (the thesis + Track 03 bar)

The smallest end-to-end vertical slice that honestly proves ARIADNE's claim. If
any of these is missing, the submission does not stand.

- **One merchant**, the 3/3/2 graph (3 methods, 3 PSPs, 2 banks, one bank shared)
  — enough for the shared-dependency case + a negative-control path.
- **The five incident types** (A shared-bank, B single-PSP control, C method-level,
  D ambiguous/no-cause, E coincidental-different-banks). Without B/E there is no
  over-attribution check; without D no do-nothing check; without A there is no
  thesis. **E is required, not optional** — it is what proves ARIADNE reasons over
  topology rather than merely counting correlated failures.
- **The full loop, end to end:** simulate → aggregate → detect → attribute →
  decide → re-simulate outcome → score.
- **ARIADNE's relational attribution** (bank blamed via its PSPs) AND **the fair
  non-relational baseline** seeing the same observations minus the graph. Both must
  exist — the comparison IS the experiment.
- **`do_nothing` as a first-class action** and at least one real recovery action
  (`reroute_traffic`). Reroute is the minimum that produces measurable recovery.
- **The Shared Dependency Discrimination result:** ARIADNE beats the baseline on
  incident A, does not regress on B, AND does not over-attribute on E — measured,
  reported honestly either way.
- **Money recovered across a batch** (Track 03's bar), computed with the
  **shared-seed counterfactual**, + the **safety metrics** (false-intervention
  cost, do-nothing-correct-rate) reported as loudly as recovery.
- **The recovery-vs-risk frontier** across ≥3 intervention thresholds, plotted.
- **Determinism** (seeded) and **the diagnoser/ground-truth seal** (the eval is the
  only reader of ground truth).
- **Tests** for graph, simulator, attribute, baseline, policy, metrics, run.

## Tier 2 — NICE-TO-HAVE (build only if credits remain after Tier 1 is green)

Genuine enhancements that strengthen the story but are not load-bearing. Each is
independently skippable.

- The other two recovery actions (`disable_method_temporarily`, `retry_with_fallback`).
- More incident variety per type (varying severity, partial degradation, staggered
  onset) for a richer frontier.
- Calibration reporting (does stated confidence match hit rate) as its own figure.
- Cohort/geography-specific incidents (a fault that hits only one customer segment).
- A short auto-generated run report (markdown) summarizing a batch.
- More than two banks / an issuer-vs-acquirer distinction that actually changes a
  diagnosis.

## Tier 3 — ABSOLUTELY NOT v1 (out of scope, on purpose)

These are where scope explosion lives. Building any of them means rebuilding ATLAS
inside the hackathon. Explicitly excluded:

- Any graph database, vector store, ML model, LLM, or agent framework.
- Real Razorpay / real merchant data or live API integration.
- A web UI / dashboard / interactive front end.
- Multiple merchants, multi-tenant modeling, or org hierarchies.
- Streaming / real-time ingestion; everything is batch, in-process.
- Temporal decay of coefficients, moderators/sign-reversal, or the other
  ATLAS-vision reasoning-layer features (those are ATLAS R&D, not ARIADNE v1).
- Learning/adaptation: ARIADNE must NOT learn from past incidents within a run
  (that risks the loop teaching itself the answer — see hostile-review surface #6).
- Auth, persistence, deployment, packaging for distribution.

---

## The fallback ladder (if credits run low mid-build)

Build in this order so there is always a submittable artifact:

1. **Minimum submittable:** Tier 1 with `reroute` only, incidents A+B+D, frontier
   at 3 thresholds. This alone proves the thesis and clears Track 03.
2. Add incident C (method-level) and the third/fourth actions (Tier 2).
3. Add Tier 2 richness (calibration figure, cohort incidents, run report).

If the build stalls, stop at the highest completed rung and ship that. A clean
Tier-1 slice beats a half-finished Tier-2 sprawl.
