"""The core relational reasoning (BUILD_SPEC §3.8, DR-001 B1).

For each candidate upstream node — including DERIVED bank health computed from the
PSPs that settle via it — score how well "this ONE shared node is unhealthy"
explains the observed failure pattern versus "these PSPs are independently
unhealthy". The pinned coverage×specificity formula is what separates incident A
(one shared bank) from incident E (two coincidental faults on different banks).

This is the ONLY module that uses the graph for attribution, and bank-level health
is DERIVED here from the same per-PSP ``NodeStats`` the baseline also sees — it is
never an extra observation.

SEAL: this module MUST NOT import from or reference the simulator's ground-truth
module or its injected-truth types. The diagnoser never sees injected truth
(BUILD_SPEC §1 rule 3). If a test seems to need injected truth here, the test is
wrong.
"""

from dataclasses import dataclass, field

from ..model.graph import PaymentGraph
from ..observe.aggregate import NodeStats
from .detect import Detection

# Named constant (DR-001): a bank is only blamed when the down PSPs are specific to
# it — down PSPs must not spill onto other banks beyond this tolerance.
S_MIN = 0.8


@dataclass
class Attribution:
    root_cause_id: str  # the node ARIADNE blames (may be a bank)
    root_cause_kind: str  # "bank" | "psp" | "method" | "none"
    confidence: float  # 0..1
    evidence_path: list[str]  # the observations/edges supporting it
    claim_type: str = "hypothesis"
    # for the coincidental/multi-PSP case, all independently-blamed PSPs
    secondary_causes: list[str] = field(default_factory=list)


def _down_psps(stats: dict[str, NodeStats], detection: Detection) -> list[str]:
    """The down set D: dropped nodes that are PSPs (methods are handled separately)."""
    return sorted(
        n
        for n in detection.dropped_nodes
        if n in stats and stats[n].node_kind == "psp"
    )


def _down_methods(stats: dict[str, NodeStats], detection: Detection) -> list[str]:
    return sorted(
        n
        for n in detection.dropped_nodes
        if n in stats and stats[n].node_kind == "method"
    )


def _bank_scores(
    graph: PaymentGraph, down: list[str]
) -> list[tuple[str, float, float]]:
    """(bank_id, coverage, specificity) for every bank, derived from the down set D.

    coverage(X)    = |D ∩ P(X)| / |P(X)|
    specificity(X) = 1 − (|D − P(X)| / |D|)
    """
    d_set = set(down)
    scored: list[tuple[str, float, float]] = []
    for bank_id in graph.banks:
        p_x = set(graph.psps_for_bank(bank_id))
        if not p_x:
            continue
        coverage = len(d_set & p_x) / len(p_x)
        specificity = 1.0 - (len(d_set - p_x) / len(d_set)) if d_set else 0.0
        scored.append((bank_id, coverage, specificity))
    return scored


def _norm_delta(stats: dict[str, NodeStats], node_ids: list[str]) -> float:
    """Mean per-node delta magnitude normalized to 0..1 (delta is in [-1, 1])."""
    if not node_ids:
        return 0.0
    mags = [min(1.0, abs(stats[n].delta)) for n in node_ids if n in stats]
    return sum(mags) / len(mags) if mags else 0.0


def attribute(
    stats: dict[str, NodeStats], graph: PaymentGraph, detection: Detection
) -> Attribution:
    """Implements the pinned DR-001 decision rule EXACTLY (BUILD_SPEC §3.8)."""
    down = _down_psps(stats, detection)

    # (4) nothing PSP-level breaches — but a method might be the whole story.
    if not down:
        methods = _down_methods(stats, detection)
        if methods:
            return _blame_method(stats, methods)
        return Attribution(
            root_cause_id="",
            root_cause_kind="none",
            confidence=0.0,
            evidence_path=["no node breached detect threshold"],
        )

    scored = _bank_scores(graph, down)

    # (1) best bank fully covered AND specific → blame the BANK.
    #
    # ACCEPTED CONSEQUENCE OF THE PINNED RULE (DR-001 B1): the bank test runs
    # BEFORE the method test by design. A method whose carriers ALL settle via one
    # bank (e.g. NETBANKING is routed only through psp_1+psp_2, both on bank_A)
    # drops exactly that bank's PSP set, giving coverage=1.0/specificity=1.0, so it
    # is read as a bank fault rather than a method fault. This is faithful to the
    # frozen formula — it is NOT a bug to be reordered here; disambiguating a
    # single-bank method from a bank would be a DESIGN change requiring a new
    # Decision Record. The evaluation stays honest because scenario C uses `upi`,
    # a CROSS-bank method (psp_1 on bank_A + psp_3 on bank_B) whose down set no
    # single bank fully covers, so it correctly resolves to METHOD below. See the
    # FEAT-005 review-hardening note and test_attribute for the pinned behaviour.
    full = [s for s in scored if s[1] == 1.0 and len(graph.psps_for_bank(s[0])) > 1]
    full.sort(key=lambda s: s[2], reverse=True)
    if full:
        bank_id, coverage, specificity = full[0]
        if specificity >= S_MIN:
            return Attribution(
                root_cause_id=bank_id,
                root_cause_kind="bank",
                confidence=coverage * specificity,
                evidence_path=[
                    f"down PSPs {down} all settle via {bank_id}",
                    f"coverage={coverage:.2f} specificity={specificity:.2f}",
                    f"shared dependency {bank_id} explains the correlated failures",
                ],
            )

    # (3) a single method is down across PSPs → blame the METHOD.
    #     (only when the down PSPs don't form a clean bank story above)
    methods = _down_methods(stats, detection)
    if len(methods) == 1 and len(down) > 1:
        return _blame_method(stats, methods)

    # (2) down PSPs sit on DIFFERENT banks (no bank reached coverage 1.0 with
    #     >1 PSP) → blame each down PSP INDEPENDENTLY (incident E / B).
    confidence = _norm_delta(stats, down)
    return Attribution(
        root_cause_id=down[0],
        root_cause_kind="psp",
        confidence=confidence,
        evidence_path=[
            f"down PSPs {down} do not share one fully-covered bank",
            f"blaming each PSP independently; mean|delta|={confidence:.2f}",
        ],
        secondary_causes=down[1:],
    )


def _blame_method(stats: dict[str, NodeStats], methods: list[str]) -> Attribution:
    confidence = _norm_delta(stats, methods)
    return Attribution(
        root_cause_id=methods[0],
        root_cause_kind="method",
        confidence=confidence,
        evidence_path=[
            f"method(s) {methods} down across PSPs",
            f"mean|delta|={confidence:.2f}",
        ],
        secondary_causes=methods[1:],
    )
