"""Simulator configuration (BUILD_SPEC §3.3).

Base success rates and noise are build-time tuning choices (adapter Q5); the
values here are documented so runs reproduce. Everything downstream flows from
cfg.seed for determinism.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ariadne.model.entities import Method


def _default_base_success() -> dict[Method, float]:
    return {Method.UPI: 0.97, Method.CARD: 0.95, Method.NETBANKING: 0.93}


@dataclass
class SimConfig:
    seed: int
    n_windows: int = 20
    txns_per_window: int = 500
    base_success: dict[Method, float] = field(default_factory=_default_base_success)
    noise_std: float = 0.01  # per-window jitter on success rate
    cohorts: tuple[str, ...] = ("new", "returning", "high_value")
    geographies: tuple[str, ...] = ("north", "south", "east", "west")
    avg_amount: float = 1000.0     # rupees; mean transaction value
    base_latency_ms: float = 120.0

    # Per-cohort multiplicative offsets on the base success rate, so a naive
    # "everything dropped" reading is wrong (BUILD_SPEC §3.5). Small, bounded.
    def cohort_offset(self, cohort: str) -> float:
        return {"new": -0.02, "returning": 0.0, "high_value": 0.01}.get(cohort, 0.0)

    def geography_offset(self, geography: str) -> float:
        return {
            "north": 0.0,
            "south": 0.005,
            "east": -0.005,
            "west": 0.0,
        }.get(geography, 0.0)
