"""Policy / action-selection tests (BUILD_SPEC §5, §3.11, §3.10).

  * below threshold -> do_nothing (the safety default)
  * a confident bank diagnosis -> a bounded reroute onto a HEALTHY sibling
  * never reroute onto a node the graph shows is also bad
  * the action model refuses an out-of-bounds reroute (onto a bad node)

Fixtures are built directly from Attribution + NodeStats — no ground truth.
"""

import pytest

from ariadne.decide.actions import Action, do_nothing, reroute
from ariadne.decide.policy import select_action
from ariadne.diagnosis.attribute import Attribution
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats


def _psp(node_id, success_rate, volume=500):
    return NodeStats(
        node_id=node_id,
        node_kind="psp",
        success_rate=success_rate,
        volume=volume,
        avg_latency_ms=120.0,
        baseline_rate=0.95,
        delta=success_rate - 0.95,
    )


def _bank_attr(confidence):
    return Attribution(
        root_cause_id="bank_A",
        root_cause_kind="bank",
        confidence=confidence,
        evidence_path=["bank_A shared dependency"],
    )


def test_below_threshold_does_nothing():
    g = default_graph()
    stats = {"psp_1": _psp("psp_1", 0.6), "psp_2": _psp("psp_2", 0.6), "psp_3": _psp("psp_3", 0.95)}
    attr = _bank_attr(0.5)
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "do_nothing"
    assert action.confidence == 0.5


def test_none_attribution_does_nothing_regardless_of_threshold():
    g = default_graph()
    stats = {"psp_1": _psp("psp_1", 0.95)}
    attr = Attribution("", "none", 0.0, ["nothing breached"])
    action = select_action(attr, g, stats, intervention_threshold=0.0)
    assert action.kind == "do_nothing"


def test_above_threshold_reroutes_to_a_healthy_sibling():
    """bank_A bad -> psp_1 & psp_2 bad; psp_3 (bank_B) healthy is the only target."""
    g = default_graph()
    stats = {
        "psp_1": _psp("psp_1", 0.60),
        "psp_2": _psp("psp_2", 0.58),
        "psp_3": _psp("psp_3", 0.95),
    }
    attr = _bank_attr(0.95)
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "reroute"
    # target must be the healthy sibling, never a bad node
    assert action.params["to_psp"] == "psp_3"
    assert action.params["from_psp"] in {"psp_1", "psp_2"}
    assert action.expected_recovery > 0.0


def test_never_reroutes_onto_a_bad_node():
    """If every sibling for the bad PSPs is also bad, hold instead of rerouting."""
    g = default_graph()
    # all three PSPs bad -> no healthy target anywhere -> do_nothing
    stats = {
        "psp_1": _psp("psp_1", 0.55),
        "psp_2": _psp("psp_2", 0.55),
        "psp_3": _psp("psp_3", 0.55),
    }
    attr = Attribution(
        root_cause_id="psp_1",
        root_cause_kind="psp",
        confidence=0.9,
        evidence_path=["psp_1 down"],
        secondary_causes=["psp_2", "psp_3"],
    )
    action = select_action(attr, g, stats, intervention_threshold=0.70)
    assert action.kind == "do_nothing"


def test_reroute_builder_refuses_out_of_bounds_target():
    g = default_graph()
    # NETBANKING is carried by psp_1 and psp_2; psp_2 is marked bad -> refuse.
    with pytest.raises(ValueError):
        reroute(
            g,
            Method.NETBANKING,
            from_psp="psp_1",
            to_psp="psp_2",
            bad_nodes={"psp_1", "psp_2"},
            expected_recovery=1.0,
            confidence=0.9,
        )


def test_reroute_builder_refuses_psp_not_carrying_method():
    g = default_graph()
    # UPI is carried by psp_1 and psp_3, NOT psp_2.
    with pytest.raises(ValueError):
        reroute(
            g,
            Method.UPI,
            from_psp="psp_2",
            to_psp="psp_3",
            bad_nodes=set(),
            expected_recovery=1.0,
            confidence=0.9,
        )


def test_do_nothing_builder_is_first_class():
    a = do_nothing("confidence below threshold", 0.3)
    assert isinstance(a, Action)
    assert a.kind == "do_nothing"
    assert a.decision_id
    assert a.expected_recovery == 0.0
