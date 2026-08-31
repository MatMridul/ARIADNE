"""Detection: did something drop vs. baseline, and where (BUILD_SPEC §3.7).

Deterministic threshold on delta vs. rolling baseline. Shared by ARIADNE and the
baseline. Imports NOTHING from simulator/ -- the diagnoser never sees ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass

from ariadne.observe.aggregate import NodeStats


@dataclass
class Detection:
    triggered: bool
    dropped_nodes: list[str]  # PSP node_ids whose delta breaches the threshold
    window: int


def detect(
    stats: dict[str, NodeStats], detect_threshold: float, window: int = 0
) -> Detection:
    """A PSP is 'down' when its success rate fell below baseline by more than
    detect_threshold (delta <= -detect_threshold). Only PSP-level nodes are
    considered here; method/bank reasoning happens in attribute()."""
    dropped = sorted(
        s.node_id
        for s in stats.values()
        if s.node_kind == "psp" and s.delta <= -detect_threshold
    )
    return Detection(triggered=bool(dropped), dropped_nodes=dropped, window=window)
