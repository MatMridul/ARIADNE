"""Honest scoring (BUILD_SPEC §3.13). This module is part of eval/ -- the ONLY
place allowed to read GroundTruth.

money_recovered uses the shared-seed counterfactual (hostile-review fix #5):
revenue(action, seed=k) - revenue(no_action, seed=k) under the SAME seed and
therefore the same underlying demand and per-transaction failure draws, differing
only in the routing/method config the action changed. A negative value is legal
and is reported (an action that made things worse).
"""
from __future__ import annotations

from dataclasses import dataclass

from ariadne.decide.actions import Action
from ariadne.decide.policy import apply_action, apply_action_config
from ariadne.model.entities import Transaction
from ariadne.model.graph import PaymentGraph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import GroundTruth, Incident, IncidentType


def captured_revenue(txns: list[Transaction]) -> float:
    """Realised revenue = sum of successful transaction amounts."""
    return sum(t.amount for t in txns if t.success)


def money_recovered(
    base_graph: PaymentGraph,
    cfg: SimConfig,
    incident: Incident,
    action: Action,
) -> float:
    """revenue(action) - revenue(no_action) under the SAME seed/draws.
    Both re-simulations use cfg (same seed) and the same incident; only the graph
    config differs (no-action = base_graph, action = post-action graph)."""
    no_action_txns, _ = generate(base_graph, cfg, incident)
    action_graph = apply_action(base_graph, action)
    action_cfg = apply_action_config(cfg, action)
    action_txns, _ = generate(action_graph, action_cfg, incident)
    return captured_revenue(action_txns) - captured_revenue(no_action_txns)


@dataclass
class RunMetrics:
    detection_precision: float = 0.0
    detection_recall: float = 0.0
    detection_latency: float = 0.0
    root_cause_accuracy: float = 0.0
    path_accuracy: float = 0.0
    calibration_error: float = 0.0
    money_recovered: float = 0.0
    expected_vs_realized_gap: float = 0.0
    false_intervention_cost: float = 0.0
    unsafe_action_rate: float = 0.0
    do_nothing_correct_rate: float = 0.0
    n_scenarios: int = 0


def root_cause_hit(gt: GroundTruth, blamed_ids: list[str]) -> bool:
    """Whole-incident scoring (used in unit fixtures). A/B/C: the single true node
    must be blamed. E: BOTH independent PSPs must be blamed and no bank. D: nothing."""
    true = set(gt.true_causes)
    blamed = set(blamed_ids)
    if not true:  # incident D: correct iff nothing was blamed
        return not blamed
    return blamed == true


def active_true_causes(gt: GroundTruth, window: int) -> set[str]:
    """The true cause(s) actually active in THIS window (eval-side; reads ground
    truth). For E the two independent faults have their own onset windows, so a
    single window has at most one of them active -- scoring must reflect that."""
    inc = gt.incident
    it = inc.incident_type
    if it == IncidentType.NONE:
        return set()
    active: set[str] = set()
    if it == IncidentType.COINCIDENTAL:
        if inc.start_window <= window <= inc.end_window and inc.target_id:
            active.add(inc.target_id)
        if inc.secondary_start_window <= window <= inc.secondary_end_window and inc.secondary_target_id:
            active.add(inc.secondary_target_id)
        return active
    # A/B/C: single fault span
    if inc.start_window <= window <= inc.end_window:
        return set(gt.true_causes)
    return set()


def root_cause_hit_window(gt: GroundTruth, blamed_ids: list[str], window: int) -> bool:
    """Window-aware RCA: a hit iff the blamed set matches exactly the causes active
    in this window. This correctly rewards ARIADNE for naming the right node while
    penalising over-attribution (e.g. blaming a bank on incident E)."""
    active = active_true_causes(gt, window)
    blamed = set(blamed_ids)
    if not active:  # window has no active cause -> correct iff nothing blamed
        return not blamed
    return blamed == active


def is_no_cause(gt: GroundTruth) -> bool:
    return gt.incident.incident_type == IncidentType.NONE
