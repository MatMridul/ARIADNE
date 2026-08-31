"""Bounded recovery actions (BUILD_SPEC §3.10, adapter §6).

Every action is bounded, audited (decision_id, evidence_path, confidence), and
stoppable. do_nothing is a first-class action. Builders validate their bounds and
raise on out-of-bounds requests; the policy layer avoids constructing those.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ariadne.model.entities import Method
from ariadne.model.graph import PaymentGraph


@dataclass
class Action:
    kind: str  # "reroute" | "disable_method" | "retry_fallback" | "do_nothing"
    params: dict
    decision_id: str
    evidence_path: list[str] = field(default_factory=list)
    confidence: float = 0.0
    expected_recovery: float = 0.0


def _decision_id(kind: str, params: dict) -> str:
    key = f"{kind}|{sorted(params.items())}".encode("utf-8")
    return kind + "-" + hashlib.blake2b(key, digest_size=6).hexdigest()


def reroute(
    graph: PaymentGraph,
    method: Method,
    from_psp: str,
    to_psp: str,
    *,
    confidence: float,
    expected_recovery: float,
    evidence_path: list[str],
) -> Action:
    """Move a method's traffic from a bad PSP to a healthy sibling.
    Bounds: to_psp must carry (or be able to carry) the method and must differ
    from from_psp. The policy layer guarantees to_psp is not itself degraded."""
    if from_psp == to_psp:
        raise ValueError("reroute target must differ from source")
    if from_psp not in graph.psps or to_psp not in graph.psps:
        raise ValueError("reroute endpoints must be known PSPs")
    params = {
        "method": method.value,
        "from_psp": from_psp,
        "to_psp": to_psp,
    }
    return Action(
        kind="reroute",
        params=params,
        decision_id=_decision_id("reroute", params),
        evidence_path=list(evidence_path),
        confidence=confidence,
        expected_recovery=expected_recovery,
    )


def disable_method(
    graph: PaymentGraph,
    method: Method,
    active_methods: list[Method],
    *,
    confidence: float,
    expected_recovery: float,
    evidence_path: list[str],
) -> Action:
    """Temporarily disable a method. Bound: never disable the LAST working method."""
    remaining = [m for m in active_methods if m != method]
    if not remaining:
        raise ValueError("refusing to disable the last working method")
    params = {"method": method.value}
    return Action(
        kind="disable_method",
        params=params,
        decision_id=_decision_id("disable_method", params),
        evidence_path=list(evidence_path),
        confidence=confidence,
        expected_recovery=expected_recovery,
    )


def retry_fallback(
    method: Method,
    max_retries: int,
    retriable_codes: list[str],
    *,
    confidence: float,
    expected_recovery: float,
    evidence_path: list[str],
) -> Action:
    """Bounded retry for retriable failure codes only. Bound: 1 <= max_retries <= 3."""
    if not (1 <= max_retries <= 3):
        raise ValueError("max_retries out of bounds (1..3)")
    if not retriable_codes:
        raise ValueError("retry_fallback requires at least one retriable code")
    params = {
        "method": method.value,
        "max_retries": max_retries,
        "retriable_codes": sorted(retriable_codes),
    }
    return Action(
        kind="retry_fallback",
        params=params,
        decision_id=_decision_id("retry_fallback", params),
        evidence_path=list(evidence_path),
        confidence=confidence,
        expected_recovery=expected_recovery,
    )


def do_nothing(reason: str, confidence: float) -> Action:
    params = {"reason": reason}
    return Action(
        kind="do_nothing",
        params=params,
        decision_id=_decision_id("do_nothing", params),
        evidence_path=[reason],
        confidence=confidence,
        expected_recovery=0.0,
    )
