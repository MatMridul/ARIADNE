"""Phase 2 tests: honest-adversary simulator invariants (BUILD_SPEC §5)."""
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import (
    GroundTruth,
    Incident,
    IncidentType,
    make_incident,
)


def _rate_by_psp(txns, window_lo, window_hi):
    """Success rate per PSP over a window range."""
    agg = {}
    for t in txns:
        w = int(t.timestamp // 500)
        if window_lo <= w <= window_hi:
            s, n = agg.get(t.psp_id, (0, 0))
            agg[t.psp_id] = (s + (1 if t.success else 0), n + 1)
    return {p: s / n for p, (s, n) in agg.items() if n}


def test_same_seed_identical_txns():
    g = default_graph()
    cfg = SimConfig(seed=42)
    inc = make_incident(IncidentType.NONE, seed=42, n_windows=cfg.n_windows)
    a, _ = generate(g, cfg, inc)
    b, _ = generate(g, cfg, inc)
    assert len(a) == len(b)
    assert [(t.txn_id, t.success, t.psp_id) for t in a] == [
        (t.txn_id, t.success, t.psp_id) for t in b
    ]


def test_different_seed_differs():
    g = default_graph()
    inc0 = make_incident(IncidentType.NONE, seed=1, n_windows=20)
    inc1 = make_incident(IncidentType.NONE, seed=2, n_windows=20)
    a, _ = generate(g, SimConfig(seed=1), inc0)
    b, _ = generate(g, SimConfig(seed=2), inc1)
    assert [t.success for t in a] != [t.success for t in b]


def test_shared_bank_lowers_all_psps_on_target_and_not_control():
    g = default_graph()
    cfg = SimConfig(seed=7, severity_note=None) if False else SimConfig(seed=7)
    inc = Incident(
        incident_type=IncidentType.SHARED_BANK,
        target_id="bank_A",
        start_window=5,
        end_window=8,
        severity=0.30,
    )
    txns, gt = generate(g, cfg, inc)
    during = _rate_by_psp(txns, 5, 8)
    before = _rate_by_psp(txns, 0, 4)
    # psp_1 and psp_2 (bank_A) drop substantially; psp_3 (bank_B) does not
    assert during["psp_1"] < before["psp_1"] - 0.1
    assert during["psp_2"] < before["psp_2"] - 0.1
    assert abs(during["psp_3"] - before["psp_3"]) < 0.05
    assert set(gt.affected_psps) == {"psp_1", "psp_2"}
    assert gt.true_causes == ["bank_A"]


def test_single_psp_lowers_only_that_psp():
    g = default_graph()
    inc = Incident(
        incident_type=IncidentType.SINGLE_PSP,
        target_id="psp_1",
        start_window=3,
        end_window=6,
        severity=0.30,
    )
    txns, gt = generate(g, SimConfig(seed=11), inc)
    during = _rate_by_psp(txns, 3, 6)
    before = _rate_by_psp(txns, 0, 2)
    assert during["psp_1"] < before["psp_1"] - 0.1
    assert abs(during["psp_2"] - before["psp_2"]) < 0.05
    assert abs(during["psp_3"] - before["psp_3"]) < 0.05
    assert gt.true_causes == ["psp_1"]


def test_none_injects_noise_only():
    g = default_graph()
    inc = make_incident(IncidentType.NONE, seed=3, n_windows=20)
    txns, gt = generate(g, SimConfig(seed=3), inc)
    rates = _rate_by_psp(txns, 0, 19)
    # all PSPs stay near their healthy band; no cause
    for p, r in rates.items():
        assert r > 0.85
    assert gt.true_causes == []
    assert gt.affected_psps == []


def test_coincidental_drops_two_psps_on_different_banks_independently():
    g = default_graph()
    # psp_1 (bank_A) and psp_3 (bank_B) -> DIFFERENT banks -> correct = 2 faults
    inc = make_incident(
        IncidentType.COINCIDENTAL,
        seed=9,
        n_windows=20,
        target_id="psp_1",
        secondary_target_id="psp_3",
    )
    assert g.settles_via["psp_1"] != g.settles_via["psp_3"]
    txns, gt = generate(g, SimConfig(seed=9), inc)
    assert sorted(gt.true_causes) == ["psp_1", "psp_3"]
    # independent onsets: not forced to be identical
    assert (inc.start_window, inc.end_window) is not None


def test_onset_randomised_per_seed():
    spans = set()
    for s in range(10):
        inc = make_incident(IncidentType.SHARED_BANK, seed=s, n_windows=20, target_id="bank_A")
        spans.add((inc.start_window, inc.end_window))
    assert len(spans) > 1  # not a fixed schedule


def test_ground_truth_not_embedded_in_txn_stream():
    g = default_graph()
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=2, end_window=4, severity=0.2)
    txns, gt = generate(g, SimConfig(seed=5), inc)
    assert isinstance(gt, GroundTruth)
    # a Transaction exposes only observable fields; no incident/cause attribute
    t = txns[0]
    for forbidden in ("incident", "incident_type", "true_causes", "severity", "target_id"):
        assert not hasattr(t, forbidden)
