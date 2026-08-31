"""Tests for the simulator (BUILD_SPEC §5 / BUILD_ORDER step 6).

Covers: determinism, SHARED_BANK correlated-failure signal, incident D as
noise-only, COINCIDENTAL two-independent-PSP faults on different banks,
onset/duration/severity variation across seeds, and the invariant that
GroundTruth is returned separately and never embedded in a Transaction.
"""

from ariadne.model.entities import Transaction
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import Incident, IncidentType


def _psp_success_rate(txns, psp_id, w0, w1):
    sel = [t for t in txns if t.psp_id == psp_id and w0 <= int(t.timestamp) <= w1]
    assert sel, f"no txns for {psp_id} in [{w0},{w1}]"
    return sum(t.success for t in sel) / len(sel)


def test_same_seed_produces_identical_transactions():
    g = default_graph()
    cfg_a = SimConfig(seed=123, n_windows=6, txns_per_window=200)
    cfg_b = SimConfig(seed=123, n_windows=6, txns_per_window=200)
    inc_a = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=2, end_window=4, severity=0.3)
    inc_b = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=2, end_window=4, severity=0.3)

    txns_a, _ = generate(g, cfg_a, inc_a)
    txns_b, _ = generate(g, cfg_b, inc_b)

    assert txns_a == txns_b  # byte-identical (dataclass equality on every field)
    assert len(txns_a) == 6 * 200


def test_different_seeds_produce_different_transactions():
    g = default_graph()
    inc = lambda: Incident(IncidentType.NONE, None)
    txns_1, _ = generate(g, SimConfig(seed=1, n_windows=5, txns_per_window=100), inc())
    txns_2, _ = generate(g, SimConfig(seed=2, n_windows=5, txns_per_window=100), inc())
    assert txns_1 != txns_2


def test_shared_bank_lowers_all_psps_on_target_bank_and_nowhere_else():
    g = default_graph()
    cfg = SimConfig(seed=7, n_windows=8, txns_per_window=400)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=3, end_window=6, severity=0.4)
    txns, gt = generate(g, cfg, inc)

    # both PSPs on bank_A are measurably depressed during the incident...
    for psp in ("psp_1", "psp_2"):
        inside = _psp_success_rate(txns, psp, 3, 6)
        outside = _psp_success_rate(txns, psp, 0, 2)
        assert inside < outside - 0.15, f"{psp} not depressed: {inside} vs {outside}"

    # ...and psp_3 (on bank_B) is NOT.
    p3_inside = _psp_success_rate(txns, "psp_3", 3, 6)
    p3_outside = _psp_success_rate(txns, "psp_3", 0, 2)
    assert abs(p3_inside - p3_outside) < 0.1

    assert sorted(gt.affected_psps) == ["psp_1", "psp_2"]
    assert gt.true_causes == ["bank_A"]


def test_incident_d_is_noise_only_no_systematic_target():
    g = default_graph()
    cfg = SimConfig(seed=11, n_windows=10, txns_per_window=400)
    inc = Incident(IncidentType.NONE, None)
    txns, gt = generate(g, cfg, inc)

    # No target: ground truth has no affected paths and no causes.
    assert gt.affected_psps == []
    assert gt.affected_methods == []
    assert gt.true_causes == []

    # No systematic drop: every PSP stays near its healthy rate across windows.
    for psp in ("psp_1", "psp_2", "psp_3"):
        first = _psp_success_rate(txns, psp, 0, 4)
        second = _psp_success_rate(txns, psp, 5, 9)
        assert abs(first - second) < 0.08


def test_coincidental_drops_two_psps_on_different_banks_independently():
    g = default_graph()
    cfg = SimConfig(seed=21, n_windows=10, txns_per_window=400)
    # psp_2 (bank_A) and psp_3 (bank_B) fail together but independently.
    inc = Incident(
        IncidentType.COINCIDENTAL,
        target_id="psp_2",
        secondary_target_id="psp_3",
        start_window=2,
        end_window=5,
        severity=0.4,
        secondary_start_window=3,
        secondary_end_window=6,
        secondary_severity=0.35,
    )
    txns, gt = generate(g, cfg, inc)

    # the two targets sit on different banks
    assert g.settles_via["psp_2"] != g.settles_via["psp_3"]
    assert sorted(gt.affected_psps) == ["psp_2", "psp_3"]
    assert sorted(gt.true_causes) == ["psp_2", "psp_3"]

    # psp_2 depressed in its own window, psp_3 depressed in its own window
    assert _psp_success_rate(txns, "psp_2", 2, 5) < _psp_success_rate(txns, "psp_2", 0, 1) - 0.15
    assert _psp_success_rate(txns, "psp_3", 3, 6) < _psp_success_rate(txns, "psp_3", 0, 1) - 0.15

    # psp_1 (bank_A, not a target) is untouched
    assert abs(
        _psp_success_rate(txns, "psp_1", 2, 6) - _psp_success_rate(txns, "psp_1", 0, 1)
    ) < 0.08


def test_onset_duration_severity_vary_across_seeds():
    g = default_graph()
    schedules = set()
    for seed in range(8):
        cfg = SimConfig(seed=seed, n_windows=20, txns_per_window=50)
        inc = Incident(IncidentType.SINGLE_PSP, "psp_1")  # unpinned → drawn per seed
        generate(g, cfg, inc)
        schedules.add((inc.start_window, inc.end_window, round(inc.severity, 4)))
    # No fixed schedule: the per-seed draws are not all identical.
    assert len(schedules) > 1


def test_ground_truth_is_returned_separately_and_not_on_transaction():
    g = default_graph()
    cfg = SimConfig(seed=5, n_windows=4, txns_per_window=50)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=1, end_window=2, severity=0.3)
    result = generate(g, cfg, inc)

    # generate returns a (txns, GroundTruth) tuple — ground truth is separate.
    assert isinstance(result, tuple) and len(result) == 2
    txns, gt = result
    assert gt.true_causes == ["bank_A"]

    # No Transaction carries any incident / ground-truth field.
    allowed = set(Transaction.__dataclass_fields__.keys())
    forbidden = {"incident", "incident_type", "ground_truth", "groundtruth", "true_causes", "target_id"}
    assert allowed.isdisjoint(forbidden)
    for t in txns:
        for name in forbidden:
            assert not hasattr(t, name)
