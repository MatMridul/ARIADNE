"""Metrics tests (BUILD_SPEC §5, §3.13).

Hand-built transaction fixtures make captured revenue and the shared-seed
money_recovered exactly predictable, INCLUDING a case where money_recovered is
negative (an action that made things worse) — which must be reported, not clamped.
"""

from ariadne.eval.metrics import (
    captured_revenue,
    do_nothing_correct_rate,
    false_intervention_cost,
    money_recovered,
)
from ariadne.model.entities import Method, Transaction


def _txn(window, amount, success):
    return Transaction(
        txn_id="t",
        timestamp=window + 0.0,
        method=Method.UPI,
        psp_id="psp_1",
        bank_id="bank_A",
        amount=amount,
        success=success,
        failure_code=None if success else "DECLINED",
        latency_ms=100.0,
        cohort="new",
        geography="north",
    )


def test_captured_revenue_counts_only_successes():
    txns = [_txn(0, 100.0, True), _txn(0, 50.0, False), _txn(0, 30.0, True)]
    assert captured_revenue(txns) == 130.0


def test_captured_revenue_respects_window_filter():
    txns = [_txn(0, 100.0, True), _txn(1, 200.0, True), _txn(2, 400.0, True)]
    # only windows 1 and 2 count -> 200 + 400
    assert captured_revenue(txns, windows=range(1, 3)) == 600.0
    # window 0 alone
    assert captured_revenue(txns, windows=range(0, 1)) == 100.0


def test_money_recovered_positive_when_action_helps():
    no_action = [_txn(0, 100.0, False), _txn(0, 100.0, False)]  # captured 0
    action = [_txn(0, 100.0, True), _txn(0, 100.0, False)]  # captured 100
    assert money_recovered(action, no_action) == 100.0


def test_money_recovered_negative_is_preserved_not_clamped():
    """An action that makes things worse yields a LEGAL negative number."""
    no_action = [_txn(0, 100.0, True), _txn(0, 100.0, True)]  # captured 200
    action = [_txn(0, 100.0, True), _txn(0, 100.0, False)]  # captured 100
    result = money_recovered(action, no_action)
    assert result == -100.0
    assert result < 0.0  # explicitly: not clamped to zero


def test_false_intervention_cost_charged_only_when_acting_without_cause():
    # acted with no real cause (incident D) -> charged
    assert false_intervention_cost(acted=True, had_real_cause=False, cost=1000.0) == 1000.0
    # acted with a real cause -> not a false intervention
    assert false_intervention_cost(acted=True, had_real_cause=True, cost=1000.0) == 0.0
    # held -> no cost
    assert false_intervention_cost(acted=False, had_real_cause=False, cost=1000.0) == 0.0


def test_do_nothing_correct_rate():
    # correctly held when there was no cause
    assert do_nothing_correct_rate(acted=False, had_real_cause=False) == 1.0
    # correctly acted when there was a cause
    assert do_nothing_correct_rate(acted=True, had_real_cause=True) == 1.0
    # acted when it should have held (false intervention) -> wrong
    assert do_nothing_correct_rate(acted=True, had_real_cause=False) == 0.0
    # held when it should have acted -> wrong
    assert do_nothing_correct_rate(acted=False, had_real_cause=True) == 0.0
