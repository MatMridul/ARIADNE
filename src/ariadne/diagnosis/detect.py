"""Deterministic detection (BUILD_SPEC §3.7).

``detect`` applies a deterministic threshold on each node's delta vs. its rolling
baseline and reports which nodes breached it. It is shared by ARIADNE and the
baseline (both start from the identical per-node ``NodeStats``).

This module observes derived per-node stats only. It MUST NOT import from the
simulator's ground-truth module or otherwise see injected truth (BUILD_SPEC §1
rule 3).
"""

from dataclasses import dataclass

from ..observe.aggregate import NodeStats


@dataclass
class Detection:
    triggered: bool
    dropped_nodes: list[str]  # nodes whose delta breaches the detection threshold
    window: int


def detect(
    stats: dict[str, NodeStats], detect_threshold: float, window: int = 0
) -> Detection:
    """Deterministic threshold on delta vs. baseline. Shared by ARIADNE and baseline.

    A node is "dropped" when its success rate fell below its rolling baseline by
    more than ``detect_threshold`` (i.e. ``delta <= -detect_threshold``). Both PSP
    and method nodes are eligible, so the same routine also surfaces method-level
    faults. ``window`` is threaded through purely for provenance.
    """
    dropped = sorted(
        node_id for node_id, s in stats.items() if s.delta <= -detect_threshold
    )
    return Detection(triggered=bool(dropped), dropped_nodes=dropped, window=window)
