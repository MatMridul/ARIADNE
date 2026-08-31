"""Multi-system comparison, discrimination result, batch + threshold sweep.

Split out of eval/run.py to keep each module small. Reads GroundTruth only through
run_once (which is the sole ground-truth reader). This module orchestrates runs.
"""
from __future__ import annotations

from statistics import mean

from ariadne.eval.metrics import RunMetrics
from ariadne.eval.run import run_once
from ariadne.eval.scenarios import scenario_batch
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import IncidentType, make_incident


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
