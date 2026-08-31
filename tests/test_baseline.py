"""Phase 5 — the discrimination gap exists (BUILD_SPEC §5).

On a shared-bank window the baseline returns multiple INDEPENDENT PSP faults, never
a bank (proves the gap). On a coincidental (E) window the baseline is CORRECT
(independent PSPs) -- so the A-vs-E contrast isolates ARIADNE's real advantage.
"""
from ariadne.baseline.independent import baseline_attribute
from ariadne.observe.aggregate import NodeStats


def _psp(node_id, rate, baseline):
    return NodeStats(node_id, "psp", rate, 500, 120.0, baseline, rate - baseline)


def test_baseline_never_blames_a_bank_on_shared_bank_window():
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.68, 0.95),
        "psp:psp_3": _psp("psp_3", 0.95, 0.95),
    }
    attr = baseline_attribute(stats, detect_threshold=0.05)
    assert attr.root_cause_kind == "psp"  # cannot see the shared bank
    assert attr.root_cause_kind != "bank"
    assert sorted(attr.psp_causes) == ["psp_1", "psp_2"]


def test_baseline_correct_on_coincidental_window():
    # two PSPs on different banks down -> independent PSPs is the RIGHT answer
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.95, 0.95),
        "psp:psp_3": _psp("psp_3", 0.68, 0.93),
    }
    attr = baseline_attribute(stats, detect_threshold=0.05)
    assert attr.root_cause_kind == "psp"
    assert sorted(attr.psp_causes) == ["psp_1", "psp_3"]


def test_baseline_none_when_nothing_breaches():
    stats = {
        "psp:psp_1": _psp("psp_1", 0.955, 0.96),
        "psp:psp_2": _psp("psp_2", 0.95, 0.95),
    }
    attr = baseline_attribute(stats, detect_threshold=0.05)
    assert attr.root_cause_kind == "none"


def test_baseline_sees_same_inputs_as_ariadne_but_no_graph():
    # baseline_attribute's signature takes NO graph -> structurally cannot use it
    import inspect
    sig = inspect.signature(baseline_attribute)
    assert "graph" not in sig.parameters
