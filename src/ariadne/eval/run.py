"""The evaluation harness (BUILD_SPEC §3.14).

``run_once`` drives the full thin loop for ONE incident-A scenario at ONE
threshold: simulate → aggregate → detect → attribute → select_action →
re-simulate the affected windows under the action's changed config (SAME seed) →
score against GroundTruth.

This is the ONLY place GroundTruth is read (BUILD_SPEC §1 rule 3). ``diagnosis/``
and ``decide/`` never see it — they receive only ``NodeStats`` / ``Detection``.
"""

from ..decide.policy import select_action
from ..diagnosis.attribute import attribute
from ..diagnosis.detect import detect
from ..model.entities import Method
from ..model.graph import PaymentGraph, default_graph
from ..observe.aggregate import window_stats
from ..simulator.config import SimConfig
from ..simulator.engine import generate
from ..simulator.incidents import Incident, IncidentType
from .metrics import (
    RunMetrics,
    do_nothing_correct_rate,
    false_intervention_cost,
    money_recovered,
)

# Detection sensitivity for the thin loop (delta below −threshold = "dropped").
_DETECT_THRESHOLD = 0.05
# Nominal cost charged for a false intervention (acting with no real cause).
_FALSE_INTERVENTION_COST = 1000.0


def _incident_a(graph: PaymentGraph) -> Incident:
    """A shared-bank incident on the bank shared by >1 PSP (bank_A)."""
    shared = graph.shared_banks()
    bank_id = next(iter(shared)) if shared else "bank_A"
    return Incident(
        incident_type=IncidentType.SHARED_BANK,
        target_id=bank_id,
        start_window=8,
        end_window=11,
        severity=0.4,
    )


def _apply_action(graph: PaymentGraph, action) -> PaymentGraph:
    """Return the graph as changed by the chosen action (reroute), else unchanged."""
    if action.kind == "reroute":
        p = action.params
        return graph.reroute(Method(p["method"]), p["from_psp"], p["to_psp"])
    return graph


def run_once(system: str, intervention_threshold: float, seed: int) -> RunMetrics:
    """Drive the full loop on one incident-A scenario. ``system`` accepts
    ``"ariadne"`` (baseline is wired in FEAT-004)."""
    graph = default_graph()
    cfg = SimConfig(seed=seed)
    incident = _incident_a(graph)

    # 1) simulate + read ground truth (eval-only).
    no_action_txns, gt = generate(graph, cfg, incident)
    affected = range(incident.start_window, incident.end_window + 1)

    # 2) aggregate the first affected window, then detect.
    stats = window_stats(no_action_txns, graph, incident.start_window)
    detection = detect(stats, _DETECT_THRESHOLD, window=incident.start_window)

    # 3) diagnose (no ground truth here) — only ariadne is wired in this feature.
    if system != "ariadne":
        raise ValueError(f"unknown system {system!r} (baseline arrives in FEAT-004)")
    attr = attribute(stats, graph, detection)

    # 4) decide.
    action = select_action(attr, graph, stats, intervention_threshold)
    acted = action.kind != "do_nothing"

    # 5) re-simulate the SAME incident under the changed config, SAME seed.
    action_graph = _apply_action(graph, action)
    action_txns, _ = generate(action_graph, cfg, incident)

    # 6) score. money_recovered is the shared-seed counterfactual; negatives kept.
    recovered = money_recovered(action_txns, no_action_txns, affected)
    had_cause = bool(gt.true_causes)
    return RunMetrics(
        money_recovered=recovered,
        false_intervention_cost=false_intervention_cost(
            acted, had_cause, _FALSE_INTERVENTION_COST
        ),
        do_nothing_correct_rate=do_nothing_correct_rate(acted, had_cause),
        root_cause_accuracy=1.0
        if attr.root_cause_id in gt.true_causes
        else 0.0,
    )
