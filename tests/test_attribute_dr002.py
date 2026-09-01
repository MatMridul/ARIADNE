"""DR-002 regression: attribution branch disambiguation (E6 fix).

These encode the SEMANTIC cases (spread vs. concentrated failure), not target
numbers, per the repair mandate. Synthetic NodeStats windows exercise the exact
seven required cases. No simulator / no ground truth here.
"""
from ariadne.diagnosis.attribute import attribute
from ariadne.diagnosis.detect import detect
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats

G = default_graph()


def _p(nid, rate, base):
    return NodeStats(nid, "psp", rate, 500, 120.0, base, rate - base)


def _m(nid, rate, base):
    return NodeStats(nid, "method", rate, 500, 120.0, base, rate - base)


def _spread_methods(drop):
    # all methods drop ~equally by `drop` (PSP/bank-localized signature)
    return {
        "method:upi": _m("upi", 0.96 - drop, 0.96),
        "method:card": _m("card", 0.95 - drop, 0.95),
        "method:netbanking": _m("netbanking", 0.93 - drop, 0.93),
    }


def _run(stats):
    return attribute(stats, G, detect(stats, 0.05))


def test_case1_diff_bank_psps_independent():
    # psp_1 (bank_A) + psp_3 (bank_B) down; psp_2 healthy; methods spread
    stats = {
        "psp:psp_1": _p("psp_1", 0.70, 0.96),
        "psp:psp_2": _p("psp_2", 0.95, 0.95),
        "psp:psp_3": _p("psp_3", 0.68, 0.93),
        **_spread_methods(0.16),
    }
    r = _run(stats)
    assert r.root_cause_kind == "psp"
    assert sorted(r.psp_causes) == ["psp_1", "psp_3"]


def test_case2_overlapping_diff_bank_psps_independent():
    # same structure, both firmly down together (the overlap that used to hijack)
    stats = {
        "psp:psp_1": _p("psp_1", 0.72, 0.96),
        "psp:psp_2": _p("psp_2", 0.94, 0.95),
        "psp:psp_3": _p("psp_3", 0.70, 0.93),
        **_spread_methods(0.15),
    }
    r = _run(stats)
    assert r.root_cause_kind == "psp"  # NOT method (was the E6 bug)
    assert sorted(r.psp_causes) == ["psp_1", "psp_3"]


def test_case3_shared_bank():
    stats = {
        "psp:psp_1": _p("psp_1", 0.70, 0.96),
        "psp:psp_2": _p("psp_2", 0.68, 0.95),
        "psp:psp_3": _p("psp_3", 0.95, 0.95),
        **_spread_methods(0.15),
    }
    r = _run(stats)
    assert r.root_cause_kind == "bank"
    assert r.root_cause_id == "bank_A"


def test_case4_all_psps_down_not_bank():
    # coverage(bank_A)=1.0 but specificity 0.67 < 0.8 -> must NOT be bank
    stats = {
        "psp:psp_1": _p("psp_1", 0.70, 0.96),
        "psp:psp_2": _p("psp_2", 0.70, 0.95),
        "psp:psp_3": _p("psp_3", 0.70, 0.93),
        **_spread_methods(0.15),
    }
    r = _run(stats)
    assert r.root_cause_kind != "bank"


def test_case5_method_wide_degradation():
    # card concentrated: card dominates, others near baseline; PSPs mildly diluted
    stats = {
        "psp:psp_1": _p("psp_1", 0.88, 0.96),
        "psp:psp_2": _p("psp_2", 0.87, 0.95),
        "psp:psp_3": _p("psp_3", 0.86, 0.94),
        "method:upi": _m("upi", 0.955, 0.96),
        "method:card": _m("card", 0.72, 0.95),
        "method:netbanking": _m("netbanking", 0.92, 0.93),
    }
    r = _run(stats)
    assert r.root_cause_kind == "method"
    assert r.root_cause_id == "card"


def test_case6_one_psp():
    stats = {
        "psp:psp_1": _p("psp_1", 0.70, 0.96),
        "psp:psp_2": _p("psp_2", 0.95, 0.95),
        "psp:psp_3": _p("psp_3", 0.95, 0.95),
        **_spread_methods(0.05),
    }
    r = _run(stats)
    assert r.root_cause_kind == "psp"
    assert r.root_cause_id == "psp_1"


def test_case7_noise_none():
    stats = {
        "psp:psp_1": _p("psp_1", 0.955, 0.96),
        "psp:psp_2": _p("psp_2", 0.945, 0.95),
        "psp:psp_3": _p("psp_3", 0.955, 0.95),
        **_spread_methods(0.01),
    }
    r = _run(stats)
    assert r.root_cause_kind == "none"


def test_spread_failure_is_not_a_method_fault():
    # explicit semantic guard: two PSPs down + methods spread evenly -> NOT method
    stats = {
        "psp:psp_1": _p("psp_1", 0.70, 0.96),
        "psp:psp_2": _p("psp_2", 0.95, 0.95),
        "psp:psp_3": _p("psp_3", 0.68, 0.93),
        **_spread_methods(0.16),  # concentration ~0 -> method branch must not fire
    }
    r = _run(stats)
    assert r.root_cause_kind != "method"
