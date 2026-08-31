"""Reproducible incident batch (BUILD_SPEC §3.12).

Mixes all FIVE incident types (A shared-bank, B single-PSP, C method, D no-cause,
E coincidental-different-banks) plus clean windows, so 'money recovered across a
batch' (Track 03 bar) is measurable and both do-nothing (D) and don't-over-attribute
(B, E) behaviours are exercised. Onset/duration/severity are randomised per seed
inside make_incident (engine), so each scenario in the batch is genuinely varied.

Batch composition (adapter Q4, build-time tuning; documented here so runs reproduce):
2x A, 1x B, 1x C, 2x D, 1x E per seed -> 7 scenarios/seed. A and D are doubled
because A is the thesis case and D is the headline safety case.
"""
from __future__ import annotations

from ariadne.model.entities import Method
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import Incident, IncidentType, make_incident

# (incident_type, target_id, secondary_target_id) templates for one seed's batch
_BATCH_TEMPLATE: list[tuple[IncidentType, str | None, str | None]] = [
    (IncidentType.SHARED_BANK, "bank_A", None),
    (IncidentType.SHARED_BANK, "bank_A", None),
    (IncidentType.SINGLE_PSP, "psp_3", None),
    (IncidentType.METHOD, Method.CARD.value, None),
    (IncidentType.NONE, None, None),
    (IncidentType.NONE, None, None),
    (IncidentType.COINCIDENTAL, "psp_1", "psp_3"),
]


def scenario_batch(seed: int) -> list[tuple[Incident, SimConfig]]:
    """A reproducible batch for one seed. Each scenario gets its own SimConfig
    seeded distinctly (seed*100 + index) so scenarios don't share draws, while the
    whole batch remains deterministic in `seed`."""
    batch: list[tuple[Incident, SimConfig]] = []
    for idx, (it, target, secondary) in enumerate(_BATCH_TEMPLATE):
        sub_seed = seed * 100 + idx
        cfg = SimConfig(seed=sub_seed)
        inc = make_incident(
            it, sub_seed, cfg.n_windows,
            target_id=target, secondary_target_id=secondary,
        )
        batch.append((inc, cfg))
    return batch
