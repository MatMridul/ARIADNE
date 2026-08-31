"""ARIADNE's core relational attribution (BUILD_SPEC §3.8, DR-001 B1).

Given per-PSP / per-method NodeStats and the dependency graph, decide whether ONE
shared upstream node (a bank) best explains the observed failure pattern, or
whether the down PSPs are independent faults, or a method fault, or nothing.

Pinned scoring (DR-001, do not replace with a fancier model):
  down set D = PSPs breaching the detect threshold.
  For bank X with PSP-set P(X):
    coverage(X)    = |D ∩ P(X)| / |P(X)|
    specificity(X) = 1 - |D - P(X)| / |D|
  Blame the BANK when a bank has coverage == 1.0, |P(X)| > 1, and
  specificity >= S_MIN; confidence = coverage(X) * specificity(X).
  Else if down PSPs sit on different banks (no bank hits coverage 1.0 with >1 PSP)
  -> blame each down PSP INDEPENDENTLY (incident E / B).
  Else if a single method is down across PSPs -> blame the METHOD.
  Else -> 'none', confidence 0 (drives do_nothing).

Imports NOTHING from simulator/ -- the diagnoser never sees ground truth. Bank
health is DERIVED here from PSP stats via the graph; it is not an observed input.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ariadne.diagnosis.detect import Detection
from ariadne.model.graph import PaymentGraph
from ariadne.observe.aggregate import NodeStats

S_MIN = 0.8  # pinned (DR-001); specificity floor to blame a shared bank
_METHOD_DELTA_MIN = 0.05  # a method must be clearly down to be blamed


@dataclass
class Attribution:
    root_cause_id: str
    root_cause_kind: str  # "bank" | "psp" | "method" | "none"
    confidence: float
    evidence_path: list[str] = field(default_factory=list)
    claim_type: str = "hypothesis"
    # for independent-PSP verdicts (E/B): the full set of independently-blamed PSPs
    psp_causes: list[str] = field(default_factory=list)


def _psp_delta(stats: dict[str, NodeStats], psp_id: str) -> float:
    for s in stats.values():
        if s.node_kind == "psp" and s.node_id == psp_id:
            return s.delta
    return 0.0


def _bank_score(
    graph: PaymentGraph, bank_id: str, down: set[str]
) -> tuple[float, float]:
    members = set(graph.psps_for_bank(bank_id))
    if not members or not down:
        return 0.0, 0.0
    coverage = len(down & members) / len(members)
    specificity = 1.0 - len(down - members) / len(down)
    return coverage, specificity


def attribute(
    stats: dict[str, NodeStats], graph: PaymentGraph, detection: Detection
) -> Attribution:
    down = set(detection.dropped_nodes)
    if not down:
        return Attribution(
            root_cause_id="",
            root_cause_kind="none",
            confidence=0.0,
            evidence_path=["no PSP breached the detection threshold"],
        )

    # --- candidate shared-bank explanation --------------------------------
    best_bank: str | None = None
    best_conf = 0.0
    best_cov = 0.0
    best_spec = 0.0
    for bank_id in graph.banks:
        members = graph.psps_for_bank(bank_id)
        if len(members) <= 1:
            continue  # not a shared dependency -> cannot be a shared cause
        cov, spec = _bank_score(graph, bank_id, down)
        if cov == 1.0 and spec >= S_MIN:
            conf = cov * spec
            if conf > best_conf:
                best_bank, best_conf, best_cov, best_spec = bank_id, conf, cov, spec

    if best_bank is not None:
        members = graph.psps_for_bank(best_bank)
        return Attribution(
            root_cause_id=best_bank,
            root_cause_kind="bank",
            confidence=best_conf,
            evidence_path=[
                f"bank {best_bank} settles {members}",
                f"coverage={best_cov:.2f} (all its PSPs down)",
                f"specificity={best_spec:.2f} (down PSPs are its own)",
                f"confidence=coverage*specificity={best_conf:.2f}",
            ],
            psp_causes=sorted(down),
        )

    # --- method-level explanation: a method down across PSPs --------------
    method_cause = _method_cause(stats)
    if method_cause is not None:
        m_id, m_delta = method_cause
        # only prefer a method explanation when PSP-level signal doesn't cleanly
        # localise to one PSP (i.e. multiple PSPs down but no shared bank)
        if len(down) > 1:
            conf = min(1.0, abs(m_delta) / 0.3)
            return Attribution(
                root_cause_id=m_id,
                root_cause_kind="method",
                confidence=conf,
                evidence_path=[
                    f"method {m_id} delta={m_delta:.3f} across PSPs",
                    "no single bank covers all down PSPs",
                ],
            )

    # --- independent PSP faults (incident E / single-PSP B) ---------------
    # down PSPs do not all share one bank -> blame each on itself.
    deltas = [abs(_psp_delta(stats, p)) for p in down]
    conf = min(1.0, (sum(deltas) / len(deltas)) / 0.3) if deltas else 0.0
    return Attribution(
        root_cause_id=sorted(down)[0],
        root_cause_kind="psp",
        confidence=conf,
        evidence_path=[
            f"down PSPs {sorted(down)} do not all settle via one shared bank",
            "blaming each PSP independently (no shared-cause support)",
        ],
        psp_causes=sorted(down),
    )


def _method_cause(stats: dict[str, NodeStats]) -> tuple[str, float] | None:
    worst: tuple[str, float] | None = None
    for s in stats.values():
        if s.node_kind == "method" and s.delta <= -_METHOD_DELTA_MIN:
            if worst is None or s.delta < worst[1]:
                worst = (s.node_id, s.delta)
    return worst
