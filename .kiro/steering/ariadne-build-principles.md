# ARIADNE — Build Principles (steering)

You are building ARIADNE, an ATLAS-class "Merchant Revenue Recovery Intelligence"
system, from a frozen spec. Read `docs/adapter.md` and `docs/BUILD_SPEC.md` — they
are the contract. These rules apply on **every** turn.

## The one rule that matters most

**The graph must earn its place.** Do not build a graph feature because graphs are
cool or because the spec mentions it. Build it because it enables a specific
decision that the non-relational baseline *cannot* make. If a feature enables no
such decision, cut it and note why. Complexity must earn its place.

## Non-negotiables

1. **Python standard library only** for core logic. `pytest` (dev) and
   `matplotlib` (only in `reporting/`) are the sole exceptions. No graph DB, no
   vector store, no ML framework, no LLM, no web framework. If you believe you
   need one, STOP and write a Decision Record first — do not add it silently.

2. **The diagnoser must never see ground truth.** Code under `src/ariadne/diagnosis/`
   and `src/ariadne/baseline/` must never import, read, or receive the simulator's
   injected-incident parameters (`Incident`, `GroundTruth`). Ground truth is read
   ONLY by `src/ariadne/eval/`. If you find yourself passing ground truth into a
   diagnoser to make a test pass, the test is wrong — fix the test, not the seal.

3. **Observed vs. derived is sacred.** Raw transactions are observed facts. Node
   health, attribution, and recovery estimates are DERIVED and must carry
   `claim_type`, an evidence path, and a confidence value.

4. **Determinism.** Everything flows from a seed. Same seed → identical
   transactions → identical results. Never use unseeded randomness.

5. **Unknown > fabricated.** Never invent a number the simulator did not produce.
   If a value is unknown, represent it as unknown / low-confidence — never a guess
   dressed as a fact.

6. **No cross-incident learning (v1 invariant).** Diagnose each incident from ITS
   OWN observation window only. The diagnoser keeps no state across incidents and
   never adapts from a past incident's outcome — nothing about how one incident
   resolved may influence diagnosis, action selection, or evaluation of the next.
   This closes the "feedback loop teaches itself the answer" hole. (Learning /
   adaptation is Tier 3, out of scope — see `docs/SCOPE.md`.)

## The honesty guards (do not weaken these to get a nicer result)

- The evaluation is written **before** we know whether ARIADNE beats the baseline.
  A loss on the shared-bank test is a **valid, useful result** — report it, do not
  hide or tune around it.
- `do_nothing` is a first-class action. Correctly doing nothing on the
  ambiguous/no-cause incident (incident D) is a WIN and is scored as one.
- **Report false-intervention cost as loudly as recovery.** Safety metrics are not
  an appendix.
- The baseline is the **strongest reasonable non-relational alternative**, not a
  strawman. It sees the same observations ARIADNE sees. It only lacks the graph.

## Working style

- Small, tested modules — one test file per module. No module over ~200 lines.
- Build the loop end-to-end thin first (one incident, one action, one metric),
  then widen. A working narrow loop beats a broad half-loop.
- Every material design choice → a Decision Record in `docs/decisions/` (Proposed
  state), never ratified alone.
- On Windows/PowerShell: no bash heredocs, no `for`-loop `$f` interpolation, no
  `&` chaining, no Unix `tail`/`head`. Write files with the editor and
  `git commit -F`; use `Select-Object`/`Get-Content`.
