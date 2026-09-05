# ARIA — Build Order (the Haiku session follows this literally)

> Read `docs/adapter.md`, `docs/BUILD_SPEC.md`, `docs/SCOPE.md`, and both
> `.kiro/steering/*.md` first. Then work these steps IN ORDER. Do not skip ahead,
> do not widen before the thin loop runs, do not add anything in Tier 3 of SCOPE.md.
> After each step, run its tests and make sure they pass before moving on.
>
> Guiding philosophy: **you decide function bodies, not designs.** Every design
> choice is already made in the spec/DRs. If you hit a genuine design fork the spec
> did not resolve, STOP and surface it — do not invent an architecture.

## Phase 0 — project skeleton
1. Create the package layout from BUILD_SPEC §2 (`src/ariadne/...`, `tests/`),
   `pyproject.toml` (Python 3.11, pytest as dev dep, matplotlib optional extra),
   empty `__init__.py` files. Confirm `pytest` runs (0 tests) green.

## Phase 1 — the model (no reasoning yet)
2. `model/entities.py` — the dataclasses/enums from §3.1.
3. `model/graph.py` — `PaymentGraph` + `default_graph()` (3/3/2, bank_A shared).
4. `tests/test_graph.py` — `psps_for_bank` / `shared_banks` return the shared PSPs;
   `reroute` returns a new graph and leaves the original unchanged.

## Phase 2 — the simulator (honest adversary)
5. `simulator/config.py`, `simulator/incidents.py` (four incident types +
   `Incident` + `GroundTruth`), `simulator/engine.py` (`generate`).
6. `tests/test_simulator.py` — same seed → identical txns; a SHARED_BANK incident
   lowers success across ALL PSPs on the target bank and nowhere else; incident D
   injects noise only; a COINCIDENTAL (E) incident drops two PSPs on DIFFERENT
   banks independently; onset/duration/severity are randomized per seed. **Verify
   GroundTruth is returned separately, not embedded in the transaction stream the
   reasoner reads.**

## Phase 3 — observation
7. `observe/aggregate.py` — `NodeStats` + `window_stats` (per-PSP, per-method).
8. `tests/test_aggregate.py` — stats and rolling baseline compute correctly.

## Phase 4 — the thin end-to-end loop (ONE incident, ONE action, ONE metric)
9. `diagnosis/detect.py` (`detect`).
10. `diagnosis/attribute.py` (`attribute`) — the shared-vs-independent scoring
    (DR-001 B1: `confidence = coverage × specificity`, `S_MIN = 0.8`).
    **Import nothing from `simulator/incidents.py`.** Diagnose from THIS window's
    observations only — keep no state across incidents (BUILD_SPEC §1 rule 7).
11. `decide/actions.py` (`reroute`, `do_nothing` only for now) + `decide/policy.py`
    (`select_action` with the intervention threshold).
12. `eval/metrics.py` (start with `money_recovered`, `false_intervention_cost`,
    `do_nothing_correct_rate`) + a minimal `eval/run.py:run_once` for ONE incident-A
    scenario at ONE threshold. **`money_recovered` uses the shared-seed
    counterfactual** (action vs. no-action under the SAME seed/draws — BUILD_SPEC §3.13).
13. Prove the thin loop runs end to end on incident A and produces a money-recovered
    number. **Checkpoint: the loop works before widening.**
14. `tests/test_attribute.py` (bank / psp / none / **coincidental-E → two
    independent PSPs, not a bank**), `tests/test_policy.py` (below-threshold →
    do_nothing; never disable last method; never reroute onto a bad node),
    `tests/test_metrics.py`.

## Phase 5 — the fair baseline + the discrimination result
15. `baseline/independent.py` — same stats, no graph, blames each node itself.
16. `tests/test_baseline.py` — on the shared-bank window the baseline returns
    multiple independent PSP faults, never a bank (proves the gap exists); on the
    coincidental (E) window the baseline is correct (independent PSPs).
17. Extend `eval/run.py` to run BOTH systems and produce the discrimination result:
    ARIA beats baseline on incident A, does not regress on B, and does not
    over-attribute on E (the A-vs-E contrast isolates ARIA's real advantage).

## Phase 6 — widen to the full batch + frontier
18. `eval/scenarios.py` — the batch mixing A/B/C/D/E + clean windows.
19. `eval/run.py:run_sweep` across seeds × thresholds (0.55/0.70/0.85).
20. `reporting/frontier.py` — plot recovery vs. false-intervention cost, both series.
21. `tests/test_run.py` — sweep produces the A-improvement + B-no-regression result
    and a frontier with one point per threshold.

## Phase 7 — Tier-2, ONLY if credits remain (see SCOPE.md fallback ladder)
22. Add `disable_method_temporarily` + `retry_with_fallback` and their policy paths.
23. Add incident-C richness, calibration figure, run report — each independently.

## Definition of done
Run the full suite green, produce the frontier PNG, and confirm every box in
BUILD_SPEC §6. If the discrimination test does NOT favor ARIA, report that
honestly — it is a valid result, not a bug to hide.

## Stop conditions (surface to the human, don't improvise)
- A design fork the spec/DRs did not resolve.
- A temptation to give the diagnoser any access to ground truth to pass a test.
- A dependency outside the allowed stack feels necessary.
- Scope creep beyond Tier 1 while Tier 1 is not yet green.
