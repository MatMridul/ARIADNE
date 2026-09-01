"""The fair non-relational baseline (BUILD_SPEC §3.9, DR-001 C1).

The STRONGEST reasonable independent monitor -- NOT a strawman. It sees the SAME
per-PSP and per-method NodeStats ARIADNE sees (rates, baselines, latency, volume)
and uses baselines and thresholds competently. It has NO dependency graph: it
cannot know two PSPs share a bank, so it blames each independently-dropped node on
ITSELF.

Consequence (the discrimination gap): on a shared-bank incident it reports several
independent PSP faults rather than one bank. On a coincidental incident (E) it is
CORRECT (independent PSPs). The A-vs-E contrast is what isolates ARIADNE's real
advantage.

Imports NOTHING from simulator/ -- never sees ground truth. Imports NO graph.
"""
from __future__ import annotations

from ariadne.diagnosis.attribute import Attribution
from ariadne.observe.aggregate import NodeStats


def baseline_attribute(
    stats: dict[str, NodeStats], detect_threshold: float
) -> Attribution:
    down = sorted(
        s.node_id
        for s in stats.values()
        if s.node_kind == "psp" and s.delta <= -detect_threshold
    )
    if not down:
        # competent method check before giving up (still non-relational)
        method_down = _worst_method(stats, detect_threshold)
        if method_down is not None:
            m_id, m_delta = method_down
            return Attribution(
                root_cause_id=m_id,
                root_cause_kind="method",
                confidence=min(1.0, abs(m_delta) / 0.3),
                evidence_path=[f"method {m_id} delta={m_delta:.3f} (independent monitor)"],
            )
        return Attribution(
            root_cause_id="",
            root_cause_kind="none",
            confidence=0.0,
            evidence_path=["no PSP or method breached threshold"],
        )

    # blame each down PSP on itself -- confidence from mean delta magnitude
    by_id = {s.node_id: s for s in stats.values() if s.node_kind == "psp"}
    deltas = [abs(by_id[p].delta) for p in down if p in by_id]
    conf = min(1.0, (sum(deltas) / len(deltas)) / 0.3) if deltas else 0.0
    return Attribution(
        root_cause_id=down[0],
        root_cause_kind="psp",
        confidence=conf,
        evidence_path=[
            f"independent monitor: PSPs {down} each dropped vs their own baseline",
            "no graph -> cannot attribute to a shared upstream node",
        ],
        psp_causes=down,
    )


def _worst_method(
    stats: dict[str, NodeStats], detect_threshold: float
) -> tuple[str, float] | None:
    worst: tuple[str, float] | None = None
    for s in stats.values():
        if s.node_kind == "method" and s.delta <= -detect_threshold:
            if worst is None or s.delta < worst[1]:
                worst = (s.node_id, s.delta)
    return worst
