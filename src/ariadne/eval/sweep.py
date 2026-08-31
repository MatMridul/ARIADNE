"""Batch driving + sweep aggregation (BUILD_SPEC §3.12/§3.14).

Split out of ``eval/run.py`` (which holds the single-incident thin loop and the
discrimination helper) to keep every module small. This module drives the full
``scenario_batch`` for one system at one threshold and aggregates ``run_sweep``
across seeds × thresholds into (1) the Shared Dependency Discrimination result and
(2) the recovery-vs-false-intervention-cost frontier per system.

This is part of ``eval/`` — the ONLY layer allowed to read GroundTruth.
"""

from ..baseline.independent import baseline_attribute
from ..decide.policy import select_action
from ..diagnosis.attribute import Attribution, attribute
from ..diagnosis.detect import detect
from ..model.entities import Method
from ..model.graph import PaymentGraph, default_graph
from ..observe.aggregate import window_stats
from ..simulator.config import SimConfig
from ..simulator.engine import generate
from ..simulator.incidents import GroundTruth, Incident, IncidentType
from .metrics import (
    RunMetrics,
    calibration_error,
    detection_latency,
    detection_metrics,
    do_nothing_correct_rate,
    expected_vs_realized_gap,
    false_intervention_cost,
    money_recovered,
    path_accuracy,
    root_cause_accuracy,
    unsafe_action_rate,
)

_DETECT_THRESHOLD = 0.05
_FALSE_INTERVENTION_COST = 1000.0


def _diagnose(system: str, stats, graph: PaymentGraph, detection) -> Attribution:
    if system == "ariadne":
        return attribute(stats, graph, detection)
    if system == "baseline":
        return baseline_attribute(stats, _DETECT_THRESHOLD)
    raise ValueError(f"unknown system {system!r}")


def _apply_action(graph: PaymentGraph, action) -> PaymentGraph:
    if action.kind == "reroute":
        p = action.params
        return graph.reroute(Method(p["method"]), p["from_psp"], p["to_psp"])
    return graph


def _affected_nodes(gt: GroundTruth) -> set[str]:
    """The PSP/method node-ids the incident truly depressed (for detection scoring)."""
    nodes = set(gt.affected_psps)
    nodes.update(f"method_{m.value}" for m in gt.affected_methods)
    return nodes


def run_scenario(
    system: str,
    intervention_threshold: float,
    incident: Incident,
    cfg: SimConfig,
) -> RunMetrics:
    """Drive the full loop for ONE scenario and score the complete RunMetrics set.

    simulate → aggregate → detect → attribute/baseline → decide → re-simulate the
    affected windows under the changed config (SAME seed) → score vs GroundTruth.
    Handles method incidents (C) and no-cause incidents (D: correct = do_nothing)."""
    graph = default_graph()

    no_action_txns, gt = generate(graph, cfg, incident)
    had_cause = bool(gt.true_causes)

    # Detection/attribution window: incident onset if there is one, else a fixed
    # mid-run window so a no-cause run is still exercised end-to-end.
    if had_cause:
        detect_window = incident.start_window
        affected = range(incident.start_window, incident.end_window + 1)
    else:
        detect_window = cfg.n_windows // 2
        affected = range(detect_window, detect_window + 1)

    stats = window_stats(no_action_txns, graph, detect_window)
    detection = detect(stats, _DETECT_THRESHOLD, window=detect_window)
    attr = _diagnose(system, stats, graph, detection)

    action = select_action(attr, graph, stats, intervention_threshold)
    acted = action.kind != "do_nothing"

    action_graph = _apply_action(graph, action)
    action_txns, _ = generate(action_graph, cfg, incident)
    recovered = money_recovered(action_txns, no_action_txns, affected)

    truth = set(gt.true_causes)
    blamed = {attr.root_cause_id, *attr.secondary_causes} - {""}
    rc_acc = root_cause_accuracy(blamed, truth)
    correct = rc_acc == 1.0
    precision, recall = detection_metrics(detection.dropped_nodes, _affected_nodes(gt))
    onset = incident.start_window if had_cause else None
    detected = detection.window if detection.triggered else None

    return RunMetrics(
        detection_precision=precision,
        detection_recall=recall,
        detection_latency=detection_latency(onset, detected),
        root_cause_accuracy=rc_acc,
        path_accuracy=path_accuracy(attr.root_cause_kind, blamed, truth, had_cause),
        calibration_error=calibration_error(attr.confidence, correct),
        money_recovered=recovered,
        expected_vs_realized_gap=expected_vs_realized_gap(
            action.expected_recovery, recovered
        ),
        false_intervention_cost=false_intervention_cost(
            acted, had_cause, _FALSE_INTERVENTION_COST
        ),
        unsafe_action_rate=unsafe_action_rate(acted, had_cause),
        do_nothing_correct_rate=do_nothing_correct_rate(acted, had_cause),
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_batch(system: str, intervention_threshold: float, seed: int) -> dict:
    """Run the whole scenario_batch for one system at one threshold; aggregate."""
    from .scenarios import scenario_batch

    metrics = [
        run_scenario(system, intervention_threshold, inc, cfg)
        for inc, cfg in scenario_batch(seed)
    ]
    return {
        "money_recovered": sum(m.money_recovered for m in metrics),
        "false_intervention_cost": sum(m.false_intervention_cost for m in metrics),
        "root_cause_accuracy": _mean([m.root_cause_accuracy for m in metrics]),
        "detection_precision": _mean([m.detection_precision for m in metrics]),
        "detection_recall": _mean([m.detection_recall for m in metrics]),
        "path_accuracy": _mean([m.path_accuracy for m in metrics]),
        "calibration_error": _mean([m.calibration_error for m in metrics]),
        "unsafe_action_rate": _mean([m.unsafe_action_rate for m in metrics]),
        "do_nothing_correct_rate": _mean([m.do_nothing_correct_rate for m in metrics]),
        "n_scenarios": len(metrics),
    }


def build_frontier(seeds: list[int], thresholds: tuple[float, ...]) -> dict:
    """Recovery-vs-false-intervention-cost frontier per system across thresholds.

    One point per threshold per system: the batch totals averaged over ``seeds``."""
    systems = ("ariadne", "baseline")
    frontier: dict = {s: [] for s in systems}
    for system in systems:
        for thr in thresholds:
            batches = [run_batch(system, thr, seed) for seed in seeds]
            frontier[system].append(
                {
                    "threshold": thr,
                    "money_recovered": _mean(
                        [b["money_recovered"] for b in batches]
                    ),
                    "false_intervention_cost": _mean(
                        [b["false_intervention_cost"] for b in batches]
                    ),
                    "do_nothing_correct_rate": _mean(
                        [b["do_nothing_correct_rate"] for b in batches]
                    ),
                    "root_cause_accuracy": _mean(
                        [b["root_cause_accuracy"] for b in batches]
                    ),
                }
            )
    return frontier
