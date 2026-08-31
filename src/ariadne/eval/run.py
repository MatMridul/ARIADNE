"""Evaluation harness — the ONLY code that reads GroundTruth (BUILD_SPEC §3.14).

run_once: for ONE scenario, drives detect -> attribute -> decide -> re-simulate
          outcome -> score. Returns RunMetrics.
run_sweep: runs BOTH systems across seeds x thresholds, returns the discrimination
           result + frontier data. (Phase 5-6; stub for now.)
"""
from __future__ import annotations

from ariadne.baseline.independent import baseline_attribute
from ariadne.decide.policy import apply_action, select_action
from ariadne.diagnosis.attribute import Attribution, attribute
from ariadne.diagnosis.detect import detect
from ariadne.eval.metrics import (
    RunMetrics,
    captured_revenue,
    is_no_cause,
    money_recovered,
    root_cause_hit_window,
)
from ariadne.model.graph import PaymentGraph, default_graph
from ariadne.observe.aggregate import psp_stats, window_stats
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import (
    GroundTruth,
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
    rca_hits = 0
    total_scored = 0
    do_nothing_correct = 0
    do_nothing_total = 0
    expected_rec_sum = 0.0

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

        if det.triggered:
            total_detects += 1
            total_scored += 1
            if inc_active:
                correct_detects += 1
            if root_cause_hit_window(gt, _blamed_ids(attr), w):
                rca_hits += 1

        if action.kind != "do_nothing":
            expected_rec_sum += action.expected_recovery
            if action.expected_recovery > best_expected:
                best_expected = action.expected_recovery
                best_action = action
            if not inc_active:
                acted_when_clean = True

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

    return RunMetrics(
        detection_precision=correct_detects / total_detects if total_detects else 1.0,
        detection_recall=correct_detects / max(1, _incident_windows(gt.incident, cfg.n_windows)),
        root_cause_accuracy=rca_hits / total_scored if total_scored else 1.0,
        money_recovered=realized,
        expected_vs_realized_gap=abs(expected_rec_sum - realized),
        false_intervention_cost=false_cost,
        do_nothing_correct_rate=do_nothing_correct / do_nothing_total if do_nothing_total else 1.0,
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


# --- Phase 5/6: multi-system comparison + discrimination result --------------
from statistics import mean

from ariadne.simulator.incidents import make_incident


def _mean(xs):
    return mean(xs) if xs else 0.0


def compare_systems_on_incident(
    incident_type: IncidentType,
    seeds: list[int],
    intervention_threshold: float,
    *,
    target_id: str | None = None,
    secondary_target_id: str | None = None,
) -> dict:
    """Run BOTH systems on a given incident type across seeds; aggregate the
    metrics that matter for the discrimination result (RCA + money recovered)."""
    out = {"ariadne": {"rca": [], "money": []}, "baseline": {"rca": [], "money": []}}
    for seed in seeds:
        cfg = SimConfig(seed=seed)
        inc = make_incident(
            incident_type, seed, cfg.n_windows,
            target_id=target_id, secondary_target_id=secondary_target_id,
        )
        for system in ("ariadne", "baseline"):
            m = run_once(system, intervention_threshold, seed, incident=inc, cfg=cfg)
            out[system]["rca"].append(m.root_cause_accuracy)
            out[system]["money"].append(m.money_recovered)
    return {
        system: {
            "root_cause_accuracy": _mean(v["rca"]),
            "money_recovered": _mean(v["money"]),
        }
        for system, v in out.items()
    }


def discrimination_result(seeds: list[int], intervention_threshold: float = 0.70) -> dict:
    """The Shared Dependency Discrimination result (adapter §7):
      - incident A: ARIADNE must beat baseline (RCA + money recovered)
      - incident B: ARIADNE must NOT regress vs baseline
      - incident E: ARIADNE must NOT over-attribute (RCA should hold; both correct)
    Written before the outcome is known; a loss is a valid, reportable result.
    """
    a = compare_systems_on_incident(IncidentType.SHARED_BANK, seeds, intervention_threshold, target_id="bank_A")
    b = compare_systems_on_incident(IncidentType.SINGLE_PSP, seeds, intervention_threshold, target_id="psp_1")
    e = compare_systems_on_incident(
        IncidentType.COINCIDENTAL, seeds, intervention_threshold,
        target_id="psp_1", secondary_target_id="psp_3",
    )
    return {
        "incident_A_shared_bank": a,
        "incident_B_single_psp": b,
        "incident_E_coincidental": e,
        "A_ariadne_beats_baseline_rca": a["ariadne"]["root_cause_accuracy"] > a["baseline"]["root_cause_accuracy"],
        "A_ariadne_beats_baseline_money": a["ariadne"]["money_recovered"] > a["baseline"]["money_recovered"],
        "B_no_regression": a["ariadne"]["root_cause_accuracy"] >= 0.0
        and b["ariadne"]["root_cause_accuracy"] >= b["baseline"]["root_cause_accuracy"] - 1e-9,
        "E_ariadne_not_over_attributes": e["ariadne"]["root_cause_accuracy"] >= e["baseline"]["root_cause_accuracy"] - 1e-9,
    }


# --- Phase 6: full batch + threshold sweep -----------------------------------
from ariadne.eval.metrics import RunMetrics as _RM
from ariadne.eval.scenarios import scenario_batch


def run_batch(system: str, intervention_threshold: float, seed: int) -> RunMetrics:
    """Run one seed's full batch (all five incident types) for one system at one
    threshold; aggregate into a single RunMetrics. This is 'money recovered across
    a batch' (Track 03 bar) plus the safety numbers."""
    batch = scenario_batch(seed)
    money = 0.0
    false_cost = 0.0
    rca_vals: list[float] = []
    dnc_vals: list[float] = []
    n = 0
    for inc, cfg in batch:
        m = run_once(system, intervention_threshold, cfg.seed, incident=inc, cfg=cfg)
        money += m.money_recovered
        false_cost += m.false_intervention_cost
        rca_vals.append(m.root_cause_accuracy)
        dnc_vals.append(m.do_nothing_correct_rate)
        n += 1
    return RunMetrics(
        root_cause_accuracy=_mean(rca_vals),
        money_recovered=money,
        false_intervention_cost=false_cost,
        do_nothing_correct_rate=_mean(dnc_vals),
        n_scenarios=n,
    )


def run_sweep(
    seeds: list[int],
    thresholds: tuple[float, ...] = (0.55, 0.70, 0.85),
    include_discrimination: bool = True,
) -> dict:
    """Run BOTH systems across all thresholds and seeds. Produces:
      1. discrimination: ARIADNE vs baseline on A (must improve) and B (no regress).
      2. frontier: recovery vs false-intervention cost per system per threshold.
    """
    frontier: dict[str, list[dict]] = {"ariadne": [], "baseline": []}
    for thr in thresholds:
        for system in ("ariadne", "baseline"):
            money_vals = []
            false_vals = []
            dnc_vals = []
            for seed in seeds:
                m = run_batch(system, thr, seed)
                money_vals.append(m.money_recovered)
                false_vals.append(m.false_intervention_cost)
                dnc_vals.append(m.do_nothing_correct_rate)
            frontier[system].append({
                "threshold": thr,
                "money_recovered": _mean(money_vals),
                "false_intervention_cost": _mean(false_vals),
                "do_nothing_correct_rate": _mean(dnc_vals),
            })
    disc = discrimination_result(seeds, intervention_threshold=0.70) if include_discrimination else None
    return {"frontier": frontier, "discrimination": disc, "seeds": seeds, "thresholds": list(thresholds)}
