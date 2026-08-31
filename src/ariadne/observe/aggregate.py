"""Window aggregation of raw transactions (BUILD_SPEC §3.6).

Aggregates one window's raw transactions into per-PSP and per-method
``NodeStats``. Both ARIADNE and the fair baseline receive the *exact same*
per-PSP and per-method stats from here (BUILD_SPEC §3.6 hostile-review fix #3).

Bank-level health is NOT produced here — it is DERIVED by ARIADNE in diagnosis
from these same per-PSP inputs via the graph. That derivation is the only thing
ARIADNE has that the baseline does not.

This module observes raw transactions only. It MUST NOT import from
``simulator/incidents.py`` (ground truth is never visible to observation or
diagnosis); it derives everything from the transaction stream and the static
graph topology.
"""

from dataclasses import dataclass

from ..model.entities import Method, Transaction
from ..model.graph import PaymentGraph


@dataclass
class NodeStats:
    node_id: str
    node_kind: str  # "psp" | "method" | "bank(derived)"
    success_rate: float
    volume: int
    avg_latency_ms: float
    baseline_rate: float  # rolling historical baseline
    delta: float  # success_rate - baseline_rate


def _window_of(txn: Transaction) -> int:
    """Window index a transaction belongs to (engine stamps it in the timestamp)."""
    return int(txn.timestamp)


def _rate(successes: int, volume: int) -> float:
    return successes / volume if volume else 0.0


def _rolling_baseline(
    history: dict[str, list[float]], node_id: str, current: float
) -> float:
    """Mean success rate for a node over prior windows; falls back to the current
    rate when there is no history (first window has no baseline yet)."""
    rates = history.get(node_id)
    if not rates:
        return current
    return sum(rates) / len(rates)


def _prior_window_rates(
    txns: list[Transaction], graph: PaymentGraph, window: int, kind: str
) -> dict[str, list[float]]:
    """Per-node success rate for each window strictly before ``window``."""
    per_window_hits: dict[int, dict[str, list[int]]] = {}
    for txn in txns:
        w = _window_of(txn)
        if w >= window:
            continue
        key = txn.psp_id if kind == "psp" else txn.method.value
        bucket = per_window_hits.setdefault(w, {})
        hit_total = bucket.setdefault(key, [0, 0])
        hit_total[0] += 1 if txn.success else 0
        hit_total[1] += 1
    history: dict[str, list[float]] = {}
    for _w, nodes in sorted(per_window_hits.items()):
        for key, (hits, total) in nodes.items():
            history.setdefault(key, []).append(_rate(hits, total))
    return history


def _node_stats_for_kind(
    txns: list[Transaction],
    graph: PaymentGraph,
    window: int,
    kind: str,
) -> dict[str, NodeStats]:
    """Aggregate the current window for either PSPs or methods."""
    hits: dict[str, int] = {}
    volume: dict[str, int] = {}
    latency: dict[str, float] = {}
    for txn in txns:
        if _window_of(txn) != window:
            continue
        key = txn.psp_id if kind == "psp" else txn.method.value
        volume[key] = volume.get(key, 0) + 1
        hits[key] = hits.get(key, 0) + (1 if txn.success else 0)
        latency[key] = latency.get(key, 0.0) + txn.latency_ms

    history = _prior_window_rates(txns, graph, window, kind)
    out: dict[str, NodeStats] = {}
    for key, vol in volume.items():
        rate = _rate(hits[key], vol)
        baseline = _rolling_baseline(history, key, rate)
        node_id = key if kind == "psp" else f"method_{key}"
        out[node_id] = NodeStats(
            node_id=node_id,
            node_kind=kind,
            success_rate=rate,
            volume=vol,
            avg_latency_ms=latency[key] / vol if vol else 0.0,
            baseline_rate=baseline,
            delta=rate - baseline,
        )
    return out


def window_stats(
    txns: list[Transaction], graph: PaymentGraph, window: int
) -> dict[str, NodeStats]:
    """Aggregate one window into per-PSP and per-method stats. ``txns`` is the full
    run stream; only the target ``window`` is summarized, with a rolling baseline
    drawn from strictly-earlier windows. Bank-level stats are intentionally NOT
    produced here (they are derived by ARIADNE in diagnosis)."""
    stats: dict[str, NodeStats] = {}
    stats.update(_node_stats_for_kind(txns, graph, window, "psp"))
    stats.update(_node_stats_for_kind(txns, graph, window, "method"))
    return stats
