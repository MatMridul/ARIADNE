"""Evaluation metrics (BUILD_SPEC §3.13).

The full ``RunMetrics`` field set is computed here: detection quality
(precision/recall/latency), diagnosis quality (root_cause_accuracy,
path_accuracy, calibration_error) and the money + safety numbers
(money_recovered, expected_vs_realized_gap, false_intervention_cost,
unsafe_action_rate, do_nothing_correct_rate).

``money_recovered = revenue(action, seed=k) − revenue(no_action, seed=k)`` under
the SAME seed/draws — a negative value is legal and MUST NOT be clamped
(BUILD_SPEC §3.13 shared-seed counterfactual). Safety metrics are first-class and
are reported as loudly as recovery (context invariant 6/7).

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
    # Headline incident-D safety number: correctly HELD on a no-cause window.
    # NaN on a cause-bearing scenario (this metric is undefined there — see
    # do_nothing_correct_rate below), so batch aggregation counts only no-cause
    # scenarios and the number is not diluted by correct-act cases.
    do_nothing_correct_rate: float = 0.0
    # Overall decision correctness (held-on-no-cause OR acted-on-cause). Kept
    # SEPARATE so the incident-D headline above stays clean.
    decision_correct_rate: float = 0.0


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


def do_nothing_correct_rate(acted: bool, had_real_cause: bool) -> float | None:
    """The incident-D safety headline: was do_nothing the correct call?

    Defined ONLY on no-cause windows (incident D / clean), where holding is the
    right answer: 1.0 when we correctly HELD, 0.0 when we wrongly acted. On a
    cause-bearing scenario the metric is undefined and returns ``None`` so batch
    aggregation skips it — this keeps the number a clean "how often did we
    correctly do nothing when there was nothing to do" and does NOT conflate it
    with correctly acting on a real cause (see ``decision_correct_rate`` for the
    overall decision-correctness number)."""
    if had_real_cause:
        return None
    return 1.0 if not acted else 0.0


def decision_correct_rate(acted: bool, had_real_cause: bool) -> float:
    """Overall decision correctness across ALL scenarios: 1.0 when we HELD on a
    no-cause window OR ACTED on a cause-bearing one, else 0.0.

    This is the number that used to be overloaded onto
    ``do_nothing_correct_rate``; it is kept as a SEPARATE field so the incident-D
    hold-on-no-cause headline stays isolated."""
    correct_hold = (not acted) and (not had_real_cause)
    correct_act = acted and had_real_cause
    return 1.0 if (correct_hold or correct_act) else 0.0


def _norm_cause(cause: str) -> str:
    """Normalize a blamed/true cause id so method names compare across layers.

    Diagnosis names methods ``method_upi`` (from ``NodeStats.node_id``) while
    GroundTruth names the raw ``upi``; strip the prefix so the two agree without
    diagnosis ever seeing ground truth."""
    return cause[len("method_") :] if cause.startswith("method_") else cause


def detection_metrics(
    dropped_nodes: list[str], affected_nodes: set[str]
) -> tuple[float, float]:
    """(precision, recall) of the detector's dropped set against the truly
    affected PSP/method nodes. A no-cause window (empty ``affected_nodes``) that
    fires nothing scores a perfect 1.0/1.0; a false alarm scores precision 0.0."""
    dropped = {_norm_cause(n) for n in dropped_nodes}
    truth = {_norm_cause(n) for n in affected_nodes}
    if not dropped and not truth:
        return 1.0, 1.0
    if not dropped:
        return 1.0, 0.0
    tp = len(dropped & truth)
    precision = tp / len(dropped)
    recall = tp / len(truth) if truth else (1.0 if not dropped else 0.0)
    return precision, recall


def detection_latency(
    first_affected_window: int | None, detected_window: int | None
) -> float:
    """Windows elapsed between incident onset and detection. 0.0 when there was no
    incident (nothing to detect) or detection landed on the onset window."""
    if first_affected_window is None or detected_window is None:
        return 0.0
    return float(max(0, detected_window - first_affected_window))


def root_cause_accuracy(blamed: set[str], true_causes: set[str]) -> float:
    """1.0 when the blamed node-set exactly matches the true causes (after method
    normalization). Both empty (correct no-cause) is a perfect score."""
    b = {_norm_cause(x) for x in blamed if x}
    t = {_norm_cause(x) for x in true_causes if x}
    return 1.0 if b == t else 0.0


def path_accuracy(
    root_cause_kind: str, blamed: set[str], true_causes: set[str], had_cause: bool
) -> float:
    """Did the reasoning reach the right KIND of explanation?

    Rewards naming the correct causal nodes AND, for a no-cause window, correctly
    landing on ``none``. This is the "did the evidence path point at the right
    place" score, distinct from exact-set root-cause accuracy."""
    if not had_cause:
        return 1.0 if root_cause_kind == "none" else 0.0
    if root_cause_kind == "none":
        return 0.0
    b = {_norm_cause(x) for x in blamed if x}
    t = {_norm_cause(x) for x in true_causes if x}
    return len(b & t) / len(b | t) if (b or t) else 0.0


def calibration_error(confidence: float, correct: bool) -> float:
    """|confidence − outcome|: how far the stated confidence sat from being right.

    A confident-and-correct or unconfident-and-wrong call is well calibrated;
    a confident-and-wrong call is punished (that is the dangerous failure)."""
    outcome = 1.0 if correct else 0.0
    return abs(confidence - outcome)


def expected_vs_realized_gap(expected_recovery: float, realized: float) -> float:
    """Signed gap between what the action promised and what it delivered. Negative
    means it under-delivered; kept unclamped."""
    return expected_recovery - realized


def unsafe_action_rate(acted: bool, had_real_cause: bool) -> float:
    """1.0 when the system took an action with no real cause to fix (the unsafe
    failure mode), else 0.0. Aggregated this is the batch unsafe-action rate."""
    return 1.0 if (acted and not had_real_cause) else 0.0
