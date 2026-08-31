"""The thesis test in miniature (BUILD_SPEC §5, §3.8).

Attribution fixtures are built DIRECTLY from NodeStats + Detection — never from
GroundTruth. That is the point: the diagnoser must reach the right answer from the
observed pattern and the graph topology alone.

  * shared-bank window (both PSPs on bank_A down) -> "bank"
  * single-PSP window                              -> "psp"
  * noise window (nothing breaches)                -> "none"
  * COINCIDENTAL window (two PSPs on DIFFERENT banks down) -> TWO independent PSP
    causes, NOT a bank (proves reasoning over topology, not failure counting)

It also asserts the SEAL: attribute.py imports nothing from simulator/incidents.
"""

import ast
import pathlib

from ariadne.diagnosis.attribute import S_MIN, attribute
from ariadne.diagnosis.detect import Detection
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats


def _psp(node_id, success_rate, baseline_rate, volume=500):
    return NodeStats(
        node_id=node_id,
        node_kind="psp",
        success_rate=success_rate,
        volume=volume,
        avg_latency_ms=120.0,
        baseline_rate=baseline_rate,
        delta=success_rate - baseline_rate,
    )


def test_shared_bank_window_blames_the_bank():
    """Both PSPs on bank_A (psp_1, psp_2) are down; psp_3 (bank_B) is healthy."""
    g = default_graph()
    stats = {
        "psp_1": _psp("psp_1", 0.60, 0.95),
        "psp_2": _psp("psp_2", 0.58, 0.95),
        "psp_3": _psp("psp_3", 0.94, 0.95),
    }
    det = Detection(triggered=True, dropped_nodes=["psp_1", "psp_2"], window=3)
    attr = attribute(stats, g, det)
    assert attr.root_cause_kind == "bank"
    assert attr.root_cause_id == "bank_A"
    # coverage 1.0 (both of bank_A's PSPs) * specificity 1.0 (no spill) = 1.0
    assert attr.confidence == 1.0
    assert attr.claim_type == "hypothesis"
    assert attr.evidence_path  # a real evidence path is built


def test_single_psp_window_blames_that_psp_not_the_bank():
    """Only psp_1 down. bank_A has coverage 0.5 (psp_2 healthy) -> not a bank."""
    g = default_graph()
    stats = {
        "psp_1": _psp("psp_1", 0.55, 0.95),
        "psp_2": _psp("psp_2", 0.94, 0.95),
        "psp_3": _psp("psp_3", 0.95, 0.95),
    }
    det = Detection(triggered=True, dropped_nodes=["psp_1"], window=3)
    attr = attribute(stats, g, det)
    assert attr.root_cause_kind == "psp"
    assert attr.root_cause_id == "psp_1"
    assert not attr.secondary_causes
    assert 0.0 < attr.confidence <= 1.0


def test_noise_window_returns_none():
    g = default_graph()
    stats = {
        "psp_1": _psp("psp_1", 0.945, 0.95),
        "psp_2": _psp("psp_2", 0.948, 0.95),
        "psp_3": _psp("psp_3", 0.951, 0.95),
    }
    det = Detection(triggered=False, dropped_nodes=[], window=3)
    attr = attribute(stats, g, det)
    assert attr.root_cause_kind == "none"
    assert attr.confidence == 0.0


def test_coincidental_window_blames_two_independent_psps_not_a_bank():
    """psp_1 (bank_A) and psp_3 (bank_B) drop together by chance.

    No bank reaches coverage 1.0 with >1 PSP (bank_A has psp_2 healthy, bank_B has
    only psp_3), so the correct answer is TWO independent PSP faults, NOT a shared
    bank cause. This is the A-vs-E anti-cheat.
    """
    g = default_graph()
    stats = {
        "psp_1": _psp("psp_1", 0.60, 0.95),
        "psp_2": _psp("psp_2", 0.94, 0.95),
        "psp_3": _psp("psp_3", 0.58, 0.95),
    }
    det = Detection(triggered=True, dropped_nodes=["psp_1", "psp_3"], window=3)
    attr = attribute(stats, g, det)
    assert attr.root_cause_kind == "psp"
    # both down PSPs are blamed independently
    blamed = {attr.root_cause_id, *attr.secondary_causes}
    assert blamed == {"psp_1", "psp_3"}


def test_s_min_constant_is_named_and_default_zero_point_eight():
    assert S_MIN == 0.8


def test_attribute_does_not_import_incidents_or_ground_truth():
    """SEAL: the diagnoser never references simulator ground truth."""
    src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "ariadne"
        / "diagnosis"
        / "attribute.py"
    )
    tree = ast.parse(src.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("incidents" in mod for mod in imported), imported
    # No name/attribute in executable code references the ground-truth types.
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    assert "GroundTruth" not in names
    assert "Incident" not in names
