# ARIADNE — Where Everything Lives (spec pointer)

You are building ARIADNE in `C:\Mridul\Programs\ARIADNE`. The full, frozen,
ratified spec is on disk. Read on demand — do NOT re-read every turn (that wastes
budget). Start here, in this order:

1. `docs/BUILD_ORDER.md`   ← START HERE. Phase-by-phase build sequence + stop conditions.
2. `docs/BUILD_SPEC.md`    ← the microscopic module-by-module contract (data structures, signatures).
3. `docs/adapter.md`       ← the domain model (entities, relationships, incidents, actions, eval).
4. `docs/SCOPE.md`         ← the three tiers + fallback ladder. Do NOT build Tier 3.
5. `docs/decisions/DR-001-ariadne-core-design.md`  ← Accepted design decisions (graph 3/3/2,
                              attribution formula coverage×specificity S_MIN 0.8, acting baseline).

The class this instantiates: `C:\Mridul\Programs\ATLAS` (read only if you need the
ATLAS-class contract; `docs/EVALUATION.md §7` is the required relational-value principle).

If a design question arises that these files do NOT resolve: the reasoning behind
every decision is in the DRs and in KiroCrew memory (searchable). Surface a genuine
gap to the user rather than inventing an architecture. The spec decides designs;
you decide function bodies.
