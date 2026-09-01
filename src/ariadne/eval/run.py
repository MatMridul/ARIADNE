"""Evaluation harness — the ONLY code that reads GroundTruth (BUILD_SPEC §3.14).

run_once: for ONE scenario, drives detect -> attribute -> decide -> re-simulate
          outcome -> score. Returns RunMetrics.

Multi-system comparison, the discrimination result, and the threshold sweep live in
eval/sweep.py (kept separate so each module stays small).
"""
from __future__ import annotations

from ariadne.baseline.independent import baseline_attribute
from ariadne.decide.policy import select_action
from ariadne.diagnosis.attribute import Attribution, attribute
from ariadne.diagnosis.detect import detect
from ariadne.eval.metrics import (
    RunMetrics,
    active_true_causes,
    is_action_audited,
    is_no_cause,
    is_unsafe_action,
    money_recovered,
    root_cause_hit_window,
)
from ariadne.model.graph import PaymentGraph, default_graph
from ariadne.observe.aggregate import window_stats
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import (
    Incident,
    IncidentType,
)

DETECT_THRESHOLD = 0.05  # delta vs baseline to flag a PSP as 'dropped'


def _blamed_ids(attr: Attribution) -> list[str]:
    if attr.root_cause_kind == "bank":
        return [attr.root_cause_id]
    if attr.root_cause_kind == "psp":
        return sorted(attr.psp_causes) if attr.psp_causes else [attr.root_cause_id]
    if attr.root_cause_kind == "method":
        return [attr.root_cause_id]
    return []


def run_once(
    system: str,
    intervention_threshold: float,
    seed: int,
    incident: Incident | None = None,
    graph: PaymentGraph | None = None,
    cfg: SimConfig | None = None,
) -> RunMetrics:
    """Drive the full loop for ONE scenario.

    system: "ariadne" | "baseline"
    Returns RunMetrics for this single scenario.
    """
    if graph is None:
        graph = default_graph()
    if cfg is None:
        cfg = SimConfig(seed=seed)
    if incident is None:
        from ariadne.simulator.incidents import make_incident
        incident = make_incident(IncidentType.SHARED_BANK, seed, cfg.n_windows, target_id="bank_A")

    txns, gt = generate(graph, cfg, incident)

    correct_detects = 0
    total_detects = 0
    rca_hits_cond = 0            # RCA numerator | detection fired
    rca_scored_cond = 0         # RCA denominator | detection fired
    rca_hits_uncond = 0         # RCA numerator | all active-incident windows
    rca_scored_uncond = 0       # RCA denominator | all active-incident windows
    do_nothing_correct = 0
    do_nothing_total = 0
    expected_rec_sum = 0.0

    executed_actions = 0        # non-do_nothing actions actually taken
    unsafe_actions = 0          # of those, how many violated a safety invariant
    unaudited_actions = 0       # actions missing audit fields (should be 0)
    false_interventions = 0     # acted on a window with NO active incident cause

    best_action = None          # representative recovery action for this scenario
    best_expected = -1.0
    acted_when_clean = False     # a non-do_nothing fired during a clean window

    # process each window: detection, attribution, decision, scoring signals
    for w in range(cfg.n_windows):
        stats = window_stats(txns, graph, w, cfg.txns_per_window)
        det = detect(stats, DETECT_THRESHOLD, w)

        if system == "ariadne":
            attr = attribute(stats, graph, det)
        else:
            attr = baseline_attribute(stats, DETECT_THRESHOLD)

        action = select_action(attr, graph, stats, intervention_threshold, avg_amount=cfg.avg_amount)
        inc_active = _incident_active(gt.incident, w)
        active_causes = active_true_causes(gt, w)
        hit = root_cause_hit_window(gt, _blamed_ids(attr), w)

        # detection metrics
        if det.triggered:
            total_detects += 1
            if inc_active:
                correct_detects += 1

        # RCA | detected: only windows where detection fired (the historical metric)
        if det.triggered:
            rca_scored_cond += 1
            if hit:
                rca_hits_cond += 1

        # RCA | unconditional: EVERY window with a truly active cause, incl. detection
        # misses (a detection miss on an active window is an RCA miss). P1 #2 — do not
        # hide detection misses from the evaluation.
        if active_causes:
            rca_scored_uncond += 1
            if hit:
                rca_hits_uncond += 1

        # action + safety accounting (P2 #4/#5: measured, not asserted)
        if action.kind != "do_nothing":
            executed_actions += 1
            if not is_action_audited(action):
                unaudited_actions += 1
            psp_delta = {s.node_id: s.delta for s in stats.values() if s.node_kind == "psp"}
            active_methods = [
                m.value for m in graph.routing
                if any(wt > 0.0 for _p, wt in graph.routing[m])
            ]
            if is_unsafe_action(action, graph, psp_delta, active_methods):
                unsafe_actions += 1
            expected_rec_sum += action.expected_recovery
            if action.expected_recovery > best_expected:
                best_expected = action.expected_recovery
                best_action = action
            if not inc_active:
                acted_when_clean = True
            if not active_causes:
                false_interventions += 1  # acted where there was no real cause

        if is_no_cause(gt):
            do_nothing_total += 1
            if action.kind == "do_nothing":
                do_nothing_correct += 1

    # money recovered: ONE shared-seed counterfactual for the scenario using the
    # representative (highest-expected-recovery) action. O(1) re-sims, not O(windows).
    realized = 0.0
    false_cost = 0.0
    if best_action is not None:
        realized = money_recovered(graph, cfg, gt.incident, best_action)
        if acted_when_clean:
            # false intervention: acting on a clean window. Cost = the downside if
            # the action hurt, else a fixed churn/ops proxy.
            false_cost = abs(realized) if realized < 0 else (cfg.avg_amount * 0.01 * cfg.txns_per_window)

    rca_cond = rca_hits_cond / rca_scored_cond if rca_scored_cond else 1.0
    rca_uncond = rca_hits_uncond / rca_scored_uncond if rca_scored_uncond else 1.0
    return RunMetrics(
        detection_precision=correct_detects / total_detects if total_detects else 1.0,
        detection_recall=correct_detects / max(1, _incident_windows(gt.incident, cfg.n_windows)),
        root_cause_accuracy=rca_cond,                       # back-compat alias
        root_cause_accuracy_conditional=rca_cond,
        root_cause_accuracy_unconditional=rca_uncond,
        rca_scored_conditional=rca_scored_cond,
        rca_scored_unconditional=rca_scored_uncond,
        money_recovered=realized,
        expected_vs_realized_gap=abs(expected_rec_sum - realized),
        false_intervention_cost=false_cost,
        false_interventions=false_interventions,
        unsafe_action_rate=(unsafe_actions / executed_actions) if executed_actions else 0.0,
        executed_actions=executed_actions,
        unaudited_actions=unaudited_actions,
        do_nothing_correct_rate=do_nothing_correct / do_nothing_total if do_nothing_total else 1.0,
        do_nothing_scored=do_nothing_total,
        n_scenarios=1,
    )


def _incident_active(incident: Incident, w: int) -> bool:
    if incident.incident_type == IncidentType.NONE:
        return False
    if incident.start_window <= w <= incident.end_window:
        return True
    if incident.incident_type == IncidentType.COINCIDENTAL:
        if incident.secondary_start_window <= w <= incident.secondary_end_window:
            return True
    return False


def _incident_windows(incident: Incident, n_windows: int) -> int:
    if incident.incident_type == IncidentType.NONE:
        return 0
    count = incident.end_window - incident.start_window + 1
    if incident.incident_type == IncidentType.COINCIDENTAL:
        count += incident.secondary_end_window - incident.secondary_start_window + 1
    return max(1, count)
