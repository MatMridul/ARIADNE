"""Phase 7 (Tier-2) — disable_method + retry_fallback actions and their policy paths."""
from ariadne.decide import actions as A
from ariadne.decide.policy import apply_action, apply_action_config, select_action
from ariadne.diagnosis.attribute import Attribution
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats
from ariadne.simulator.config import SimConfig


def _method(node_id, rate, baseline, volume=500):
    return NodeStats(node_id, "method", rate, volume, 120.0, baseline, rate - baseline)


def test_method_cause_mild_prefers_retry_fallback():
    g = default_graph()
    stats = {"method:card": _method("card", 0.75, 0.95)}  # down but not severe
    attr = Attribution("card", "method", confidence=0.9)
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "retry_fallback"
    assert action.params["method"] == "card"
    assert 1 <= action.params["max_retries"] <= 3


def test_method_cause_severe_disables_method_when_fallback_exists():
    g = default_graph()
    stats = {"method:card": _method("card", 0.30, 0.95)}  # severely down
    attr = Attribution("card", "method", confidence=0.9)
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "disable_method"
    assert action.params["method"] == "card"


def test_disable_method_refuses_last_working_method():
    g = default_graph()
    # collapse routing so only CARD is active -> disabling it is refused
    for m in list(g.routing.keys()):
        if m != Method.CARD:
            g.routing[m] = [(p, 0.0) for p, _w in g.routing[m]]
    stats = {"method:card": _method("card", 0.20, 0.95)}
    attr = Attribution("card", "method", confidence=1.0)
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    # cannot disable the last method -> falls back to retry (still additive/safe)
    assert action.kind == "retry_fallback"


def test_retry_fallback_config_applied_for_counterfactual():
    cfg = SimConfig(seed=1)
    action = A.retry_fallback(
        Method.CARD, max_retries=2, retriable_codes=["GATEWAY_TIMEOUT"],
        confidence=1.0, expected_recovery=0.0, evidence_path=[],
    )
    new_cfg = apply_action_config(cfg, action)
    assert new_cfg.retry_method == "card"
    assert new_cfg.retry_max == 2
    assert "GATEWAY_TIMEOUT" in new_cfg.retry_codes
    # graph is unchanged for a retry action
    g = default_graph()
    assert apply_action(g, action) is g


def test_disable_method_zeroes_routing_in_apply_action():
    g = default_graph()
    action = A.disable_method(
        g, Method.CARD, [Method.UPI, Method.CARD, Method.NETBANKING],
        confidence=1.0, expected_recovery=0.0, evidence_path=[],
    )
    g2 = apply_action(g, action)
    assert all(w == 0.0 for _p, w in g2.routing[Method.CARD])
    # other methods untouched
    assert any(w > 0.0 for _p, w in g2.routing[Method.UPI])
