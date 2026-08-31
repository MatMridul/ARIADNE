"""The fair non-relational baseline (BUILD_SPEC §3.9, DR-001 C1).

``baseline_attribute`` is the strongest *reasonable* non-relational monitor. It
sees the SAME per-PSP and per-method ``NodeStats`` (success rate, rolling
baseline, latency, volume) that ARIADNE sees, and it applies the SAME detection
threshold competently. What it does NOT have is the dependency graph: it cannot
know that two PSPs settle via the same bank.

Because it has no notion of a shared upstream dependency, it blames each
independently-dropped node on ITSELF. On a shared-bank incident (both PSPs on
bank_A drop together) it therefore reports several INDEPENDENT PSP faults — never
a bank — which is exactly the discrimination gap the thesis tests. On a
coincidental incident (two PSPs on different banks, independent faults) that same
per-node reasoning is CORRECT, so the A-vs-E contrast isolates ARIADNE's real
advantage rather than punishing a strawman.

SEAL: this module MUST NOT import from or reference the simulator's ground-truth
module or its injected-truth types (BUILD_SPEC §1 rule 3). It reasons purely from
the observed per-node stats — it never sees injected truth.
"""

from ..diagnosis.attribute import Attribution
from ..observe.aggregate import NodeStats


def _dropped_nodes(
    stats: dict[str, NodeStats], detect_threshold: float
) -> list[str]:
    """Nodes whose success rate fell below baseline by more than the threshold.

    Uses the SAME deterministic rule as ``diagnosis.detect`` (``delta <=
    -detect_threshold``) so the baseline is a fair, competent monitor and not a
    strawman. PSPs are considered first because they are the actionable unit; a
    method is only surfaced when no PSP breached (a genuinely method-shaped fault).
    """
    return sorted(
        node_id
        for node_id, s in stats.items()
        if s.node_kind == "psp" and s.delta <= -detect_threshold
    )


def _dropped_methods(
    stats: dict[str, NodeStats], detect_threshold: float
) -> list[str]:
    return sorted(
        node_id
        for node_id, s in stats.items()
        if s.node_kind == "method" and s.delta <= -detect_threshold
    )


def _norm_delta(stats: dict[str, NodeStats], node_ids: list[str]) -> float:
    """Mean per-node delta magnitude normalized to 0..1 (delta is in [-1, 1])."""
    if not node_ids:
        return 0.0
    mags = [min(1.0, abs(stats[n].delta)) for n in node_ids if n in stats]
    return sum(mags) / len(mags) if mags else 0.0


def baseline_attribute(
    stats: dict[str, NodeStats], detect_threshold: float
) -> Attribution:
    """Blame each independently-dropped node on ITSELF (no graph reasoning).

    Returns an ``Attribution`` whose primary is the first dropped PSP and whose
    ``secondary_causes`` carry any additional independently-dropped PSPs. With no
    graph it can never conclude a shared-bank cause. When nothing PSP-level dropped
    it falls back to a dropped method, then to ``none``.
    """
    dropped = _dropped_nodes(stats, detect_threshold)

    if not dropped:
        methods = _dropped_methods(stats, detect_threshold)
        if methods:
            confidence = _norm_delta(stats, methods)
            return Attribution(
                root_cause_id=methods[0],
                root_cause_kind="method",
                confidence=confidence,
                evidence_path=[
                    f"method(s) {methods} breached the detection threshold",
                    f"no per-PSP breach; mean|delta|={confidence:.2f}",
                    "non-relational monitor: no shared-dependency reasoning",
                ],
                secondary_causes=methods[1:],
            )
        return Attribution(
            root_cause_id="",
            root_cause_kind="none",
            confidence=0.0,
            evidence_path=["no node breached the detection threshold"],
        )

    confidence = _norm_delta(stats, dropped)
    return Attribution(
        root_cause_id=dropped[0],
        root_cause_kind="psp",
        confidence=confidence,
        evidence_path=[
            f"PSPs {dropped} each breached the detection threshold",
            "no dependency graph: each dropped PSP is blamed independently",
            f"mean|delta|={confidence:.2f}",
        ],
        secondary_causes=dropped[1:],
    )
