"""The harness / sweep test (BUILD_SPEC §5, §3.14, BUILD_ORDER step 21).

``run_sweep`` must produce (1) the Shared Dependency Discrimination result —
ARIADNE improves on incident A and does not regress on B (plus no over-attribution
on E) — and (2) a recovery-vs-risk frontier with one point per threshold per
system. Seed/threshold counts are kept small so the sweep runs fast.

This is an ``eval/`` test — the only layer that reads GroundTruth.
"""

import ast
import pathlib

from ariadne.eval.run import run_sweep
from ariadne.eval.scenarios import scenario_batch
from ariadne.simulator.incidents import IncidentType

_SEEDS = [7, 11]
_THRESHOLDS = (0.55, 0.70, 0.85)


def test_scenario_batch_exercises_all_five_incident_types():
    batch = scenario_batch(7)
    kinds = {inc.incident_type for inc, _cfg in batch}
    # all five incident types plus clean (NONE) windows appear.
    assert IncidentType.SHARED_BANK in kinds
    assert IncidentType.SINGLE_PSP in kinds
    assert IncidentType.METHOD in kinds
    assert IncidentType.NONE in kinds  # D / clean
    assert IncidentType.COINCIDENTAL in kinds


def test_scenario_batch_is_deterministic_per_seed():
    a = scenario_batch(7)
    b = scenario_batch(7)
    assert [c.seed for _i, c in a] == [c.seed for _i, c in b]
    assert [i.incident_type for i, _c in a] == [i.incident_type for i, _c in b]
    # a different seed yields different per-scenario seeds.
    other = scenario_batch(8)
    assert [c.seed for _i, c in a] != [c.seed for _i, c in other]


def test_run_sweep_discrimination_result():
    sweep = run_sweep(_SEEDS, thresholds=_THRESHOLDS)
    summary = sweep["discrimination"]["summary"]
    # A: ARIADNE names the shared bank where the baseline cannot -> improvement.
    assert summary["A_ariadne_beats_baseline"] is True
    assert summary["A_ariadne_blames_bank"] is True
    assert summary["A_baseline_blames_independent_psps"] is True
    # B: no regression (both correct on the single-PSP control).
    assert summary["B_no_regression"] is True
    # E: no over-attribution (ARIADNE stays PSP-level, not a bank).
    assert summary["E_ariadne_no_over_attribution"] is True


def test_run_sweep_frontier_one_point_per_threshold_per_system():
    sweep = run_sweep(_SEEDS, thresholds=_THRESHOLDS)
    frontier = sweep["frontier"]
    assert set(frontier) == {"ariadne", "baseline"}
    for system in ("ariadne", "baseline"):
        points = frontier[system]
        assert len(points) == len(_THRESHOLDS)
        assert [p["threshold"] for p in points] == list(_THRESHOLDS)
        for p in points:
            assert "money_recovered" in p
            assert "false_intervention_cost" in p


def test_run_sweep_ariadne_recovers_more_than_baseline_on_batch():
    """The batch-level payoff of the discrimination gap: ARIADNE recovers strictly
    more money than the baseline (which cannot name the shared bank on A)."""
    sweep = run_sweep(_SEEDS, thresholds=_THRESHOLDS)
    ariadne_best = max(p["money_recovered"] for p in sweep["frontier"]["ariadne"])
    baseline_best = max(p["money_recovered"] for p in sweep["frontier"]["baseline"])
    assert ariadne_best > baseline_best


def test_only_reporting_imports_matplotlib():
    """Guard the seal: matplotlib must appear ONLY under reporting/ and its import
    must be inside a function (not module top-level) so the suite runs without it."""
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "ariadne"
    offenders = []
    for path in src.rglob("*.py"):
        text = path.read_text()
        if "matplotlib" not in text:
            continue
        rel = path.relative_to(src)
        if rel.parts[0] != "reporting":
            offenders.append(str(rel))
            continue
        # inside reporting: the import must be nested (guarded), never top-level.
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = " ".join(a.name for a in node.names)
                if "matplotlib" in mod or "matplotlib" in names:
                    offenders.append(f"{rel}: top-level matplotlib import")
    assert offenders == [], offenders
