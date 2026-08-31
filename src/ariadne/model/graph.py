"""The static payment dependency graph (adapter.md §2, BUILD_SPEC §3.2).

Holds ONLY the static topology (what routes to what, what settles where). It does
NOT hold node health -- health is derived from observed transactions in diagnosis/.
Stdlib only; dict-backed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ariadne.model.entities import Bank, Method, PSP


@dataclass
class PaymentGraph:
    psps: dict[str, PSP]
    banks: dict[str, Bank]
    # method -> list of (psp_id, routing_weight); mutable (reroute changes it)
    routing: dict[Method, list[tuple[str, float]]]
    # psp_id -> bank_id it settles via
    settles_via: dict[str, str]

    def banks_for_method(self, m: Method) -> set[str]:
        """Every bank reachable by a method, via the PSPs the method routes to."""
        return {
            self.settles_via[psp_id]
            for psp_id, _weight in self.routing.get(m, [])
            if psp_id in self.settles_via
        }

    def psps_for_bank(self, bank_id: str) -> list[str]:
        """The shared-dependency lookup: which PSPs settle via this bank.
        Sorted for determinism."""
        return sorted(
            psp_id for psp_id, b in self.settles_via.items() if b == bank_id
        )

    def shared_banks(self) -> dict[str, list[str]]:
        """bank_id -> PSPs, for banks used by >1 PSP. The load-bearing edge:
        this is what the non-relational baseline cannot see."""
        result: dict[str, list[str]] = {}
        for bank_id in self.banks:
            psps = self.psps_for_bank(bank_id)
            if len(psps) > 1:
                result[bank_id] = psps
        return result

    def psps_for_method(self, m: Method) -> list[str]:
        """PSPs a method currently routes to (any positive weight), sorted."""
        return sorted(
            psp_id for psp_id, w in self.routing.get(m, []) if w > 0.0
        )

    def reroute(self, m: Method, from_psp: str, to_psp: str) -> "PaymentGraph":
        """Return a NEW graph with method m's weight moved from one PSP to another.
        Immutable-style so the caller can hold the prior graph for rollback."""
        new_routing: dict[Method, list[tuple[str, float]]] = {
            method: list(pairs) for method, pairs in self.routing.items()
        }
        pairs = new_routing.get(m, [])
        weights = {psp_id: w for psp_id, w in pairs}
        if from_psp not in weights:
            raise ValueError(f"{from_psp} does not carry method {m.value}")
        moved = weights.pop(from_psp)
        weights[from_psp] = 0.0
        weights[to_psp] = weights.get(to_psp, 0.0) + moved
        new_routing[m] = sorted(weights.items())
        return PaymentGraph(
            psps=dict(self.psps),
            banks=dict(self.banks),
            routing=new_routing,
            settles_via=dict(self.settles_via),
        )


def default_graph() -> PaymentGraph:
    """3 methods, 3 PSPs, 2 banks (DR-001 A1).

    bank_A is SHARED by PSP-1 & PSP-2 (the shared dependency under test);
    bank_B is used only by PSP-3 (the negative-control path).
    Routing: each method is carried by all three PSPs with equal weight so a
    shared-bank fault surfaces across PSP-1 and PSP-2 for every method, while
    PSP-3 (on bank_B) stays healthy as the control.
    """
    psps = {
        "psp_1": PSP("psp_1", "PSP-1"),
        "psp_2": PSP("psp_2", "PSP-2"),
        "psp_3": PSP("psp_3", "PSP-3"),
    }
    banks = {
        "bank_A": Bank("bank_A", "Bank-A", "acquirer"),
        "bank_B": Bank("bank_B", "Bank-B", "acquirer"),
    }
    settles_via = {
        "psp_1": "bank_A",
        "psp_2": "bank_A",  # shared with psp_1
        "psp_3": "bank_B",
    }
    routing: dict[Method, list[tuple[str, float]]] = {
        m: [("psp_1", 1.0), ("psp_2", 1.0), ("psp_3", 1.0)] for m in Method
    }
    return PaymentGraph(
        psps=psps, banks=banks, routing=routing, settles_via=settles_via
    )
