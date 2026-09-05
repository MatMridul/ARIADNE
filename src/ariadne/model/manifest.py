"""Topology ingestion boundary — manifest -> PaymentGraph.

The minimum credible entry point for getting a merchant's payment infrastructure
into ARIA. It VALIDATES a JSON topology manifest and NORMALIZES it into the
EXISTING domain representation (`PaymentGraph` + `PSP`/`Bank`/`Method`). It does
NOT duplicate the graph model, does NOT persist anything, and adds NO reasoning.

Manifest shape (all ids are strings):
    {
      "merchant": {"id": "...", "name": "..."},
      "methods":  [{"id": "upi", "name": "UPI"}, ...],   # id must be a known Method
      "psps":     [{"id": "psp_1", "name": "PSP-1"}, ...],
      "banks":    [{"id": "bank_A", "name": "Bank-A", "role": "acquirer"}, ...],
      "routes":   [{"method": "upi", "psp": "psp_1", "bank": "bank_A", "weight": 1.0}, ...]
    }

A route asserts: method -> psp (with weight) AND psp settles_via bank. `weight`
is optional (defaults 1.0). The converter derives `routing` and `settles_via`
exactly as `default_graph()` builds them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ariadne.model.entities import Bank, Method, PSP
from ariadne.model.graph import PaymentGraph

_VALID_METHODS = {m.value for m in Method}
_VALID_ROLES = {"acquirer", "issuer"}


class TopologyValidationError(ValueError):
    """Raised when a manifest is structurally invalid. Message lists every issue."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class NormalizedTopology:
    """The result of a successful import: the real PaymentGraph plus a small
    summary the API/UI can surface. Held in memory / request-scoped — NOT persisted."""

    graph: PaymentGraph
    merchant_id: str
    merchant_name: str
    method_ids: list[str] = field(default_factory=list)
    psp_ids: list[str] = field(default_factory=list)
    bank_ids: list[str] = field(default_factory=list)
    route_count: int = 0
    shared_banks: dict[str, list[str]] = field(default_factory=dict)


def _as_list(m: dict, key: str) -> list:
    v = m.get(key, [])
    return v if isinstance(v, list) else []


def validate_manifest(manifest: dict) -> list[str]:
    """Return a list of human-readable validation errors (empty => valid).
    Checks: presence, unique ids, valid method ids, valid bank roles, non-empty
    core sets, and that every route references existing nodes."""
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    merchant = manifest.get("merchant")
    if not isinstance(merchant, dict) or not merchant.get("id"):
        errors.append("merchant.id is required")

    methods = _as_list(manifest, "methods")
    psps = _as_list(manifest, "psps")
    banks = _as_list(manifest, "banks")
    routes = _as_list(manifest, "routes")

    if not methods:
        errors.append("at least one payment method is required")
    if not psps:
        errors.append("at least one PSP is required")
    if not banks:
        errors.append("at least one bank is required")
    if not routes:
        errors.append("at least one route is required")

    # unique ids within each collection
    method_ids: list[str] = []
    for i, mth in enumerate(methods):
        mid = (mth or {}).get("id") if isinstance(mth, dict) else None
        if not mid:
            errors.append(f"methods[{i}].id is required")
            continue
        if mid in method_ids:
            errors.append(f"duplicate method id '{mid}'")
        method_ids.append(mid)
        if mid not in _VALID_METHODS:
            errors.append(
                f"method id '{mid}' is not a supported method "
                f"(one of {sorted(_VALID_METHODS)})"
            )

    psp_ids: list[str] = []
    for i, p in enumerate(psps):
        pid = (p or {}).get("id") if isinstance(p, dict) else None
        if not pid:
            errors.append(f"psps[{i}].id is required")
            continue
        if pid in psp_ids:
            errors.append(f"duplicate PSP id '{pid}'")
        psp_ids.append(pid)

    bank_ids: list[str] = []
    for i, b in enumerate(banks):
        bid = (b or {}).get("id") if isinstance(b, dict) else None
        if not bid:
            errors.append(f"banks[{i}].id is required")
            continue
        if bid in bank_ids:
            errors.append(f"duplicate bank id '{bid}'")
        bank_ids.append(bid)
        role = (b or {}).get("role", "acquirer")
        if role not in _VALID_ROLES:
            errors.append(f"bank '{bid}' has invalid role '{role}' (acquirer|issuer)")

    # cross-id ns collision (a PSP and bank sharing an id would be ambiguous)
    dupe_ns = set(psp_ids) & set(bank_ids)
    for d in sorted(dupe_ns):
        errors.append(f"id '{d}' used for both a PSP and a bank")

    # routes reference existing nodes; a PSP must settle via exactly one bank
    psp_bank: dict[str, str] = {}
    for i, r in enumerate(routes):
        if not isinstance(r, dict):
            errors.append(f"routes[{i}] must be an object")
            continue
        rm, rp, rb = r.get("method"), r.get("psp"), r.get("bank")
        if rm not in method_ids:
            errors.append(f"routes[{i}] references unknown method '{rm}'")
        if rp not in psp_ids:
            errors.append(f"routes[{i}] references unknown PSP '{rp}'")
        if rb not in bank_ids:
            errors.append(f"routes[{i}] references unknown bank '{rb}'")
        w = r.get("weight", 1.0)
        if not isinstance(w, (int, float)) or w < 0:
            errors.append(f"routes[{i}].weight must be a non-negative number")
        # a PSP must settle via a single, consistent bank across its routes
        if rp in psp_ids and rb in bank_ids:
            if rp in psp_bank and psp_bank[rp] != rb:
                errors.append(
                    f"PSP '{rp}' settles via conflicting banks "
                    f"('{psp_bank[rp]}' and '{rb}') across routes"
                )
            psp_bank.setdefault(rp, rb)

    # every PSP that appears must resolve to a bank
    for pid in psp_ids:
        if pid not in psp_bank and not errors:
            errors.append(f"PSP '{pid}' has no route assigning it a bank")

    return errors


def manifest_to_graph(manifest: dict) -> NormalizedTopology:
    """Validate + convert a manifest into the existing PaymentGraph. Raises
    TopologyValidationError with all issues if invalid. No persistence."""
    errors = validate_manifest(manifest)
    if errors:
        raise TopologyValidationError(errors)

    merchant = manifest["merchant"]
    methods = _as_list(manifest, "methods")
    psps = _as_list(manifest, "psps")
    banks = _as_list(manifest, "banks")
    routes = _as_list(manifest, "routes")

    psp_objs = {p["id"]: PSP(p["id"], p.get("name", p["id"])) for p in psps}
    bank_objs = {
        b["id"]: Bank(b["id"], b.get("name", b["id"]), b.get("role", "acquirer"))
        for b in banks
    }

    # settles_via: psp -> bank (validation guaranteed consistency)
    settles_via: dict[str, str] = {}
    # routing: Method -> [(psp_id, weight)] accumulated across routes
    routing_acc: dict[Method, dict[str, float]] = {}

    for r in routes:
        method = Method(r["method"])
        psp_id = r["psp"]
        bank_id = r["bank"]
        weight = float(r.get("weight", 1.0))
        settles_via[psp_id] = bank_id
        routing_acc.setdefault(method, {})
        routing_acc[method][psp_id] = routing_acc[method].get(psp_id, 0.0) + weight

    routing: dict[Method, list[tuple[str, float]]] = {
        m: sorted(w.items()) for m, w in routing_acc.items()
    }

    graph = PaymentGraph(
        psps=psp_objs,
        banks=bank_objs,
        routing=routing,
        settles_via=settles_via,
    )

    return NormalizedTopology(
        graph=graph,
        merchant_id=merchant["id"],
        merchant_name=merchant.get("name", merchant["id"]),
        method_ids=[m["id"] for m in methods],
        psp_ids=sorted(psp_objs),
        bank_ids=sorted(bank_objs),
        route_count=len(routes),
        shared_banks=graph.shared_banks(),
    )
