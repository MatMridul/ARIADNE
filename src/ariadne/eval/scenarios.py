"""Reproducible scenario batch (BUILD_SPEC §3.12).

``scenario_batch(seed)`` builds a deterministic mix of all FIVE incident types
plus clean (no-cause) windows so "money recovered across a batch" is measurable
and the do-nothing (D) and don't-over-attribute (B, E) behaviours are exercised.

Only the incident *type* and its graph-derived target(s) are pinned here; the
onset / duration / severity are left unset so the engine draws them per seed
(BUILD_SPEC §3.5). Each scenario carries its own ``SimConfig`` with a distinct
per-scenario seed derived from the batch seed, so the batch is fully reproducible
yet the scenarios are not secretly synchronized.

This is part of ``eval/`` — the ONLY layer allowed to read GroundTruth.
"""

from ..model.graph import PaymentGraph, default_graph
from ..simulator.config import SimConfig
from ..simulator.incidents import Incident, IncidentType

# ---------------------------------------------------------------------------
# Batch mix (adapter §8 Q4 — build-time tuning, no DR needed).
#
# The batch runs this many scenarios of each kind, so every headline behaviour is
# exercised more than once per seed and the aggregate money/safety numbers are not
# dominated by a single draw:
#
#   A shared-bank            x2   (the thesis / recovery driver)
#   B single-PSP             x2   (no over-attribution control)
#   C method                 x1   (method-level fault, diagnosable end-to-end)
#   D noise / no-cause       x2   (do_nothing is the correct, scored win)
#   E coincidental           x2   (two PSPs, different banks — no bank blame)
#   clean (== D, no target)  x1   (extra quiet window; another do_nothing win)
#
# Total: 10 scenarios per seed. Counts are deliberately small so run_sweep stays
# fast, while still giving each incident type repeated coverage.
# ---------------------------------------------------------------------------
_A_COUNT = 2
_B_COUNT = 2
_C_COUNT = 1
_D_COUNT = 2
_E_COUNT = 2
_CLEAN_COUNT = 1


def _shared_bank(graph: PaymentGraph) -> str:
    shared = graph.shared_banks()
    return next(iter(shared)) if shared else "bank_A"


def _primary_psp(graph: PaymentGraph) -> str:
    return sorted(graph.psps_for_bank(_shared_bank(graph)))[0]


def _other_bank_psp(graph: PaymentGraph, shared_bank: str) -> str:
    return next(
        (p for p, b in sorted(graph.settles_via.items()) if b != shared_bank),
        "psp_3",
    )


def _incident_a(graph: PaymentGraph) -> Incident:
    return Incident(incident_type=IncidentType.SHARED_BANK, target_id=_shared_bank(graph))


def _incident_b(graph: PaymentGraph) -> Incident:
    return Incident(incident_type=IncidentType.SINGLE_PSP, target_id=_primary_psp(graph))


def _incident_c(graph: PaymentGraph) -> Incident:
    # A method-level fault: pick a method carried by PSPs on more than one bank so
    # the diagnoser must reach for the METHOD explanation rather than a bank.
    return Incident(incident_type=IncidentType.METHOD, target_id="upi")


def _incident_d(graph: PaymentGraph) -> Incident:
    # No real cause: onset/severity irrelevant (engine leaves NONE untouched).
    return Incident(incident_type=IncidentType.NONE, target_id=None)


def _incident_e(graph: PaymentGraph) -> Incident:
    # COINCIDENTAL means two PSPs on DIFFERENT banks fail AT THE SAME TIME by
    # chance. If the two faults were scheduled on independent windows they would
    # not overlap and the "coincidental" property would be lost, so the two onsets
    # are pinned to the SAME window here (the honest coincidental test: both down
    # together, on different banks, so no single bank covers the down set).
    bank = _shared_bank(graph)
    return Incident(
        incident_type=IncidentType.COINCIDENTAL,
        target_id=sorted(graph.psps_for_bank(bank))[0],
        secondary_target_id=_other_bank_psp(graph, bank),
        start_window=8,
        end_window=11,
        severity=0.4,
        secondary_start_window=8,
        secondary_end_window=11,
        secondary_severity=0.4,
    )


def scenario_batch(seed: int) -> list[tuple[Incident, SimConfig]]:
    """A reproducible batch mixing all five incident types plus clean windows.

    Deterministic per ``seed``: each scenario gets a distinct derived seed so its
    randomized onset/duration/severity is reproducible but independent."""
    graph = default_graph()
    plan: list = []
    plan += [(_incident_a, "A")] * _A_COUNT
    plan += [(_incident_b, "B")] * _B_COUNT
    plan += [(_incident_c, "C")] * _C_COUNT
    plan += [(_incident_d, "D")] * _D_COUNT
    plan += [(_incident_e, "E")] * _E_COUNT
    plan += [(_incident_d, "clean")] * _CLEAN_COUNT

    batch: list[tuple[Incident, SimConfig]] = []
    for idx, (builder, _kind) in enumerate(plan):
        # Distinct, reproducible per-scenario seed derived from the batch seed.
        scenario_seed = seed * 1000 + idx
        batch.append((builder(graph), SimConfig(seed=scenario_seed)))
    return batch
