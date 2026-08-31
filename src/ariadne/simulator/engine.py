"""Deterministic payment-ecosystem simulator (BUILD_SPEC §3.5, adapter §7).

The honest adversary. Given (graph, cfg, incident) it produces the transaction log
the reasoner sees, plus GroundTruth the reasoner must NOT see.

Determinism & shared-seed counterfactual (hostile-review fix #5):
  Every per-transaction random quantity derives from a stream keyed by
  (cfg.seed, window, txn_index, quantity_name). The SAME (seed, window, index)
  therefore yields the SAME demand and the SAME success/latency draws regardless
  of the routing config. An action that only changes routing/method config is thus
  compared against no-action under identical underlying draws -- the action's
  causal effect is isolated, phantom recovery from re-randomisation is impossible.

Incident onset/duration/severity are randomised per seed within bounded ranges
(no fixed schedule a reasoner could learn as a tell), and severities overlap the
noise band for a fraction of cases so some incidents are genuinely ambiguous.
"""
from __future__ import annotations

import hashlib
import struct

from ariadne.model.entities import Method, Transaction
from ariadne.model.graph import PaymentGraph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import GroundTruth, Incident, IncidentType

_METHODS = (Method.UPI, Method.CARD, Method.NETBANKING)


def _u01(*parts: object) -> float:
    """A deterministic uniform(0,1) draw from a tuple key (stdlib hashing only)."""
    key = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    (n,) = struct.unpack("<Q", digest)
    return n / 2**64


def _routing_choice(graph: PaymentGraph, method: Method, r: float) -> str:
    """Pick a PSP for a method by routing weight, deterministically from r in [0,1).
    PSPs with zero weight (e.g. after a reroute) are never chosen."""
    pairs = [(p, w) for p, w in graph.routing.get(method, []) if w > 0.0]
    total = sum(w for _p, w in pairs)
    if total <= 0.0:
        return ""  # method fully disabled -> no PSP carries it
    threshold = r * total
    acc = 0.0
    for psp_id, w in sorted(pairs):
        acc += w
        if threshold < acc:
            return psp_id
    return sorted(pairs)[-1][0]


def _in_window(window: int, start: int, end: int) -> bool:
    return start <= window <= end


def _incident_drop(
    incident: Incident,
    graph: PaymentGraph,
    window: int,
    psp_id: str,
    method: Method,
) -> float:
    """Success-rate drop applied to THIS transaction's path from the injected
    incident. Zero if the path is not affected or the window is outside onset."""
    it = incident.incident_type
    if it == IncidentType.NONE:
        return 0.0
    if it == IncidentType.SHARED_BANK:
        # all PSPs settling via the target bank drop, during the window
        if _in_window(window, incident.start_window, incident.end_window):
            if graph.settles_via.get(psp_id) == incident.target_id:
                return incident.severity
        return 0.0
    if it == IncidentType.SINGLE_PSP:
        if _in_window(window, incident.start_window, incident.end_window):
            if psp_id == incident.target_id:
                return incident.severity
        return 0.0
    if it == IncidentType.METHOD:
        if _in_window(window, incident.start_window, incident.end_window):
            if method.value == incident.target_id:
                return incident.severity
        return 0.0
    if it == IncidentType.COINCIDENTAL:
        drop = 0.0
        if psp_id == incident.target_id and _in_window(
            window, incident.start_window, incident.end_window
        ):
            drop = max(drop, incident.severity)
        if psp_id == incident.secondary_target_id and _in_window(
            window, incident.secondary_start_window, incident.secondary_end_window
        ):
            drop = max(drop, incident.secondary_severity)
        return drop
    return 0.0


def _effective_rate(
    cfg: SimConfig,
    method: Method,
    cohort: str,
    geography: str,
    window: int,
    drop: float,
) -> float:
    base = cfg.base_success[method]
    base += cfg.cohort_offset(cohort) + cfg.geography_offset(geography)
    # per-window noise, symmetric, deterministic from (seed, window, method)
    noise = (_u01(cfg.seed, "noise", window, method.value) - 0.5) * 2.0 * cfg.noise_std
    rate = base + noise - drop
    return min(1.0, max(0.0, rate))


def generate(
    graph: PaymentGraph, cfg: SimConfig, incident: Incident
) -> tuple[list[Transaction], GroundTruth]:
    """Deterministic given cfg.seed. Returns (transactions, ground_truth).

    Ground truth is a SEPARATE return value; it is never embedded in a Transaction.
    """
    txns: list[Transaction] = []
    for window in range(cfg.n_windows):
        for i in range(cfg.txns_per_window):
            # demand attributes (same regardless of routing config -> shared-seed)
            m = _METHODS[int(_u01(cfg.seed, "method", window, i) * len(_METHODS))]
            cohort = cfg.cohorts[
                int(_u01(cfg.seed, "cohort", window, i) * len(cfg.cohorts))
            ]
            geo = cfg.geographies[
                int(_u01(cfg.seed, "geo", window, i) * len(cfg.geographies))
            ]
            amount = cfg.avg_amount * (0.5 + _u01(cfg.seed, "amount", window, i))

            r_route = _u01(cfg.seed, "route", window, i)
            psp_id = _routing_choice(graph, m, r_route)
            if psp_id == "":
                continue  # method fully disabled: transaction cannot be placed
            bank_id = graph.settles_via.get(psp_id, "")

            drop = _incident_drop(incident, graph, window, psp_id, m)
            rate = _effective_rate(cfg, m, cohort, geo, window, drop)

            r_success = _u01(cfg.seed, "success", window, i)
            success = r_success < rate
            latency = cfg.base_latency_ms * (
                1.0 + _u01(cfg.seed, "latency", window, i)
            )
            if not success:
                latency *= 1.5  # failures tend to be slower
            failure_code = None if success else _failure_code(m, drop)

            txns.append(
                Transaction(
                    txn_id=f"s{cfg.seed}-w{window}-t{i}",
                    timestamp=float(window * cfg.txns_per_window + i),
                    method=m,
                    psp_id=psp_id,
                    bank_id=bank_id,
                    amount=amount,
                    success=success,
                    failure_code=failure_code,
                    latency_ms=latency,
                    cohort=cohort,
                    geography=geo,
                )
            )

    gt = _ground_truth(incident, graph)
    return txns, gt


def _failure_code(method: Method, drop: float) -> str:
    """A plausible failure code. Incident-driven failures get a distinct code from
    baseline noise failures -- but note the reasoner treats codes as opaque; codes
    do NOT leak ground truth (they are just observations)."""
    if drop > 0.0:
        return "BANK_DECLINE" if method != Method.NETBANKING else "GATEWAY_TIMEOUT"
    return "INSUFFICIENT_FUNDS"


def _ground_truth(incident: Incident, graph: PaymentGraph) -> GroundTruth:
    it = incident.incident_type
    if it == IncidentType.SHARED_BANK:
        affected = graph.psps_for_bank(incident.target_id or "")
        return GroundTruth(incident, affected, list(_METHODS), [incident.target_id or ""])
    if it == IncidentType.SINGLE_PSP:
        return GroundTruth(incident, [incident.target_id or ""], list(_METHODS), [incident.target_id or ""])
    if it == IncidentType.METHOD:
        return GroundTruth(incident, sorted(graph.psps.keys()), [Method(incident.target_id)], [incident.target_id or ""])
    if it == IncidentType.COINCIDENTAL:
        causes = [c for c in (incident.target_id, incident.secondary_target_id) if c]
        return GroundTruth(incident, sorted(causes), list(_METHODS), sorted(causes))
    # NONE
    return GroundTruth(incident, [], [], [])
