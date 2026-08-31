"""Phase 4 — the thesis test in miniature (BUILD_SPEC §5).

Synthetic NodeStats windows (no simulator dependency here) exercise the four
verdicts. ARIADNE reasons over TOPOLOGY, not correlated-failure counting:
  - shared bank down (all its PSPs)         -> "bank"
  - single PSP down                          -> "psp" (no over-attribution)
  - noise (nothing breaches)                 -> "none"
  - COINCIDENTAL (two PSPs, different banks) -> two INDEPENDENT PSPs, NOT a bank
"""
from ariadne.diagnosis.attribute import attribute
from ariadne.diagnosis.detect import detect
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats


def _psp(node_id, rate, baseline):
    return NodeStats(node_id, "psp", rate, 500, 120.0, baseline, rate - baseline)


def _method(node_id, rate, baseline):
    return NodeStats(node_id, "method", rate, 500, 120.0, baseline, rate - baseline)


def _run(stats):
    g = default_graph()
    det = detect(stats, detect_threshold=0.05)
    return attribute(stats, g, det), det


def test_shared_bank_window_blames_bank():
    # psp_1 & psp_2 (bank_A) both down; psp_3 (bank_B) healthy
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.68, 0.95),
        "psp:psp_3": _psp("psp_3", 0.95, 0.95),
    }
    attr, _ = _run(stats)
    assert attr.root_cause_kind == "bank"
    assert attr.root_cause_id == "bank_A"
    assert 0.0 < attr.confidence <= 1.0
    assert attr.confidence == 1.0  # coverage 1.0 * specificity 1.0


def test_single_psp_window_blames_psp_not_bank():
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),  # only psp_1 down
        "psp:psp_2": _psp("psp_2", 0.95, 0.95),
        "psp:psp_3": _psp("psp_3", 0.95, 0.95),
    }
    attr, _ = _run(stats)
    assert attr.root_cause_kind == "psp"
    assert attr.root_cause_id == "psp_1"  # no over-attribution to bank_A


def test_noise_window_blames_none():
    stats = {
        "psp:psp_1": _psp("psp_1", 0.955, 0.96),
        "psp:psp_2": _psp("psp_2", 0.945, 0.95),
        "psp:psp_3": _psp("psp_3", 0.955, 0.95),
    }
    attr, _ = _run(stats)
    assert attr.root_cause_kind == "none"
    assert attr.confidence == 0.0


def test_coincidental_two_different_banks_blames_two_psps_not_bank():
    # psp_1 (bank_A) and psp_3 (bank_B) down together; psp_2 (bank_A) HEALTHY
    # -> no bank reaches coverage 1.0 with >1 PSP -> two independent faults
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.95, 0.95),
        "psp:psp_3": _psp("psp_3", 0.68, 0.93),
    }
    attr, _ = _run(stats)
    assert attr.root_cause_kind == "psp"
    assert sorted(attr.psp_causes) == ["psp_1", "psp_3"]
    assert attr.root_cause_kind != "bank"  # must NOT over-attribute to a bank


def test_specificity_gate_blocks_bank_when_downset_spills():
    # all three PSPs down: bank_A coverage 1.0 but specificity < 1 (psp_3 spills)
    # specificity(bank_A) = 1 - |{psp_3}|/3 = 0.667 < S_MIN(0.8) -> not a bank verdict
    stats = {
        "psp:psp_1": _psp("psp_1", 0.70, 0.96),
        "psp:psp_2": _psp("psp_2", 0.70, 0.95),
        "psp:psp_3": _psp("psp_3", 0.70, 0.93),
    }
    attr, _ = _run(stats)
    assert attr.root_cause_kind != "bank"
