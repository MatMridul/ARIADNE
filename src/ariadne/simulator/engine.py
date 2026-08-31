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
import random
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


def _txn_rng(seed: int, window: int, i: int) -> random.Random:
    """A per-transaction PRNG seeded deterministically from (seed, window, i).
    Its draw sequence depends ONLY on these -- never on the routing config -- so the
    shared-seed counterfactual holds (an action that changes routing does not
    reshuffle demand or failure draws). Faster than hashing every quantity."""
    return random.Random((seed * 1_000_003 + window) * 1_000_003 + i)


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


def _window_noise(cfg: SimConfig) -> dict[tuple[int, str], float]:
    """Per-(window, method) success-rate noise, deterministic from cfg.seed.
    Precomputed once so it is stable regardless of routing (shared-seed)."""
    out: dict[tuple[int, str], float] = {}
    rng = random.Random(cfg.seed * 7_777_777 + 13)
    for window in range(cfg.n_windows):
        for m in _METHODS:
            out[(window, m.value)] = (rng.random() - 0.5) * 2.0 * cfg.noise_std
    return out


def _effective_rate(
    cfg: SimConfig,
    method: Method,
    cohort: str,
    geography: str,
    noise: float,
    drop: float,
) -> float:
    base = cfg.base_success[method]
    base += cfg.cohort_offset(cohort) + cfg.geography_offset(geography)
    rate = base + noise - drop
    return min(1.0, max(0.0, rate))


def generate(
    graph: PaymentGraph, cfg: SimConfig, incident: Incident
) -> tuple[list[Transaction], GroundTruth]:
    """Deterministic given cfg.seed. Returns (transactions, ground_truth).

    Ground truth is a SEPARATE return value; it is never embedded in a Transaction.
    """
    txns: list[Transaction] = []
    noise_map = _window_noise(cfg)
    n_methods = len(_METHODS)
    n_cohorts = len(cfg.cohorts)
    n_geos = len(cfg.geographies)
    for window in range(cfg.n_windows):
        for i in range(cfg.txns_per_window):
            rng = _txn_rng(cfg.seed, window, i)
            # demand attributes (drawn first, in a fixed order -> same regardless of
            # routing config, so the shared-seed counterfactual holds)
            m = _METHODS[int(rng.random() * n_methods)]
            cohort = cfg.cohorts[int(rng.random() * n_cohorts)]
            geo = cfg.geographies[int(rng.random() * n_geos)]
            amount = cfg.avg_amount * (0.5 + rng.random())
            r_route = rng.random()
            r_success = rng.random()
            r_latency = rng.random()

            psp_id = _routing_choice(graph, m, r_route)
            if psp_id == "":
                continue  # method fully disabled: transaction cannot be placed
            bank_id = graph.settles_via.get(psp_id, "")

            drop = _incident_drop(incident, graph, window, psp_id, m)
            rate = _effective_rate(cfg, m, cohort, geo, noise_map[(window, m.value)], drop)

            success = r_success < rate
            latency = cfg.base_latency_ms * (1.0 + r_latency)
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
