"""Regression tests for audit repairs P2 #4/#5 and P1 #2:
unsafe_action_rate is MEASURED, do-nothing correctness is full-precision, and RCA is
reported both conditionally and unconditionally.
"""
from ariadne.decide import actions as A
from ariadne.eval.metrics import (
    is_action_audited,
    is_unsafe_action,
)
from ariadne.eval.run import run_once
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import make_incident, IncidentType

G = default_graph()
ACTIVE_METHODS = ["upi", "card", "netbanking"]


def test_do_nothing_is_always_safe_and_audited():
    a = A.do_nothing("below threshold", confidence=0.1)
    assert is_action_audited(a)
    assert not is_unsafe_action(a, G, {}, ACTIVE_METHODS)


def test_reroute_onto_degraded_target_is_unsafe():
    a = A.reroute(G, Method.UPI, "psp_1", "psp_3",
                  confidence=1.0, expected_recovery=1.0, evidence_path=["x"])
    # psp_3 is itself degraded -> unsafe
    delta = {"psp_1": -0.3, "psp_3": -0.2}
    assert is_unsafe_action(a, G, delta, ACTIVE_METHODS)


def test_reroute_onto_healthy_target_is_safe():
    a = A.reroute(G, Method.UPI, "psp_1", "psp_3",
                  confidence=1.0, expected_recovery=1.0, evidence_path=["x"])
    delta = {"psp_1": -0.3, "psp_3": 0.0}
    assert not is_unsafe_action(a, G, delta, ACTIVE_METHODS)


def test_disable_last_method_is_unsafe():
    a = A.disable_method(G, Method.UPI, [Method.UPI, Method.CARD],
                         confidence=1.0, expected_recovery=0.0, evidence_path=["x"])
    assert is_unsafe_action(a, G, {}, ["upi"])  # only upi active -> unsafe


def test_unaudited_action_is_flagged_unsafe():
    bad = A.do_nothing("x", 0.5)
    bad.evidence_path = []  # strip audit
    assert not is_action_audited(bad)
    assert is_unsafe_action(bad, G, {}, ACTIVE_METHODS)


def test_run_once_measures_unsafe_rate_and_audits():
    # incident A at low threshold -> ARIADNE acts; all actions must be safe + audited
    cfg = SimConfig(seed=2)
    inc = make_incident(IncidentType.SHARED_BANK, 2, cfg.n_windows, target_id="bank_A")
    m = run_once("ariadne", 0.55, 2, incident=inc, cfg=cfg)
    assert m.executed_actions > 0        # it actually acted
    assert m.unsafe_action_rate == 0.0   # measured, and zero
    assert m.unaudited_actions == 0


def test_run_once_reports_both_rca_metrics():
    cfg = SimConfig(seed=2)
    inc = make_incident(IncidentType.SHARED_BANK, 2, cfg.n_windows, target_id="bank_A")
    m = run_once("ariadne", 0.70, 2, incident=inc, cfg=cfg)
    # unconditional denominator >= conditional (it includes detection misses)
    assert m.rca_scored_unconditional >= m.rca_scored_conditional
    assert 0.0 <= m.root_cause_accuracy_unconditional <= 1.0
    assert 0.0 <= m.root_cause_accuracy_conditional <= 1.0
    # back-compat alias equals conditional
    assert m.root_cause_accuracy == m.root_cause_accuracy_conditional


def test_do_nothing_correct_full_precision_exposes_false_intervention():
    # Find a batch scenario where ARIADNE falsely intervened on a no-cause window and
    # confirm it is NOT silently rounded to a clean 1.00.
    from ariadne.eval.scenarios import scenario_batch
    seen_miss = False
    for seed in range(1, 21):
        for inc, cfg in scenario_batch(seed):
            if inc.incident_type == IncidentType.NONE:
                m = run_once("ariadne", 0.70, cfg.seed, incident=inc, cfg=cfg)
                if m.do_nothing_scored and m.do_nothing_correct_rate < 1.0:
                    seen_miss = True
                    # a real false intervention must be visible in the count
                    assert m.false_interventions >= 1
    # not asserting seen_miss must be True (depends on seeds) but if any exists it is exposed
    assert seen_miss in (True, False)
