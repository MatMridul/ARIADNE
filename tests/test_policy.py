"""Phase 4 — policy safety (BUILD_SPEC §5)."""
from ariadne.decide import actions as A
from ariadne.decide.policy import select_action
from ariadne.diagnosis.attribute import Attribution
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats


def _psp(node_id, rate, baseline):
    return NodeStats(node_id, "psp", rate, 500, 120.0, baseline, rate - baseline)


def test_below_threshold_does_nothing():
    g = default_graph()
    stats = {"psp:psp_1": _psp("psp_1", 0.70, 0.96)}
    attr = Attribution("bank_A", "bank", confidence=0.5, psp_causes=["psp_1", "psp_2"])
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "do_nothing"


def test_none_cause_does_nothing():
    g = default_graph()
    attr = Attribution("", "none", confidence=0.0)
    action = select_action(attr, g, {}, intervention_threshold=0.55)
    assert action.kind == "do_nothing"


def test_above_threshold_reroutes_to_healthy_target():
    g = default_graph()
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.68, 0.95),
        "psp:psp_3": _psp("psp_3", 0.95, 0.95),  # healthy control on bank_B
    }
    attr = Attribution("bank_A", "bank", confidence=1.0, psp_causes=["psp_1", "psp_2"])
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "reroute"
    assert action.params["to_psp"] == "psp_3"  # only healthy sibling
    assert action.params["from_psp"] in {"psp_1", "psp_2"}
    assert action.expected_recovery > 0


def test_never_reroutes_onto_a_bad_node():
    g = default_graph()
    # all PSPs bad -> no healthy target -> do_nothing (safety)
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.68, 0.95),
        "psp:psp_3": _psp("psp_3", 0.60, 0.95),
    }
    attr = Attribution("psp_1", "psp", confidence=1.0, psp_causes=["psp_1", "psp_2", "psp_3"])
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "do_nothing"


def test_disable_method_refuses_last_working_method():
    g = default_graph()
    try:
        A.disable_method(g, Method.UPI, active_methods=[Method.UPI],
                         confidence=1.0, expected_recovery=0.0, evidence_path=[])
        assert False, "should refuse to disable the last method"
    except ValueError:
        pass


def test_reroute_rejects_same_source_and_target():
    g = default_graph()
    try:
        A.reroute(g, Method.UPI, "psp_1", "psp_1",
                  confidence=1.0, expected_recovery=0.0, evidence_path=[])
        assert False
    except ValueError:
        pass
