"""Simulator configuration (BUILD_SPEC §3.3).

Pure data. All defaults are declared here so a run is fully described by a
``SimConfig`` plus an ``Incident``. Mutable defaults (the base-success dict and
the cohort/geography tuples) use ``field(default_factory=...)`` so instances do
not share state.
"""

from dataclasses import dataclass, field

from ..model.entities import Method


def _default_base_success() -> dict[Method, float]:
    return {Method.UPI: 0.97, Method.CARD: 0.95, Method.NETBANKING: 0.93}


@dataclass
class SimConfig:
    seed: int
    n_windows: int = 20  # time windows in a run
    txns_per_window: int = 500
    base_success: dict[Method, float] = field(default_factory=_default_base_success)
    noise_std: float = 0.01  # per-window jitter on success rate
    cohorts: tuple[str, ...] = field(
        default_factory=lambda: ("new", "returning", "high_value")
    )
    geographies: tuple[str, ...] = field(
        default_factory=lambda: ("north", "south", "east", "west")
    )
