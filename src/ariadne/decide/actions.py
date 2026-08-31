"""Bounded action model (BUILD_SPEC §3.10, adapter §6).

Thin-loop scope: only ``reroute`` and ``do_nothing`` are implemented for now.
``disable_method`` and ``retry_fallback`` are Phase 7 / Tier 2 and intentionally
omitted. Every builder validates its bounds and refuses out-of-bounds actions.

This module never sees injected truth: it MUST NOT import from the simulator's
ground-truth module (BUILD_SPEC §1 rule 3).
"""

import itertools
from dataclasses import dataclass, field

from ..model.entities import Method
from ..model.graph import PaymentGraph

_DECISION_COUNTER = itertools.count(1)


@dataclass
class Action:
    kind: str  # "reroute" | "disable_method" | "retry_fallback" | "do_nothing"
    params: dict
    decision_id: str
    evidence_path: list[str] = field(default_factory=list)
    confidence: float = 0.0
    expected_recovery: float = 0.0


def _next_decision_id(prefix: str) -> str:
    return f"{prefix}-{next(_DECISION_COUNTER)}"


def reroute(
    graph: PaymentGraph,
    method: Method,
    from_psp: str,
    to_psp: str,
    bad_nodes: set[str],
    expected_recovery: float,
    confidence: float,
    evidence_path: list[str] | None = None,
) -> Action:
    """Move ``method``'s routing weight from ``from_psp`` to ``to_psp``.

    Bounds (adapter §6): only touches one method's routing weights; ``from_psp``
    must actually carry ``method``; the target must be a real PSP that also carries
    ``method``; and it can NEVER target a node the graph shows is also bad
    (``bad_nodes``). Out-of-bounds requests raise ``ValueError`` so the policy can
    only ever emit a valid reroute.
    """
    carriers = {psp for psp, _ in graph.routing.get(method, [])}
    if from_psp not in carriers:
        raise ValueError(f"{from_psp} does not carry {method.value}")
    if to_psp not in graph.psps:
        raise ValueError(f"unknown target PSP {to_psp}")
    if to_psp == from_psp:
        raise ValueError("cannot reroute a PSP onto itself")
    if to_psp in bad_nodes:
        raise ValueError(f"cannot reroute onto bad node {to_psp}")
    return Action(
        kind="reroute",
        params={
            "method": method.value,
            "from_psp": from_psp,
            "to_psp": to_psp,
        },
        decision_id=_next_decision_id("reroute"),
        evidence_path=list(evidence_path or []),
        confidence=confidence,
        expected_recovery=expected_recovery,
    )


def do_nothing(reason: str, confidence: float) -> Action:
    """The first-class safety default. Correct on incident D is a scored win."""
    return Action(
        kind="do_nothing",
        params={"reason": reason},
        decision_id=_next_decision_id("do_nothing"),
        evidence_path=[reason],
        confidence=confidence,
        expected_recovery=0.0,
    )
