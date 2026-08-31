"""Incident types + ground truth (BUILD_SPEC §3.4).

The five incident types. Each is expressed as a target + severity that the engine
turns into a lowered per-path success rate during the incident window(s). Ground
truth = which node(s) were hit and when.

**Only the eval harness may read GroundTruth.** ``diagnosis/`` and ``baseline/``
must never import or receive ``Incident`` / ``GroundTruth`` — ground truth exists
solely for scoring. See BUILD_SPEC §1 rule 3 and DR-001.
"""

from dataclasses import dataclass, field
from enum import Enum

from ..model.entities import Method
from ..model.graph import PaymentGraph


class IncidentType(str, Enum):
    SHARED_BANK = "A_shared_bank"  # hero / thesis test — one bank, many PSPs
    SINGLE_PSP = "B_single_psp"  # control — no over-attribution
    METHOD = "C_method"  # method-level fault
    NONE = "D_ambiguous"  # noise dip, NO real cause
    COINCIDENTAL = "E_coincidental"  # two PSPs, DIFFERENT banks, by chance


@dataclass
class Incident:
    incident_type: IncidentType
    target_id: str | None  # bank_id / psp_id / method / None for D
    # for COINCIDENTAL: a second independent PSP target on a different bank
    secondary_target_id: str | None = None
    start_window: int = 0
    end_window: int = 0
    severity: float = 0.0  # drop applied to affected paths' success rate
    # for COINCIDENTAL the second fault gets its own independent onset/severity
    secondary_start_window: int = 0
    secondary_end_window: int = 0
    secondary_severity: float = 0.0


@dataclass
class GroundTruth:
    """ONLY the eval harness may read this. ``diagnosis/`` and ``baseline/`` must not."""

    incident: Incident
    affected_psps: list[str]  # computed from the graph at injection time
    affected_methods: list[Method]
    # true root cause(s): one node for A/B/C; TWO independent PSPs for E; none for D
    true_causes: list[str] = field(default_factory=list)


def apply_drop(base_rate: float, severity: float) -> float:
    """Lower a base per-path success rate by ``severity``, clamped to [0, 1].

    The incident helpers below all reduce to this: an affected path during an
    incident window has its success rate multiplied down by ``severity`` (a
    proportional drop reads more realistically than a flat subtraction and keeps
    the rate in range for any base value)."""
    modified = base_rate * (1.0 - severity)
    if modified < 0.0:
        return 0.0
    if modified > 1.0:
        return 1.0
    return modified


def affected_psps(graph: PaymentGraph, incident: Incident) -> list[str]:
    """PSPs whose success the incident depresses, computed from the graph."""
    it = incident.incident_type
    if it is IncidentType.SHARED_BANK and incident.target_id is not None:
        return sorted(graph.psps_for_bank(incident.target_id))
    if it is IncidentType.SINGLE_PSP and incident.target_id is not None:
        return [incident.target_id]
    if it is IncidentType.COINCIDENTAL:
        psps = [
            p
            for p in (incident.target_id, incident.secondary_target_id)
            if p is not None
        ]
        return sorted(psps)
    if it is IncidentType.METHOD and incident.target_id is not None:
        method = Method(incident.target_id)
        return sorted({psp for psp, _ in graph.routing.get(method, [])})
    return []


def affected_methods(graph: PaymentGraph, incident: Incident) -> list[Method]:
    if incident.incident_type is IncidentType.METHOD and incident.target_id:
        return [Method(incident.target_id)]
    return []


def true_causes(graph: PaymentGraph, incident: Incident) -> list[str]:
    """True root cause(s): one node for A/B/C; TWO independent PSPs for E; none for D."""
    it = incident.incident_type
    if it in (IncidentType.SHARED_BANK, IncidentType.SINGLE_PSP, IncidentType.METHOD):
        return [incident.target_id] if incident.target_id else []
    if it is IncidentType.COINCIDENTAL:
        return [
            p
            for p in (incident.target_id, incident.secondary_target_id)
            if p is not None
        ]
    return []  # NONE has no cause


def ground_truth(graph: PaymentGraph, incident: Incident) -> GroundTruth:
    """Compute GroundTruth from the graph at injection time (eval-only value)."""
    return GroundTruth(
        incident=incident,
        affected_psps=affected_psps(graph, incident),
        affected_methods=affected_methods(graph, incident),
        true_causes=true_causes(graph, incident),
    )
