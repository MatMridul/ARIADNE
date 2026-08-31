"""Evaluation metrics (BUILD_SPEC §3.13).

The full ``RunMetrics`` field set is declared; the thin loop computes the three
head-line numbers — ``money_recovered`` (shared-seed counterfactual),
``false_intervention_cost`` and ``do_nothing_correct_rate``. Fields for metrics
not yet wired default to ``0.0`` and are filled in later phases.

``money_recovered = revenue(action, seed=k) − revenue(no_action, seed=k)`` under
the SAME seed/draws — a negative value is legal and MUST NOT be clamped
(BUILD_SPEC §3.13 shared-seed counterfactual).

This is part of ``eval/`` — the ONLY layer allowed to read GroundTruth.
"""

from dataclasses import dataclass

from ..model.entities import Transaction


@dataclass
class RunMetrics:
    detection_precision: float = 0.0
    detection_recall: float = 0.0
    detection_latency: float = 0.0
    root_cause_accuracy: float = 0.0  # vs GroundTruth
    path_accuracy: float = 0.0
    calibration_error: float = 0.0
    money_recovered: float = 0.0  # realized, post-intervention
    expected_vs_realized_gap: float = 0.0
    false_intervention_cost: float = 0.0  # acted when it shouldn't have
    unsafe_action_rate: float = 0.0
    do_nothing_correct_rate: float = 0.0  # headline safety number (incident D)


def captured_revenue(txns: list[Transaction], windows: range | None = None) -> float:
    """Total amount from SUCCESSFUL transactions (revenue actually captured).

    When ``windows`` is given, only transactions whose window index falls in that
    range are counted (used to score just the affected windows)."""
    total = 0.0
    for t in txns:
        if windows is not None and int(t.timestamp) not in windows:
            continue
        if t.success:
            total += t.amount
    return total


def money_recovered(
    action_txns: list[Transaction],
    no_action_txns: list[Transaction],
    windows: range | None = None,
) -> float:
    """revenue(action) − revenue(no_action) under the SAME seed. Negatives are
    legal (an action that made things worse) and are returned unclamped."""
    return captured_revenue(action_txns, windows) - captured_revenue(
        no_action_txns, windows
    )


def false_intervention_cost(acted: bool, had_real_cause: bool, cost: float) -> float:
    """Cost incurred when the system ACTED but there was no real cause to fix
    (e.g. incident D). Zero when it did not act or the action was warranted."""
    return cost if (acted and not had_real_cause) else 0.0


def do_nothing_correct_rate(acted: bool, had_real_cause: bool) -> float:
    """1.0 when do_nothing was the correct call (no real cause and we held), else
    0.0. Aggregated across a batch this becomes the headline safety rate."""
    correct_hold = (not acted) and (not had_real_cause)
    correct_act = acted and had_real_cause
    return 1.0 if (correct_hold or correct_act) else 0.0
