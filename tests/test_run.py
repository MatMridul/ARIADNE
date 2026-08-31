"""Phase 6 — sweep produces the discrimination result + a frontier (BUILD_SPEC §5)."""
from ariadne.eval.sweep import run_sweep


def test_sweep_produces_a_point_per_threshold_per_system():
    res = run_sweep(seeds=[1], thresholds=(0.55, 0.70, 0.85), include_discrimination=False)
    for system in ("ariadne", "baseline"):
        pts = res["frontier"][system]
        assert len(pts) == 3  # one point per threshold
        assert sorted(p["threshold"] for p in pts) == [0.55, 0.70, 0.85]
        for p in pts:
            assert "money_recovered" in p and "false_intervention_cost" in p


def test_sweep_discrimination_ariadne_beats_baseline_on_A_no_regression_on_B_and_E():
    res = run_sweep(seeds=[1, 2], thresholds=(0.70,))
    d = res["discrimination"]
    assert d["A_ariadne_beats_baseline_rca"] is True
    assert d["A_ariadne_beats_baseline_money"] is True
    assert d["B_no_regression"] is True
    assert d["E_ariadne_not_over_attributes"] is True


def test_ariadne_recovers_at_least_as_much_as_baseline_across_thresholds():
    res = run_sweep(seeds=[1, 2], thresholds=(0.55, 0.70, 0.85), include_discrimination=False)
    a = {p["threshold"]: p["money_recovered"] for p in res["frontier"]["ariadne"]}
    b = {p["threshold"]: p["money_recovered"] for p in res["frontier"]["baseline"]}
    for thr in (0.55, 0.70, 0.85):
        assert a[thr] >= b[thr]
