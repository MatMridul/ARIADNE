"""The discrimination-gap test (BUILD_SPEC §5, §3.9, BUILD_ORDER step 16).

The fair non-relational baseline sees the SAME per-node ``NodeStats`` ARIADNE
sees, but has NO graph. So:

  * on the shared-bank window (both PSPs on bank_A down) it blames MULTIPLE
    INDEPENDENT PSPs, NEVER a bank — this proves the discrimination gap exists;
  * on the coincidental-E window (two PSPs on different banks down together) it is
    CORRECT (two independent PSPs) — so the A-vs-E contrast is exactly what
    isolates ARIADNE's real advantage, not a strawman.

Fixtures are built DIRECTLY from ``NodeStats`` — never from ground truth. If the
baseline needed ground truth, the test would be wrong.
"""

import ast
import pathlib

from ariadne.baseline.independent import baseline_attribute
from ariadne.observe.aggregate import NodeStats

_DETECT_THRESHOLD = 0.05


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


def test_shared_bank_window_baseline_blames_independent_psps_never_a_bank():
    """Both PSPs on bank_A (psp_1, psp_2) down; psp_3 healthy.

    ARIADNE would blame bank_A; the baseline has no graph, so it blames psp_1 and
    psp_2 independently and can NEVER report a bank.
    """
    stats = {
        "psp_1": _psp("psp_1", 0.60, 0.95),
        "psp_2": _psp("psp_2", 0.58, 0.95),
        "psp_3": _psp("psp_3", 0.94, 0.95),
    }
    attr = baseline_attribute(stats, _DETECT_THRESHOLD)
    assert attr.root_cause_kind == "psp"
    assert attr.root_cause_kind != "bank"
    blamed = {attr.root_cause_id, *attr.secondary_causes}
    assert blamed == {"psp_1", "psp_2"}
    assert 0.0 < attr.confidence <= 1.0
    assert attr.evidence_path


def test_coincidental_window_baseline_is_correct_two_independent_psps():
    """psp_1 (bank_A) and psp_3 (bank_B) drop together by chance.

    Here the non-relational per-node reasoning is the RIGHT answer: two independent
    PSP faults. This is why the A-vs-E contrast isolates ARIADNE's advantage.
    """
    stats = {
        "psp_1": _psp("psp_1", 0.60, 0.95),
        "psp_2": _psp("psp_2", 0.94, 0.95),
        "psp_3": _psp("psp_3", 0.58, 0.95),
    }
    attr = baseline_attribute(stats, _DETECT_THRESHOLD)
    assert attr.root_cause_kind == "psp"
    blamed = {attr.root_cause_id, *attr.secondary_causes}
    assert blamed == {"psp_1", "psp_3"}


def test_single_psp_window_baseline_blames_that_psp():
    stats = {
        "psp_1": _psp("psp_1", 0.55, 0.95),
        "psp_2": _psp("psp_2", 0.94, 0.95),
        "psp_3": _psp("psp_3", 0.95, 0.95),
    }
    attr = baseline_attribute(stats, _DETECT_THRESHOLD)
    assert attr.root_cause_kind == "psp"
    assert attr.root_cause_id == "psp_1"
    assert not attr.secondary_causes


def test_noise_window_baseline_returns_none():
    stats = {
        "psp_1": _psp("psp_1", 0.945, 0.95),
        "psp_2": _psp("psp_2", 0.948, 0.95),
        "psp_3": _psp("psp_3", 0.951, 0.95),
    }
    attr = baseline_attribute(stats, _DETECT_THRESHOLD)
    assert attr.root_cause_kind == "none"
    assert attr.confidence == 0.0


def test_baseline_does_not_import_incidents_or_ground_truth():
    """SEAL: the baseline never references simulator ground truth."""
    src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "ariadne"
        / "baseline"
        / "independent.py"
    )
    tree = ast.parse(src.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("incidents" in mod for mod in imported), imported
    names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert "GroundTruth" not in names
    assert "Incident" not in names
