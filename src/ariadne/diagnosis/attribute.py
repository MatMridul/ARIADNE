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
# A method fault CONCENTRATES in one method (others near baseline); a PSP/bank fault
# spreads evenly across all methods. The worst method must dominate the 2nd-worst by
# this margin for a method explanation to be preferred over independent PSPs (DR-002).
_METHOD_CONCENTRATION_MIN = 0.06


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
        # no PSP breached -> a pure method-level fault can still be present, since a
        # single method's drop dilutes across each PSP's mixed traffic. Inspect the
        # method view directly (still no ground truth).
        method_cause = _method_fault(stats)
        if method_cause is not None:
            m_id, m_delta = method_cause
            return Attribution(
                root_cause_id=m_id,
                root_cause_kind="method",
                confidence=min(1.0, abs(m_delta) / 0.3),
                evidence_path=[
                    f"method {m_id} delta={m_delta:.3f} concentrated in one method;"
                    " no single PSP breached",
                    "attributing to the method, not a PSP or bank",
                ],
            )
        return Attribution(
            root_cause_id="",
            root_cause_kind="none",
            confidence=0.0,
            evidence_path=["no PSP or method breached the detection threshold"],
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

    # --- concentrated method-level explanation (DR-002) -------------------
    # A method cause is preferred over independent PSPs ONLY when the failure is
    # CONCENTRATED in a single method (one method dominates the next-worst by
    # _METHOD_CONCENTRATION_MIN). Independent PSP faults (incident E) degrade all
    # methods roughly equally, so _method_fault returns None for them and this
    # branch does NOT fire -- they fall through to the independent-PSP branch below.
    method_cause = _method_fault(stats)
    if method_cause is not None and len(down) > 1:
        m_id, m_delta = method_cause
        conf = min(1.0, abs(m_delta) / 0.3)
        return Attribution(
            root_cause_id=m_id,
            root_cause_kind="method",
            confidence=conf,
            evidence_path=[
                f"method {m_id} delta={m_delta:.3f} concentrated in one method",
                "failure dominated by one method, not localised to a bank or PSP set",
            ],
        )

    # --- independent PSP faults (incident E / single-PSP B) ---------------
    # down PSPs do not all share one bank AND no concentrated method explains them
    # -> blame each on itself.
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


def _method_fault(stats: dict[str, NodeStats]) -> tuple[str, float] | None:
    """Return (method_id, delta) ONLY when a single method is genuinely the cause:
    it is clearly down AND its drop DOMINATES the next-worst method by
    _METHOD_CONCENTRATION_MIN (DR-002). A PSP/bank fault degrades all methods roughly
    equally (low concentration) and must NOT be read as a method fault."""
    methods = sorted(
        (s for s in stats.values() if s.node_kind == "method"),
        key=lambda s: s.delta,
    )
    if not methods:
        return None
    worst = methods[0]
    if worst.delta > -_METHOD_DELTA_MIN:
        return None  # no method clearly down
    second_delta = methods[1].delta if len(methods) > 1 else 0.0
    concentration = second_delta - worst.delta  # >= 0; large => worst dominates
    if concentration < _METHOD_CONCENTRATION_MIN:
        return None  # failure is spread across methods -> not a method fault
    return worst.node_id, worst.delta
