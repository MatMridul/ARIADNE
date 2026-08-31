"""Static payment topology (BUILD_SPEC §3.2).

The graph is a plain dict-backed structure (stdlib only). It holds the *static*
topology (what routes to what); it does NOT hold health — health is derived
downstream by diagnosis from observed per-PSP stats.
"""

from copy import deepcopy
from dataclasses import dataclass

from .entities import Bank, Method, PSP


@dataclass
class PaymentGraph:
    psps: dict[str, PSP]
    banks: dict[str, Bank]
    # method -> list of (psp_id, routing_weight); mutable (reroute changes it)
    routing: dict[Method, list[tuple[str, float]]]
    # psp_id -> bank_id it settles via
    settles_via: dict[str, str]

    def banks_for_method(self, m: Method) -> set[str]:
        """Banks reachable by a method, via the PSPs that carry it."""
        result: set[str] = set()
        for psp_id, _weight in self.routing.get(m, []):
            bank_id = self.settles_via.get(psp_id)
            if bank_id is not None:
                result.add(bank_id)
        return result

    def psps_for_bank(self, bank_id: str) -> list[str]:
        """The shared-dependency lookup: which PSPs settle via this bank."""
        return [
            psp_id
            for psp_id, settle_bank in self.settles_via.items()
            if settle_bank == bank_id
        ]

    def shared_banks(self) -> dict[str, list[str]]:
        """bank_id -> PSPs, for banks used by >1 PSP. The load-bearing edge."""
        result: dict[str, list[str]] = {}
        for bank_id in self.banks:
            psps = self.psps_for_bank(bank_id)
            if len(psps) > 1:
                result[bank_id] = psps
        return result

    def reroute(self, m: Method, from_psp: str, to_psp: str) -> "PaymentGraph":
        """Return a NEW graph with routing weight moved. Immutable-style for rollback."""
        new_graph = deepcopy(self)
        entries = new_graph.routing.get(m, [])
        moved_weight = 0.0
        remaining: list[tuple[str, float]] = []
        for psp_id, weight in entries:
            if psp_id == from_psp:
                moved_weight += weight
            else:
                remaining.append((psp_id, weight))
        if moved_weight:
            for idx, (psp_id, weight) in enumerate(remaining):
                if psp_id == to_psp:
                    remaining[idx] = (psp_id, weight + moved_weight)
                    break
            else:
                remaining.append((to_psp, moved_weight))
        new_graph.routing[m] = remaining
        return new_graph


def default_graph() -> PaymentGraph:
    """3 methods, 3 PSPs, 2 banks — bank_A shared by PSP-1 & PSP-2 (the shared
    dependency), bank_B used only by PSP-3.  [DECISION → DR-001: graph size]"""
    psps = {
        "psp_1": PSP("psp_1", "PSP One"),
        "psp_2": PSP("psp_2", "PSP Two"),
        "psp_3": PSP("psp_3", "PSP Three"),
    }
    banks = {
        "bank_A": Bank("bank_A", "Bank A", "acquirer"),
        "bank_B": Bank("bank_B", "Bank B", "acquirer"),
    }
    # bank_A shared by psp_1 & psp_2; bank_B used only by psp_3.
    settles_via = {
        "psp_1": "bank_A",
        "psp_2": "bank_A",
        "psp_3": "bank_B",
    }
    # Methods spread across PSPs so each method touches the shared bank and bank_B.
    routing = {
        Method.UPI: [("psp_1", 0.5), ("psp_3", 0.5)],
        Method.CARD: [("psp_2", 0.6), ("psp_3", 0.4)],
        Method.NETBANKING: [("psp_1", 0.5), ("psp_2", 0.5)],
    }
    return PaymentGraph(
        psps=psps,
        banks=banks,
        routing=routing,
        settles_via=settles_via,
    )
