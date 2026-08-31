"""Aggregation of raw transactions into per-window node statistics (BUILD_SPEC §3.6).

Both ARIADNE and the fair baseline receive the EXACT SAME NodeStats for PSPs and
methods (identical raw inputs, hostile-review fix #3). Bank-level health is NOT
produced here -- it is DERIVED by ARIADNE in diagnosis/ from these same PSP stats
via the graph. That derivation is the only thing ARIADNE has that the baseline
does not; nothing else in the inputs differs.
"""
from __future__ import annotations

from dataclasses import dataclass

from ariadne.model.entities import Transaction
from ariadne.model.graph import PaymentGraph

_TXNS_PER_WINDOW_DEFAULT = 500


@dataclass
class NodeStats:
    node_id: str
    node_kind: str  # "psp" | "method" | "bank(derived)"
    success_rate: float
    volume: int
    avg_latency_ms: float
    baseline_rate: float  # rolling historical baseline (prior windows)
    delta: float  # success_rate - baseline_rate


def _window_of(txn: Transaction, txns_per_window: int) -> int:
    return int(txn.timestamp // txns_per_window)


def _rate(succ: int, n: int) -> float:
    return succ / n if n else 0.0


def _aggregate(
    txns: list[Transaction], key
) -> dict[str, tuple[int, int, float]]:
    """key: Transaction -> node_id. Returns node_id -> (successes, volume, latency_sum)."""
    out: dict[str, tuple[int, int, float]] = {}
    for t in txns:
        node_id = key(t)
        s, n, lat = out.get(node_id, (0, 0, 0.0))
        out[node_id] = (s + (1 if t.success else 0), n + 1, lat + t.latency_ms)
    return out


def window_stats(
    txns: list[Transaction],
    graph: PaymentGraph,
    window: int,
    txns_per_window: int = _TXNS_PER_WINDOW_DEFAULT,
) -> dict[str, NodeStats]:
    """Aggregate ONE window into per-PSP and per-method NodeStats.

    `txns` is the full run log; this function selects the given window and uses the
    windows strictly BEFORE it as the rolling historical baseline. Diagnosing a
    window from its own observations only (no cross-incident learning) -- the
    baseline is per-run rolling history, not learned across incidents.
    """
    cur = [t for t in txns if _window_of(t, txns_per_window) == window]
    prior = [t for t in txns if _window_of(t, txns_per_window) < window]

    stats: dict[str, NodeStats] = {}

    for kind, key in (("psp", lambda t: t.psp_id), ("method", lambda t: t.method.value)):
        cur_agg = _aggregate(cur, key)
        prior_agg = _aggregate(prior, key)
        for node_id, (s, n, lat) in cur_agg.items():
            rate = _rate(s, n)
            ps, pn, _pl = prior_agg.get(node_id, (0, 0, 0.0))
            baseline = _rate(ps, pn) if pn else rate  # no history -> self (delta 0)
            stats[_qual(kind, node_id)] = NodeStats(
                node_id=node_id,
                node_kind=kind,
                success_rate=rate,
                volume=n,
                avg_latency_ms=(lat / n if n else 0.0),
                baseline_rate=baseline,
                delta=rate - baseline,
            )
    return stats


def _qual(kind: str, node_id: str) -> str:
    """Namespaced key so a psp and a method never collide in the stats dict."""
    return f"{kind}:{node_id}"


def psp_stats(stats: dict[str, NodeStats]) -> dict[str, NodeStats]:
    return {s.node_id: s for s in stats.values() if s.node_kind == "psp"}


def method_stats(stats: dict[str, NodeStats]) -> dict[str, NodeStats]:
    return {s.node_id: s for s in stats.values() if s.node_kind == "method"}
