# DR-001 — ARIADNE core design: graph size, attribution scoring, and a fair acting baseline

> **Layer: ARIADNE (instantiation).** This DR answers *"what exact choices are we
> making to build ARIADNE?"* — the concrete merchant-payment instantiation, one
> level below the ATLAS class. Its counterpart one layer UP is the ATLAS class
> repo's `DR-001` (Shared Dependency Discrimination Test), which answers *"what
> reusable principle graduates back into the ATLAS class?"* Keep the two separate:
> instantiation choices live here; class principles live in the ATLAS repo.

- **Status:** Accepted
- **Status history:** Proposed 2026-08-31 → Accepted 2026-08-31
- **Date proposed:** 2026-08-31
- **Date resolved:** 2026-08-31
- **Supersedes / Superseded by:** —

## Question

For ARIADNE v1, three coupled design choices must be fixed before the build:
(a) how big should the payment dependency graph be; (b) what is the exact form of
the attribution scoring that decides "one shared node is the cause" vs. "several
nodes failed independently"; and (c) should the non-relational baseline only
*diagnose*, or also *take recovery actions*?

## Context

ARIADNE instantiates the ATLAS class for the merchant payment domain (Razorpay
Buildathon Track 03). Its thesis is that explicitly modeling the payment
dependency graph lets it diagnose and recover revenue better than treating each
component independently. The falsifiable test is the **shared-bank scenario**: two
payment companies (PSPs) settle through the same bank, so a bank fault surfaces as
correlated failures across both PSPs. ARIADNE is compared against a *fair*
non-relational baseline (same observations, no graph).

These three choices are coupled because they jointly determine whether the
experiment is (1) non-trivial, (2) cleanly falsifiable, and (3) an apples-to-apples
comparison. They are marked `[DECISION → DR-001]` in `docs/BUILD_SPEC.md`. The
build runs on a cheaper model against a frozen spec under a tight credit budget, so
these must be settled now, not discovered mid-build.

## Evidence

This is a pre-build design DR, so the evidence is the spec's own structural logic
plus the ATLAS-class constraints, not runtime results yet:

- The graph only "earns its place" if there is at least one **shared downstream
  node** feeding multiple upstream paths — otherwise a per-node monitor sees
  everything the graph sees (ATLAS SPEC §6 anti-patterns; DESIGN_PRINCIPLES §10).
- For the shared-bank signal to be distinguishable from independent PSP faults,
  the topology needs ≥2 PSPs sharing ≥1 bank **and** at least one PSP on a
  different bank as a negative control (so "blame the bank" is falsifiable).
- Track 03's bar is "money recovered across a batch." If the baseline only
  diagnoses and does not act, the two systems cannot be compared on the actual
  domain objective (money recovered) — only on diagnosis accuracy, which is a
  weaker and more contestable claim.

## Options

**(a) Graph size**
- **A1 — 3 methods / 3 PSPs / 2 banks, bank_A shared by PSP-1 & PSP-2, bank_B on
  PSP-3 (recommended).** Minimal topology that still contains a shared dependency
  *and* a negative-control path. Cheap to simulate and reason over.
- A2 — larger (e.g. 5 PSPs / 3 banks). More realistic, more incident variety, but
  more simulator/reasoning surface and more build cost for no extra thesis clarity.
- A3 — flat (PSPs only, no bank layer). Rejected: removes the shared dependency,
  which *is* the experiment.

**(b) Attribution scoring form**
- **B1 — "single shared explanation vs. independent explanations" comparison, with
  a pinned coverage/specificity confidence formula (recommended).** For each bank
  X, coverage = fraction of X's PSPs that are down; specificity = fraction of the
  down PSPs that are X's. Blame the bank when coverage = 1.0 and specificity ≥ S_MIN
  (start 0.8), with confidence = coverage × specificity; blame independent PSPs when
  down PSPs sit on different banks (no bank reaches coverage 1.0 with >1 PSP); else
  "none." Deterministic, explainable, bounded confidence, and — critically — it
  separates the shared-bank case (A) from a *coincidental* two-different-banks case
  (E) rather than merely counting correlated failures.
- B2 — a probabilistic/likelihood model over failure patterns. More principled
  calibration, but adds complexity that must earn its place; premature for v1.
- B3 — pure per-node thresholding. Rejected: that is the *baseline*, not ARIADNE.

**(c) Does the baseline act?**
- **C1 — baseline also acts, using the same action menu driven by its per-node
  view (recommended).** Enables an apples-to-apples "money recovered" comparison —
  same objective, same actions, only the reasoning differs.
- C2 — baseline diagnoses only. Simpler, but reduces the comparison to diagnosis
  accuracy and forfeits the strongest, most Track-03-aligned claim.

## Proposed Decision

Adopt **A1 + B1 + C1**: the 3/3/2 shared-bank topology; the deterministic
shared-vs-independent explanation score for attribution; and a baseline that also
takes actions from the same menu. This keeps the experiment minimal, cleanly
falsifiable, deterministic (no ML/LLM in v1), and a fair head-to-head on the actual
domain objective (money recovered), while honoring "complexity must earn its place."

**Guard against the circularity/triviality risk (added after an internal hostile
review, before this DR was committed).** To stop B1 from being a trivial
failure-*counting* rule that "grades its own homework," the simulator adds a fifth
incident type **E (coincidental):** two PSPs on *different* banks drop at the same
time, where the correct answer is two *independent* faults, not a shared cause. A
mere counter of correlated failures fails E; only genuine topology reasoning gets
both A and E right. The scoring rule (B1) and the incident-injection rule are to be
developed as adversaries, and the A-vs-E contrast is the falsification guard. This
addresses — but does not fully dissolve — the Strongest Argument Against below,
which is left frozen as the honest pre-mitigation doubt for the external challenger
to weigh.

## Strongest Argument Against

The 3/3/2 topology is so small that the shared-bank signal may be **trivially**
detectable — with only two PSPs on the shared bank, "both down at once" is a very
loud, low-ambiguity pattern, which risks making ARIADNE's win look easy and
unconvincing to judges (and conversely makes the honest-adversary noise harder to
tune so the case stays genuinely ambiguous). A larger graph would produce richer,
more overlapping failure patterns where the graph's advantage is more striking and
less hand-wavable. There is also a real risk that the deterministic B1 rule is
*so* aligned with how the simulator injects the incident that ARIADNE is quietly
grading its own homework — the scoring rule and the injection rule must be
developed and reviewed as adversaries, or the discrimination result is circular.

---
<!-- Everything below is Pass 2: filled only after independent challenge.
     Everything ABOVE this line is FROZEN once the Proposed commit lands. -->

## External Challenge

The independent reviewer (ChatGPT) reviewed the ARIADNE-level decisions together
with the five hardening revisions proposed after Kiro's internal hostile review.
Recorded honestly — what it actually engaged, and what it did not:

- **Attribution formula (decision b):** explicitly endorsed. The reviewer said to
  keep the pinned `confidence = coverage × specificity` form (with `coverage = 1.0`
  and `specificity ≥ S_MIN = 0.8`) *unless a revision exposed an internal
  inconsistency*, and specifically warned against replacing it with a more
  sophisticated model — the point being to remove build-time judgment while keeping
  v1 minimal. No inconsistency was found in the consistency pass.
- **Acting baseline (decision c):** accepted implicitly. The reviewer's
  counterfactual-integrity constraint (compare action vs. no-action under the same
  stochastic realization) presupposes that *both* systems act and are compared on
  realized money-recovered — i.e. it took the acting baseline as given rather than
  contesting it.
- **Graph size / triviality (decision a):** **NOT directly attacked.** The reviewer
  did not challenge whether the 3/3/2 topology makes the shared-bank win trivial,
  nor the circularity worry that the scoring rule could mirror the injection rule
  (the DR's own Strongest Argument Against). It neither endorsed nor refuted that
  specific doubt.
- **Process constraints:** the reviewer required information parity (identical raw
  per-PSP/per-method inputs; bank health derived, never supplied), shared-seed
  counterfactual integrity, an explicit no-cross-incident-learning invariant, DR
  Pass-1 immutability, and preservation of the ARIADNE-vs-ATLAS layer distinction.

This was a genuine independent review of the decisions and their hardening — it was
NOT a full re-derivation or line-by-line re-attack of every argument in the DR, and
this Resolution does not claim it was.

## Resolution

The Proposed Decision (**A1 + B1 + C1**) survives unchanged. Nothing in the
challenge moved any of the three choices:

- The pinned attribution formula stays exactly as proposed (endorsed).
- The acting baseline stays (implicitly accepted).
- The 3/3/2 graph size stays.

On the one point the challenge did **not** press — the graph-size / "grading its
own homework" doubt in the Strongest Argument Against — the residual risk is
**mitigated, not dissolved**, by the coincidental incident **E** (two PSPs on
different banks failing together, where the correct answer is two independent
faults). A rule that merely counts correlated failures fails E; only genuine
topology reasoning passes both A and E. The scoring rule and the incident-injection
rule are to be built as adversaries, and the A-vs-E contrast is the falsification
guard. This is recorded as a residual risk to watch at eval time, not as a fully
closed concern: if, once built, ARIADNE's advantage on A does not survive the
presence of E (or the 3/3/2 signal proves trivially separable), that is grounds to
revisit graph size — which, being an implementation finding against this decision's
*foundation*, would open a new superseding DR rather than silently edit this one.

## Decision

**Accepted.** A1 (3/3/2 shared-bank topology) + B1 (`coverage × specificity`,
`S_MIN = 0.8`) + C1 (fair acting baseline), with incident E as the standing
anti-triviality control and a residual-risk note on graph size.

## Consequences

- **Enables** the build: `default_graph()` = 3/3/2, `attribute()` uses the pinned
  formula, the baseline acts, and the eval must include incident E. These are now
  fixed inputs to `BUILD_SPEC.md` / `BUILD_ORDER.md` — the build session implements
  them, it does not re-decide them.
- **Constrains** the honesty story: the discrimination claim now rests on the A-vs-E
  contrast, not on A alone. Eval reporting must show E results alongside A.
- **Leaves open** (separately): whether the discrimination test should become a
  *class-level* ATLAS requirement — that is ATLAS DR-001, still Proposed and
  awaiting its own dedicated external challenge. ARIADNE's acceptance here does NOT
  ratify the class-level generalization.
- **Watch item:** if graph size proves too small to make the win non-trivial once
  measured, revisit via a new superseding DR (foundation-level change), per the
  reversal-vs-supersession rule.
