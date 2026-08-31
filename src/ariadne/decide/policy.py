"""Action selection: attribution -> bounded action (BUILD_SPEC §3.11, adapter §6).

The intervention_threshold is the risk-appetite dial (swept by the eval), NOT
hardcoded. Below threshold -> do_nothing (the safety default). Above threshold,
choose the bounded action with best expected recovery for the diagnosed cause,
never routing onto a node the stats show is also bad and never disabling the last
working method.

Tier-1 action menu: reroute + do_nothing. (disable_method / retry_fallback are
Tier-2, wired in via `enable_tier2`.)
"""
from __future__ import annotations

from ariadne.decide import actions as A
from ariadne.decide.actions import Action
from ariadne.diagnosis.attribute import Attribution
from ariadne.model.entities import Method
from ariadne.model.graph import PaymentGraph
from ariadne.observe.aggregate import NodeStats

_HEALTHY_DELTA = -0.03  # a PSP is a safe reroute target if its delta is above this


def _psp_by_id(stats: dict[str, NodeStats]) -> dict[str, NodeStats]:
    return {s.node_id: s for s in stats.values() if s.node_kind == "psp"}


def _healthy_targets(
    stats: dict[str, NodeStats], graph: PaymentGraph, avoid: set[str]
) -> list[str]:
    psps = _psp_by_id(stats)
    return sorted(
        pid
        for pid in graph.psps
        if pid not in avoid
        and (pid not in psps or psps[pid].delta >= _HEALTHY_DELTA)
    )


def _bad_psps(attr: Attribution, graph: PaymentGraph) -> set[str]:
    if attr.root_cause_kind == "bank":
        return set(graph.psps_for_bank(attr.root_cause_id)) | set(attr.psp_causes)
    if attr.root_cause_kind == "psp":
        return set(attr.psp_causes) or {attr.root_cause_id}
    return set()


def _expected_recovery(
    stats: dict[str, NodeStats], bad: set[str], target: str
) -> float:
    """Recovery estimate: sum over bad PSPs of (target_rate - bad_rate) * bad_volume.
    Uses only observed stats -- an estimate, carried as expected_recovery."""
    psps = _psp_by_id(stats)
    target_rate = psps[target].success_rate if target in psps else 1.0
    gain = 0.0
    for pid in bad:
        if pid in psps:
            s = psps[pid]
            gain += max(0.0, target_rate - s.success_rate) * s.volume
    return gain


def select_action(
    attr: Attribution,
    graph: PaymentGraph,
    stats: dict[str, NodeStats],
    intervention_threshold: float,
    *,
    avg_amount: float = 1000.0,
) -> Action:
    if attr.root_cause_kind == "none" or attr.confidence < intervention_threshold:
        return A.do_nothing(
            reason=f"confidence {attr.confidence:.2f} below threshold "
            f"{intervention_threshold:.2f}"
            if attr.root_cause_kind != "none"
            else "no cause diagnosed",
            confidence=attr.confidence,
        )

    bad = _bad_psps(attr, graph)
    if not bad:
        return A.do_nothing(reason="no reroutable bad PSP", confidence=attr.confidence)

    targets = _healthy_targets(stats, graph, avoid=bad)
    if not targets:
        # no healthy sibling to reroute onto -> stay put (safety over action)
        return A.do_nothing(
            reason="no healthy reroute target available", confidence=attr.confidence
        )

    # choose the target maximising expected recovery
    best_target = max(targets, key=lambda t: _expected_recovery(stats, bad, t))
    recovery_txns = _expected_recovery(stats, bad, best_target)
    expected_recovery_money = recovery_txns * avg_amount

    # reroute the worst bad PSP's traffic (thin loop reroutes one method: UPI as
    # the representative method; the eval re-simulates ALL methods off bad PSPs).
    worst = min(bad, key=lambda p: _psp_by_id(stats).get(p, None).delta
                if p in _psp_by_id(stats) else 0.0)
    return A.reroute(
        graph,
        method=Method.UPI,
        from_psp=worst,
        to_psp=best_target,
        confidence=attr.confidence,
        expected_recovery=expected_recovery_money,
        evidence_path=attr.evidence_path
        + [f"reroute bad PSPs {sorted(bad)} -> healthy {best_target}"],
    )


def apply_action(graph: PaymentGraph, action: Action) -> PaymentGraph:
    """Return the post-action graph config for re-simulation. do_nothing returns
    the graph unchanged. reroute moves ALL methods' traffic off the source PSP onto
    the target (the action's real scope), so the shared-seed counterfactual measures
    the full effect of the routing change, not just one method."""
    if action.kind == "do_nothing":
        return graph
    if action.kind == "reroute":
        from_psp = action.params["from_psp"]
        to_psp = action.params["to_psp"]
        g = graph
        for m in list(graph.routing.keys()):
            weights = dict(graph.routing.get(m, []))
            if weights.get(from_psp, 0.0) > 0.0:
                g = g.reroute(m, from_psp=from_psp, to_psp=to_psp)
                graph = g  # chain rerouting across methods
        return g
    if action.kind == "disable_method":
        m = Method(action.params["method"])
        new_routing = {k: list(v) for k, v in graph.routing.items()}
        new_routing[m] = [(p, 0.0) for p, _w in graph.routing.get(m, [])]
        return PaymentGraph(
            psps=dict(graph.psps),
            banks=dict(graph.banks),
            routing=new_routing,
            settles_via=dict(graph.settles_via),
        )
    # retry_fallback is additive (modeled in metrics), no graph change
    return graph
