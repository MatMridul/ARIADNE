"""Action selection: attribution -> bounded action (BUILD_SPEC §3.11, adapter §6).

The intervention_threshold is the risk-appetite dial (swept by the eval), NOT
hardcoded. Below threshold -> do_nothing (the safety default). Above threshold,
choose the bounded action with best expected recovery for the diagnosed cause,
never routing onto a node the stats show is also bad and never disabling the last
working method.

Action menu: reroute + do_nothing (Tier-1); disable_method + retry_fallback (Tier-2),
selected inline by cause kind. No feature flag.
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


def _method_by_id(stats: dict[str, NodeStats]) -> dict[str, NodeStats]:
    return {s.node_id: s for s in stats.values() if s.node_kind == "method"}


def _active_methods(graph: PaymentGraph) -> list[Method]:
    return [m for m in graph.routing if any(w > 0.0 for _p, w in graph.routing[m])]


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

    # Tier-2: method-level cause -> retry retriable failures on that method.
    if attr.root_cause_kind == "method":
        m = Method(attr.root_cause_id)
        active = _active_methods(graph)
        m_stats = _method_by_id(stats).get(attr.root_cause_id)
        rate = m_stats.success_rate if m_stats else 1.0
        # if the method is severely down and a fallback method exists, disable it;
        # else retry its retriable failures (the safer, additive action).
        if rate < 0.5 and len(active) > 1:
            return A.disable_method(
                graph, m, active,
                confidence=attr.confidence,
                expected_recovery=0.0,
                evidence_path=attr.evidence_path + [f"disable severely-down method {m.value}"],
            )
        return A.retry_fallback(
            m, max_retries=2, retriable_codes=["GATEWAY_TIMEOUT"],
            confidence=attr.confidence,
            expected_recovery=(m_stats.volume * (1 - rate) * 0.5 * avg_amount) if m_stats else 0.0,
            evidence_path=attr.evidence_path + [f"retry retriable failures on method {m.value}"],
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


def apply_action_config(cfg, action: "Action"):
    """Return a SimConfig reflecting a Tier-2 action that changes runtime behaviour
    rather than routing (retry_fallback). do_nothing/reroute/disable_method leave the
    config unchanged (their effect is a graph change, handled by apply_action)."""
    from dataclasses import replace
    if action.kind == "retry_fallback":
        return replace(
            cfg,
            retry_method=action.params["method"],
            retry_codes=tuple(action.params["retriable_codes"]),
            retry_max=action.params["max_retries"],
        )
    return cfg
