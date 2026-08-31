"""Deterministic transaction generator (BUILD_SPEC §3.5).

``generate`` produces per-window transactions with realistic noise and, during
the incident window(s), lowers success on exactly the paths the incident should
affect. It returns the txn log the reasoner sees PLUS the ``GroundTruth`` the
reasoner must NOT see.

Determinism: everything flows from ``cfg.seed`` via a single ``random.Random``.
There is no unseeded randomness anywhere. Ground truth is never stored on a
``Transaction`` — it is returned as a separate value.
"""

import random

from ..model.entities import Method, Transaction
from ..model.graph import PaymentGraph
from .config import SimConfig
from .incidents import (
    GroundTruth,
    Incident,
    IncidentType,
    affected_psps,
    apply_drop,
    ground_truth,
)

# Bounded random ranges for the honest adversary (BUILD_SPEC §3.5). Severity
# overlaps the noise band (noise_std) at its low end so some incidents are
# genuinely ambiguous and the honest answer is do_nothing.
_SEVERITY_RANGE = (0.02, 0.45)
_MIN_DURATION = 2
_MAX_DURATION = 5

# Deterministic per-cohort / per-geography success multipliers so a naive
# "everything dropped" reading is wrong (base success varies by segment).
_COHORT_ADJ = {"new": -0.02, "returning": 0.0, "high_value": 0.01}
_GEO_ADJ = {"north": 0.0, "south": -0.01, "east": 0.005, "west": -0.005}


def _schedule(rng: random.Random, n_windows: int) -> tuple[int, int, float]:
    """Randomized onset / duration / severity within bounded ranges (no fixed
    schedule that a reasoner could learn as a tell)."""
    duration = rng.randint(_MIN_DURATION, _MAX_DURATION)
    latest_start = max(0, n_windows - duration - 1)
    start = rng.randint(0, latest_start)
    end = start + duration
    severity = rng.uniform(*_SEVERITY_RANGE)
    return start, end, severity


def _finalize_incident(incident: Incident, rng: random.Random, cfg: SimConfig) -> None:
    """Fill in onset/duration/severity per seed unless the caller pinned them.

    A caller can pin exact values (tests do this); otherwise we draw them from the
    bounded ranges. COINCIDENTAL draws a SECOND independent onset/severity so its
    two faults are not secretly synchronized."""
    if incident.incident_type is IncidentType.NONE:
        return
    if incident.end_window <= incident.start_window and incident.severity == 0.0:
        start, end, severity = _schedule(rng, cfg.n_windows)
        incident.start_window = start
        incident.end_window = end
        incident.severity = severity
    if incident.incident_type is IncidentType.COINCIDENTAL:
        if (
            incident.secondary_end_window <= incident.secondary_start_window
            and incident.secondary_severity == 0.0
        ):
            start, end, severity = _schedule(rng, cfg.n_windows)
            incident.secondary_start_window = start
            incident.secondary_end_window = end
            incident.secondary_severity = severity


def _path_severity(
    incident: Incident,
    window: int,
    method: Method,
    psp_id: str,
    shared_targets: set[str],
) -> float:
    """Total proportional success drop for one (method, psp) path in ``window``."""
    it = incident.incident_type
    if it is IncidentType.NONE:
        return 0.0
    active = incident.start_window <= window <= incident.end_window
    if it is IncidentType.SHARED_BANK:
        return incident.severity if (active and psp_id in shared_targets) else 0.0
    if it is IncidentType.SINGLE_PSP:
        return incident.severity if (active and psp_id == incident.target_id) else 0.0
    if it is IncidentType.METHOD:
        hit = active and incident.target_id and method == Method(incident.target_id)
        return incident.severity if hit else 0.0
    if it is IncidentType.COINCIDENTAL:
        drop = 0.0
        if active and psp_id == incident.target_id:
            drop = incident.severity
        sec_active = (
            incident.secondary_start_window
            <= window
            <= incident.secondary_end_window
        )
        if sec_active and psp_id == incident.secondary_target_id:
            drop = max(drop, incident.secondary_severity)
        return drop
    return 0.0


def generate(
    graph: PaymentGraph, cfg: SimConfig, incident: Incident
) -> tuple[list[Transaction], GroundTruth]:
    """Deterministic given ``cfg.seed``. See module docstring / BUILD_SPEC §3.5."""
    rng = random.Random(cfg.seed)
    _finalize_incident(incident, rng, cfg)
    shared_targets = (
        set(affected_psps(graph, incident))
        if incident.incident_type is IncidentType.SHARED_BANK
        else set()
    )

    txns: list[Transaction] = []
    counter = 0
    for window in range(cfg.n_windows):
        for _ in range(cfg.txns_per_window):
            method = _pick_method(rng, cfg)
            psp_id = _pick_psp(rng, graph, method)
            bank_id = graph.settles_via[psp_id]
            cohort = rng.choice(cfg.cohorts)
            geography = rng.choice(cfg.geographies)

            base = cfg.base_success[method]
            base += _COHORT_ADJ.get(cohort, 0.0) + _GEO_ADJ.get(geography, 0.0)
            base += rng.gauss(0.0, cfg.noise_std)  # per-window jitter
            drop = _path_severity(incident, window, method, psp_id, shared_targets)
            success_rate = apply_drop(_clamp(base), drop)

            success = rng.random() < success_rate
            latency = rng.uniform(80.0, 220.0)
            if not success:
                latency += rng.uniform(50.0, 400.0)  # failures run slower
            counter += 1
            txns.append(
                Transaction(
                    txn_id=f"t{counter}",
                    # integer part = window index (aggregate buckets by int(ts));
                    # fractional part keeps timestamps within a window ordered.
                    timestamp=window + counter * 1e-9,
                    method=method,
                    psp_id=psp_id,
                    bank_id=bank_id,
                    amount=round(rng.uniform(50.0, 5000.0), 2),
                    success=success,
                    failure_code=None if success else "DECLINED",
                    latency_ms=round(latency, 2),
                    cohort=cohort,
                    geography=geography,
                )
            )
    return txns, ground_truth(graph, incident)


def _pick_method(rng: random.Random, cfg: SimConfig) -> Method:
    return rng.choice(list(cfg.base_success.keys()))


def _pick_psp(rng: random.Random, graph: PaymentGraph, method: Method) -> str:
    entries = graph.routing[method]
    psps = [p for p, _ in entries]
    weights = [w for _, w in entries]
    return rng.choices(psps, weights=weights, k=1)[0]


def _clamp(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x
