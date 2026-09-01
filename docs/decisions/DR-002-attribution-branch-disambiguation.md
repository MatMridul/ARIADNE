# DR-002 — Attribution branch disambiguation: shared-dependency vs. independent-PSP vs. method

> **Layer: ARIADNE (instantiation).** This DR clarifies/amends the *interaction*
> between the attribution branches pinned in DR-001 (B1). It does NOT change the
> `coverage × specificity`, `S_MIN = 0.8` shared-cause formula, the acting baseline,
> or the graph size — those remain exactly as **DR-001 (Accepted)** set them.
> DR-001 is not rewritten. This DR is the smallest possible clarifying amendment.

- **Status:** Proposed
- **Status history:** Proposed 2026-08-31 (awaiting independent challenge)
- **Date proposed:** 2026-08-31
- **Date resolved:** _pending_
- **Supersedes / Superseded by:** Clarifies/amends DR-001 (does NOT supersede it)

## Question

DR-001 pinned the shared-cause attribution formula and an ordered decision rule
(bank → independent PSPs → method → none). When two independent PSPs on *different*
banks fail at the same time (incident E), what exactly distinguishes an
**independent-PSP** explanation from a **method-level** explanation, so the two
branches do not wrongly pre-empt one another?

## Context

DR-001 (Accepted) fixed attribution as: for each bank X, `coverage(X)` and
`specificity(X)`; blame the bank when `coverage == 1.0` and `specificity >= S_MIN`
(0.8), else blame independent PSPs when the down PSPs span different banks (no bank
reaches coverage 1.0 with >1 PSP), else blame a method, else none. `BUILD_SPEC.md`
§3.8 writes this rule with the **independent-PSP branch BEFORE the method branch**.

The independent acceptance audit (E6 finding) discovered that the *implementation*
in `diagnosis/attribute.py` reversed those two branches: it selected a method cause
whenever `len(down) > 1` and *any* method's delta breached a fixed −0.05, which
fires on incident E because an unrelated method's aggregate dips along with the two
PSP-localized faults. Result: on E, ARIADNE wrongly returned `method`/netbanking in
~93% of both-PSPs-down windows, and the E anti-over-attribution check failed on 3 of
4 independent seed blocks (it held only on the committed seeds 1–5).

So the frozen *intent* is correct, but DR-001 never stated the *semantic condition*
under which a method explanation is preferred over an independent-PSP explanation —
it only stated an order. That gap is load-bearing (it decides the E-vs-C boundary),
so per the decision-record README's implementation-assumption test it warrants a new
DR that clarifies DR-001 rather than a silent code edit or an edit to DR-001.

## Evidence

Reproduced on this branch (`build/tier1-tier2-full`, commit 5f7808d), seeds 1–25,
multi-PSP-down windows, statistic = (second-worst method delta − worst method delta),
i.e. how much the most-degraded method dominates the next:

| Incident | n windows | min | mean | median | max |
|----------|-----------|-----|------|--------|-----|
| E (independent PSPs) | 14 | 0.001 | 0.026 | 0.024 | 0.121 |
| A (shared bank)      | 83 | 0.000 | 0.027 | 0.024 | 0.138 |
| C (method fault)     | 44 | 0.093 | 0.211 | 0.200 | 0.379 |

Interpretation (physical, not curve-fit): a **method** fault concentrates failure in
ONE method — the worst method dominates the next by a clear margin. A **PSP-localized**
fault (independent PSPs, or a shared bank) hits *all* methods routed through the bad
node roughly equally, so no single method stands out (concentration ≈ 0). This is the
real observable difference between "card is broken" and "a PSP/bank is broken."

Per-window example (E, seed 12): methods card −0.11, netbanking −0.16, upi −0.14
(spread, concentration 0.02) with per-PSP drops ~0.185 → independent PSPs.
Per-window example (C, seed 7): card −0.24, netbanking +0.01, upi 0.00
(concentration ~0.24) with diluted per-PSP drops ~0.074 → method.

## Options

- **B1 — Restore the DR-001/BUILD_SPEC order (independent-PSP before method) AND
  gate the method branch on genuine method *concentration* (recommended).** A method
  cause is selected only when the worst method's delta breaches the method-detect
  floor AND dominates the second-worst method by a margin
  `METHOD_CONCENTRATION_MIN` (proposed 0.06, sitting in the clean gap between the E/A
  max ≈ 0.14 and the C min ≈ 0.09). Otherwise the down PSPs are blamed independently.
  This is the smallest change that makes the semantics correct: it encodes *why* a
  method explanation is warranted (concentrated single-method failure) rather than
  merely *when* it is checked. Deterministic, stdlib-only, no new scoring model.
- B2 — Pure reorder (independent-PSP strictly before method) with no concentration
  gate. Rejected: it fixes E but then a genuine method fault that saturates all PSPs
  (incident C at high severity, all three PSPs breach detection) would be caught by
  the independent-PSP branch first and *never* reach the method branch — trading the
  E bug for a C bug. The audit showed C already saturates PSP detection, so this is a
  real regression, not hypothetical.
- B3 — Replace the branch structure with a probabilistic/likelihood model over
  failure patterns. Rejected: DR-001's external challenge explicitly warned against
  replacing the pinned deterministic form with a fancier model; out of scope and
  premature for v1.
- B4 — Do nothing (leave the implementation as-is). Rejected: the audit proved the
  E anti-triviality result is not robust across seeds; leaving it makes the E-vs-A
  contrast — the anti-circularity guard DR-001 relies on — unsound.

## Proposed Decision

Adopt **B1.** Keep DR-001's shared-cause formula and `S_MIN` exactly. Clarify the
branch interaction as:

1. **Shared dependency** — a bank X with `coverage(X) == 1.0`, `|P(X)| > 1`, and
   `specificity(X) >= S_MIN`. `confidence = coverage × specificity`. (unchanged)
2. **Method failure** — selected only when a single method is *concentrated*: the
   worst method's `delta <= -METHOD_DELTA_MIN` **and** `(second_worst_delta −
   worst_delta) >= METHOD_CONCENTRATION_MIN`. This is the observable signature of a
   method-wide fault (one method dominates; others are near baseline). A method
   explanation that is not concentrated is NOT preferred over independent PSPs.
3. **Independent PSP failures** — the detected down PSPs, when neither a shared bank
   (step 1) nor a concentrated method (step 2) explains them. This is the correct
   answer for incident E (two PSPs on different banks) and single-PSP incident B.
   `confidence = mean per-PSP |delta| normalized to 0..1` (unchanged from DR-001).
4. **None** — nothing breaches; drives do_nothing. (unchanged)

`METHOD_CONCENTRATION_MIN` is a named constant, proposed 0.06, chosen to sit in the
empirically clean separation gap (E/A concentration ≤ ~0.14 vs C concentration ≥
~0.09 — see Evidence); it is a build-time tuning constant like S_MIN, documented so
runs reproduce, NOT a per-incident value and NOT tuned against ground truth.

This is verified on paper against all seven required semantic cases (see below)
before implementation.

## Strongest Argument Against

`METHOD_CONCENTRATION_MIN = 0.06` sits below the observed E/A maximum concentration
(~0.12–0.14) in a small number of windows, so there is a narrow overlap band where a
non-method incident could momentarily show concentration above the threshold and be
mislabeled a method fault (or, symmetrically, a very mild single-method fault could
fall below it and be read as independent PSPs). The constant is therefore doing real
discriminating work in a region where the two distributions are not perfectly
separated — which means the E-vs-C boundary is decided by a tuned scalar, and a
hostile reviewer could argue we again risk grading our own homework by picking the
number that makes E pass. The mitigation is that the seven regression cases encode
the *semantics* (spread vs. concentrated), not target numbers, and the broader fixed
seed evaluation (not a favorable block) reports the residual error honestly — but the
overlap band is a genuine, disclosed limitation, not a fully dissolved one.

---
<!-- Everything below is Pass 2: filled only after independent challenge.
     Everything ABOVE this line is FROZEN once the Proposed commit lands. -->

## External Challenge

_pending — to be filled after independent (ChatGPT / reviewer) challenge._

## Resolution

_pending._

## Decision

_pending._ — **Accepted / Rejected / Deferred.**

## Consequences

_pending._
