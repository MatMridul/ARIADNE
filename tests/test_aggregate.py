"""Phase 3 tests: per-window aggregation + rolling baseline."""
from ariadne.model.entities import Method, Transaction
from ariadne.model.graph import default_graph
from ariadne.observe.aggregate import (
    method_stats,
    psp_stats,
    window_stats,
)


def _txn(window, i, psp, method, success, tpw=500):
    return Transaction(
        txn_id=f"w{window}-t{i}",
        timestamp=float(window * tpw + i),
        method=method,
        psp_id=psp,
        bank_id="bank_A",
        amount=1000.0,
        success=success,
        failure_code=None if success else "X",
        latency_ms=100.0,
        cohort="returning",
        geography="north",
    )


def test_rate_volume_and_latency():
    txns = [
        _txn(0, 0, "psp_1", Method.UPI, True),
        _txn(0, 1, "psp_1", Method.UPI, True),
        _txn(0, 2, "psp_1", Method.UPI, False),
        _txn(0, 3, "psp_2", Method.CARD, True),
    ]
    stats = window_stats(txns, default_graph(), window=0)
    psps = psp_stats(stats)
    assert psps["psp_1"].volume == 3
    assert abs(psps["psp_1"].success_rate - 2 / 3) < 1e-9
    assert psps["psp_1"].avg_latency_ms == 100.0
    # method view aggregates independently
    meth = method_stats(stats)
    assert meth["upi"].volume == 3
    assert meth["card"].volume == 1


def test_rolling_baseline_and_delta():
    # window 0: psp_1 all success; window 1: psp_1 half success -> negative delta
    txns = [
        _txn(0, 0, "psp_1", Method.UPI, True),
        _txn(0, 1, "psp_1", Method.UPI, True),
        _txn(1, 0, "psp_1", Method.UPI, True),
        _txn(1, 1, "psp_1", Method.UPI, False),
    ]
    stats = window_stats(txns, default_graph(), window=1)
    s = psp_stats(stats)["psp_1"]
    assert s.baseline_rate == 1.0  # prior window all success
    assert s.success_rate == 0.5
    assert abs(s.delta - (-0.5)) < 1e-9


def test_no_history_gives_zero_delta():
    txns = [_txn(0, 0, "psp_1", Method.UPI, False)]
    stats = window_stats(txns, default_graph(), window=0)
    s = psp_stats(stats)["psp_1"]
    assert s.delta == 0.0  # no prior windows -> baseline = self
