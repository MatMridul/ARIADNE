"""Phase 4 — metrics on hand-built fixtures (BUILD_SPEC §5)."""
from ariadne.decide import actions as A
from ariadne.eval.metrics import (
    captured_revenue,
    money_recovered,
    root_cause_hit,
)
from ariadne.model.entities import Method, Transaction
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import GroundTruth, Incident, IncidentType


def _txn(psp, success, amount=100.0):
    return Transaction("id", 0.0, Method.UPI, psp, "bank_A", amount, success,
                       None if success else "X", 100.0, "returning", "north")


def test_captured_revenue_sums_only_successes():
    txns = [_txn("psp_1", True, 100.0), _txn("psp_1", False, 50.0), _txn("psp_2", True, 25.0)]
    assert captured_revenue(txns) == 125.0


def test_money_recovered_shared_seed_counterfactual_positive_on_reroute():
    g = default_graph()
    cfg = SimConfig(seed=3)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=4, end_window=8, severity=0.30)
    # reroute bad bank_A PSP onto healthy psp_3 (bank_B)
    action = A.reroute(g, Method.UPI, "psp_1", "psp_3",
                       confidence=1.0, expected_recovery=0.0, evidence_path=[])
    rec = money_recovered(g, cfg, inc, action)
    assert rec > 0  # moving traffic off the degraded bank recovers revenue


def test_money_recovered_do_nothing_is_zero():
    g = default_graph()
    cfg = SimConfig(seed=3)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=4, end_window=8, severity=0.30)
    action = A.do_nothing("below threshold", confidence=0.1)
    rec = money_recovered(g, cfg, inc, action)
    assert rec == 0.0  # identical config -> identical draws -> zero delta


def test_root_cause_hit_scoring():
    g = default_graph()
    # incident A: true cause bank_A
    gt_a = GroundTruth(Incident(IncidentType.SHARED_BANK, "bank_A"), ["psp_1", "psp_2"], [], ["bank_A"])
    assert root_cause_hit(gt_a, ["bank_A"]) is True
    assert root_cause_hit(gt_a, ["psp_1", "psp_2"]) is False  # blaming PSPs = miss

    # incident E: true causes two PSPs
    gt_e = GroundTruth(Incident(IncidentType.COINCIDENTAL, "psp_1", "psp_3"), ["psp_1", "psp_3"], [], ["psp_1", "psp_3"])
    assert root_cause_hit(gt_e, ["psp_1", "psp_3"]) is True
    assert root_cause_hit(gt_e, ["bank_A"]) is False  # over-attribution = miss

    # incident D: no cause -> correct iff nothing blamed
    gt_d = GroundTruth(Incident(IncidentType.NONE, None), [], [], [])
    assert root_cause_hit(gt_d, []) is True
    assert root_cause_hit(gt_d, ["psp_1"]) is False
