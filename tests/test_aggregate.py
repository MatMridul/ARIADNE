"""Tests for observe/aggregate.py (BUILD_ORDER step 8).

Uses controlled, hand-built transactions so per-PSP / per-method success_rate,
volume, and delta-vs-rolling-baseline are exactly predictable. Also asserts the
non-negotiable invariant that observation never imports simulator ground truth.
"""

import ast
import pathlib

from ariadne.model.entities import Method, Transaction
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import NodeStats, window_stats


def _txn(txn_id, window, method, psp_id, bank_id, success, latency=100.0):
    return Transaction(
        txn_id=txn_id,
        timestamp=window + 0.0,
        method=method,
        psp_id=psp_id,
        bank_id=bank_id,
        amount=100.0,
        success=success,
        failure_code=None if success else "DECLINED",
        latency_ms=latency,
        cohort="new",
        geography="north",
    )


def _controlled_stream():
    """Window 0: psp_1 4/5 success. Window 1: psp_1 2/5 success (a drop)."""
    txns = []
    n = 0
    # window 0 — psp_1 via UPI on bank_A: 4 success, 1 fail
    for i in range(5):
        n += 1
        txns.append(_txn(f"a{n}", 0, Method.UPI, "psp_1", "bank_A", i < 4, latency=100.0))
    # window 1 — psp_1 via UPI: 2 success, 3 fail
    for i in range(5):
        n += 1
        txns.append(_txn(f"b{n}", 1, Method.UPI, "psp_1", "bank_A", i < 2, latency=200.0))
    return txns


def test_window_stats_produces_psp_and_method_nodestats():
    g = default_graph()
    txns = _controlled_stream()
    stats = window_stats(txns, g, 0)

    assert "psp_1" in stats
    assert "method_upi" in stats
    assert isinstance(stats["psp_1"], NodeStats)
    assert stats["psp_1"].node_kind == "psp"
    assert stats["method_upi"].node_kind == "method"

    # no bank-level stats are produced by observation
    assert not any(v.node_kind.startswith("bank") for v in stats.values())


def test_success_rate_and_volume_are_exact():
    g = default_graph()
    txns = _controlled_stream()
    w0 = window_stats(txns, g, 0)
    assert w0["psp_1"].volume == 5
    assert w0["psp_1"].success_rate == 4 / 5
    assert w0["method_upi"].success_rate == 4 / 5


def test_first_window_baseline_falls_back_to_current_rate():
    g = default_graph()
    txns = _controlled_stream()
    w0 = window_stats(txns, g, 0)
    # no prior windows → baseline equals current rate → delta 0
    assert w0["psp_1"].baseline_rate == 4 / 5
    assert w0["psp_1"].delta == 0.0


def test_rolling_baseline_and_delta_reflect_prior_windows():
    g = default_graph()
    txns = _controlled_stream()
    w1 = window_stats(txns, g, 1)
    # window 1 current rate is 2/5; baseline is the prior window's 4/5.
    assert w1["psp_1"].success_rate == 2 / 5
    assert w1["psp_1"].baseline_rate == 4 / 5
    assert w1["psp_1"].delta == (2 / 5) - (4 / 5)
    # latency averages the current window only
    assert w1["psp_1"].avg_latency_ms == 200.0


def test_aggregate_does_not_import_incidents():
    """Hard architectural invariant: observation must never see ground truth."""
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "ariadne" / "observe" / "aggregate.py"
    tree = ast.parse(src.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any("incidents" in mod for mod in imported), imported
