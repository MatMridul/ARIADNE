"""The evaluation harness (BUILD_SPEC §3.14).

``run_once`` drives the full thin loop for ONE incident scenario at ONE
threshold (scoring delegated to ``sweep.run_scenario``). ``run_sweep`` runs BOTH
systems across seeds × thresholds and returns the Shared Dependency
Discrimination result plus the recovery-vs-risk frontier (batch driving and
frontier aggregation live in ``eval/sweep.py`` to keep modules small).

``discrimination_result`` runs BOTH systems on incidents A, B and E and reports,
honestly, whether ARIADNE beats the baseline on A, does not regress on B, and
does not over-attribute on E.

This is the ONLY place GroundTruth is read (BUILD_SPEC §1 rule 3). ``diagnosis/``,
``baseline/`` and ``decide/`` never see it — they receive only ``NodeStats`` /
``Detection``.
"""

from ..baseline.independent import baseline_attribute
from ..diagnosis.attribute import Attribution, attribute
from ..diagnosis.detect import detect
from ..model.graph import PaymentGraph, default_graph
from ..observe.aggregate import window_stats
from ..simulator.config import SimConfig
from ..simulator.engine import generate
from ..simulator.incidents import Incident, IncidentType
from .metrics import RunMetrics
from .sweep import build_frontier, run_scenario

# Detection sensitivity for diagnosis (delta below −threshold = "dropped").
_DETECT_THRESHOLD = 0.05


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


def _incident_b(graph: PaymentGraph) -> Incident:
    """A single-PSP incident on one PSP of the shared bank (control, no over-attr)."""
    shared = graph.shared_banks()
    bank_id = next(iter(shared)) if shared else "bank_A"
    psp_id = sorted(graph.psps_for_bank(bank_id))[0]
    return Incident(
        incident_type=IncidentType.SINGLE_PSP,
        target_id=psp_id,
        start_window=8,
        end_window=11,
        severity=0.4,
    )


def _incident_e(graph: PaymentGraph) -> Incident:
    """A coincidental incident: two PSPs on DIFFERENT banks fail at once.

    One PSP from the shared bank plus the lone PSP on bank_B, so no single bank
    fully covers the down set — the honest answer is two independent PSP faults.
    """
    shared = graph.shared_banks()
    bank_id = next(iter(shared)) if shared else "bank_A"
    primary = sorted(graph.psps_for_bank(bank_id))[0]
    other = next(
        (p for p, b in sorted(graph.settles_via.items()) if b != bank_id),
        "psp_3",
    )
    return Incident(
        incident_type=IncidentType.COINCIDENTAL,
        target_id=primary,
        secondary_target_id=other,
        start_window=8,
        end_window=11,
        severity=0.4,
        secondary_start_window=8,
        secondary_end_window=11,
        secondary_severity=0.4,
    )


_INCIDENTS = {
    "A": _incident_a,
    "B": _incident_b,
    "E": _incident_e,
}


def _diagnose(
    system: str,
    stats,
    graph: PaymentGraph,
    detection,
) -> Attribution:
    """Route to the relational diagnoser (ARIADNE) or the non-relational baseline."""
    if system == "ariadne":
        return attribute(stats, graph, detection)
    if system == "baseline":
        return baseline_attribute(stats, _DETECT_THRESHOLD)
    raise ValueError(f"unknown system {system!r} (expected 'ariadne' or 'baseline')")


def run_once(
    system: str,
    intervention_threshold: float,
    seed: int,
    incident_key: str = "A",
) -> RunMetrics:
    """Drive the full loop for one incident scenario and score the full RunMetrics.

    ``system`` in {"ariadne", "baseline"}; both act via the SAME decide/policy
    menu (DR-001 C1) so the money-recovered comparison is apples-to-apples.
    ``incident_key`` selects the scenario (A shared-bank, B single-PSP,
    E coincidental). Scoring is delegated to ``sweep.run_scenario`` so the thin
    loop and the batch use one identical pipeline."""
    incident = _INCIDENTS[incident_key](default_graph())
    return run_scenario(system, intervention_threshold, incident, SimConfig(seed=seed))


def run_sweep(
    seeds: list[int],
    thresholds: tuple[float, ...] = (0.55, 0.70, 0.85),
) -> dict:
    """Run BOTH systems across all ``thresholds`` and ``seeds`` (BUILD_SPEC §3.14).

    Returns a dict with:
      * ``discrimination`` — the Shared Dependency Discrimination result on the
        first seed (ARIADNE vs baseline on A/B/E), reported honestly.
      * ``frontier`` — the recovery-vs-false-intervention-cost frontier per system,
        one point per threshold (fed to ``reporting/frontier.py``).
    """
    return {
        "seeds": list(seeds),
        "thresholds": list(thresholds),
        "discrimination": discrimination_result(seeds[0]),
        "frontier": build_frontier(list(seeds), tuple(thresholds)),
    }


def _attribution_for(system: str, incident_key: str, seed: int) -> tuple:
    """Return (Attribution, GroundTruth) for one system on one incident.

    Used by the discrimination helper to inspect WHAT each system blamed (kind /
    ids), independent of the money-recovered scoring path."""
    graph = default_graph()
    cfg = SimConfig(seed=seed)
    incident = _INCIDENTS[incident_key](graph)
    txns, gt = generate(graph, cfg, incident)
    stats = window_stats(txns, graph, incident.start_window)
    detection = detect(stats, _DETECT_THRESHOLD, window=incident.start_window)
    return _diagnose(system, stats, graph, detection), gt


def discrimination_result(seed: int = 7) -> dict:
    """The Shared Dependency Discrimination result (BUILD_ORDER step 17).

    Runs BOTH systems on incidents A, B and E and reports, honestly, what each
    system concluded and whether the thesis holds:

      * A — ARIADNE should blame the shared BANK; the baseline blames independent
        PSPs (the discrimination gap). Root-cause accuracy on A is compared.
      * B — no regression: both should correctly blame the single PSP.
      * E — no over-attribution: ARIADNE should blame TWO independent PSPs, NOT a
        bank (the A-vs-E anti-cheat).

    Numbers are reported whichever way they fall — nothing is tuned to force a win.
    """
    out: dict = {"seed": seed, "incidents": {}}
    for key in ("A", "B", "E"):
        ar_attr, gt = _attribution_for("ariadne", key, seed)
        bl_attr, _ = _attribution_for("baseline", key, seed)
        truth = set(gt.true_causes)
        ar_blamed = {ar_attr.root_cause_id, *ar_attr.secondary_causes} - {""}
        bl_blamed = {bl_attr.root_cause_id, *bl_attr.secondary_causes} - {""}
        out["incidents"][key] = {
            "true_causes": sorted(truth),
            "ariadne": {
                "kind": ar_attr.root_cause_kind,
                "blamed": sorted(ar_blamed),
                "confidence": round(ar_attr.confidence, 4),
                # for A "correct" means naming the shared bank; for B/E it means
                # exactly recovering the true PSP set.
                "correct": (ar_attr.root_cause_kind == "bank")
                if key == "A"
                else (ar_blamed == truth),
            },
            "baseline": {
                "kind": bl_attr.root_cause_kind,
                "blamed": sorted(bl_blamed),
                "confidence": round(bl_attr.confidence, 4),
                "correct": (bl_attr.root_cause_kind == "bank")
                if key == "A"
                else (bl_blamed == truth),
            },
        }

    a = out["incidents"]["A"]
    b = out["incidents"]["B"]
    e = out["incidents"]["E"]
    out["summary"] = {
        # ARIADNE names the shared bank on A where the baseline cannot.
        "A_ariadne_beats_baseline": a["ariadne"]["correct"]
        and not a["baseline"]["correct"],
        "A_ariadne_blames_bank": a["ariadne"]["kind"] == "bank",
        "A_baseline_blames_independent_psps": a["baseline"]["kind"] == "psp",
        # No regression on the single-PSP control.
        "B_no_regression": b["ariadne"]["correct"] and b["baseline"]["correct"],
        # No over-attribution: ARIADNE stays PSP-level on the coincidental case.
        "E_ariadne_no_over_attribution": e["ariadne"]["kind"] == "psp"
        and e["ariadne"]["kind"] != "bank",
    }
    return out
