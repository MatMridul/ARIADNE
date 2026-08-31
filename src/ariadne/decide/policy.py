"""Action selection (BUILD_SPEC §3.11, adapter §6).

``select_action`` ties the intervention threshold (the risk-appetite dial) to
whether ARIADNE acts. Below the threshold it returns ``do_nothing``; above it, it
picks the bounded action with the best expected recovery — for the thin loop that
means rerouting traffic away from a diagnosed bad node onto a HEALTHY sibling,
never onto a node the graph shows is also bad.

SEAL: this module MUST NOT import from the simulator's ground-truth module or its
injected-truth types (BUILD_SPEC §1 rule 3).
"""

from ..model.entities import Method
from ..model.graph import PaymentGraph
from ..observe.aggregate import NodeStats
from ..diagnosis.attribute import Attribution
from .actions import Action, do_nothing, reroute


def _bad_psps(attr: Attribution, graph: PaymentGraph) -> set[str]:
    """PSPs the diagnosis implicates and must never be rerouted onto.

    For a bank cause, every PSP settling via that bank is implicated. For a PSP
    cause, the primary plus any secondary independent PSP causes.
    """
    bad: set[str] = set()
    if attr.root_cause_kind == "bank":
        bad.update(graph.psps_for_bank(attr.root_cause_id))
    elif attr.root_cause_kind == "psp":
        bad.add(attr.root_cause_id)
        bad.update(c for c in attr.secondary_causes if c in graph.psps)
    return bad


def _healthy_target(
    graph: PaymentGraph,
    method: Method,
    from_psp: str,
    bad: set[str],
    stats: dict[str, NodeStats],
) -> str | None:
    """A sibling PSP that carries ``method``, is not bad, and looks healthiest.

    Ranks candidates by their observed success rate (highest first) so the reroute
    targets the best available sibling. Returns None when no healthy sibling exists.
    """
    candidates = [
        psp
        for psp, _ in graph.routing.get(method, [])
        if psp != from_psp and psp not in bad
    ]
    if not candidates:
        return None

    def _rate(psp: str) -> float:
        s = stats.get(psp)
        return s.success_rate if s else 0.0

    candidates.sort(key=_rate, reverse=True)
    return candidates[0]


def _best_reroute(
    graph: PaymentGraph,
    stats: dict[str, NodeStats],
    bad: set[str],
    attr: Attribution,
) -> Action | None:
    """Best bounded reroute across the methods carried by any bad PSP.

    Expected recovery is estimated as the volume-weighted success-rate lift from
    moving a bad PSP's share of a method onto its healthy sibling.
    """
    best: Action | None = None
    for method in Method:
        entries = graph.routing.get(method, [])
        carriers = {psp for psp, _ in entries}
        for from_psp in sorted(bad & carriers):
            target = _healthy_target(graph, method, from_psp, bad, stats)
            if target is None:
                continue
            from_rate = stats[from_psp].success_rate if from_psp in stats else 0.0
            to_rate = stats[target].success_rate if target in stats else from_rate
            volume = stats[from_psp].volume if from_psp in stats else 0
            expected = max(0.0, (to_rate - from_rate)) * volume
            try:
                action = reroute(
                    graph,
                    method,
                    from_psp,
                    target,
                    bad_nodes=bad,
                    expected_recovery=expected,
                    confidence=attr.confidence,
                    evidence_path=attr.evidence_path
                    + [f"reroute {method.value}: {from_psp}->{target}"],
                )
            except ValueError:
                continue
            if best is None or action.expected_recovery > best.expected_recovery:
                best = action
    return best


def select_action(
    attr: Attribution,
    graph: PaymentGraph,
    stats: dict[str, NodeStats],
    intervention_threshold: float,
) -> Action:
    """See module docstring / BUILD_SPEC §3.11. ``intervention_threshold`` is a
    parameter (the risk-appetite dial), never hardcoded."""
    if attr.confidence < intervention_threshold or attr.root_cause_kind == "none":
        return do_nothing(
            reason="confidence below threshold", confidence=attr.confidence
        )

    bad = _bad_psps(attr, graph)
    action = _best_reroute(graph, stats, bad, attr)
    if action is None:
        # No healthy sibling to reroute onto (e.g. method-level fault or every
        # sibling is also bad) → the safe choice is to hold.
        return do_nothing(
            reason="no healthy reroute target available",
            confidence=attr.confidence,
        )
    return action
