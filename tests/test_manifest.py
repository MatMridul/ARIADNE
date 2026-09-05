"""Tests for the topology ingestion boundary (manifest -> PaymentGraph).

Covers: a valid manifest, invalid references, duplicate ids, malformed routes,
shared-bank detection, and normalization into the existing PaymentGraph. No
diagnosis/eval/simulator logic is touched.
"""
import pytest

from ariadne.model.entities import Method
from ariadne.model.graph import PaymentGraph
from ariadne.model.manifest import (
    TopologyValidationError,
    manifest_to_graph,
    validate_manifest,
)


def _valid_manifest() -> dict:
    """The canonical 3/3/2 shared-bank topology as a manifest."""
    return {
        "merchant": {"id": "mx_1", "name": "Acme Commerce"},
        "methods": [
            {"id": "upi", "name": "UPI"},
            {"id": "card", "name": "Card"},
            {"id": "netbanking", "name": "Netbanking"},
        ],
        "psps": [
            {"id": "psp_1", "name": "PSP-1"},
            {"id": "psp_2", "name": "PSP-2"},
            {"id": "psp_3", "name": "PSP-3"},
        ],
        "banks": [
            {"id": "bank_A", "name": "Bank-A", "role": "acquirer"},
            {"id": "bank_B", "name": "Bank-B", "role": "acquirer"},
        ],
        "routes": [
            {"method": "upi", "psp": "psp_1", "bank": "bank_A"},
            {"method": "upi", "psp": "psp_2", "bank": "bank_A"},
            {"method": "upi", "psp": "psp_3", "bank": "bank_B"},
            {"method": "card", "psp": "psp_1", "bank": "bank_A"},
            {"method": "card", "psp": "psp_2", "bank": "bank_A"},
            {"method": "card", "psp": "psp_3", "bank": "bank_B"},
        ],
    }


def test_valid_manifest_normalizes_to_graph():
    norm = manifest_to_graph(_valid_manifest())
    assert isinstance(norm.graph, PaymentGraph)
    assert norm.merchant_name == "Acme Commerce"
    assert set(norm.psp_ids) == {"psp_1", "psp_2", "psp_3"}
    assert set(norm.bank_ids) == {"bank_A", "bank_B"}
    # settles_via derived from routes
    assert norm.graph.settles_via == {
        "psp_1": "bank_A",
        "psp_2": "bank_A",
        "psp_3": "bank_B",
    }
    # routing keys are real Method enum members
    assert Method.UPI in norm.graph.routing
    assert Method.CARD in norm.graph.routing


def test_shared_bank_detected():
    norm = manifest_to_graph(_valid_manifest())
    shared = norm.shared_banks
    assert set(shared.keys()) == {"bank_A"}
    assert set(shared["bank_A"]) == {"psp_1", "psp_2"}
    # bank_B is NOT shared (single PSP)
    assert "bank_B" not in shared


def test_invalid_reference_unknown_psp():
    m = _valid_manifest()
    m["routes"].append({"method": "upi", "psp": "psp_ghost", "bank": "bank_A"})
    errs = validate_manifest(m)
    assert any("psp_ghost" in e for e in errs)
    with pytest.raises(TopologyValidationError):
        manifest_to_graph(m)


def test_invalid_reference_unknown_bank():
    m = _valid_manifest()
    m["routes"][0]["bank"] = "bank_ghost"
    errs = validate_manifest(m)
    assert any("bank_ghost" in e for e in errs)


def test_duplicate_psp_id():
    m = _valid_manifest()
    m["psps"].append({"id": "psp_1", "name": "dupe"})
    errs = validate_manifest(m)
    assert any("duplicate PSP id 'psp_1'" in e for e in errs)


def test_duplicate_bank_id():
    m = _valid_manifest()
    m["banks"].append({"id": "bank_A", "name": "dupe"})
    errs = validate_manifest(m)
    assert any("duplicate bank id 'bank_A'" in e for e in errs)


def test_malformed_route_missing_fields():
    m = _valid_manifest()
    m["routes"].append({"method": "upi"})  # missing psp + bank
    errs = validate_manifest(m)
    assert any("unknown PSP" in e for e in errs)
    assert any("unknown bank" in e for e in errs)


def test_unsupported_method_id_rejected():
    m = _valid_manifest()
    m["methods"].append({"id": "crypto", "name": "Crypto"})
    m["routes"].append({"method": "crypto", "psp": "psp_1", "bank": "bank_A"})
    errs = validate_manifest(m)
    assert any("crypto" in e and "supported method" in e for e in errs)


def test_psp_conflicting_banks_rejected():
    m = _valid_manifest()
    # psp_1 already settles via bank_A; assert a conflicting bank_B route
    m["routes"].append({"method": "netbanking", "psp": "psp_1", "bank": "bank_B"})
    errs = validate_manifest(m)
    assert any("conflicting banks" in e for e in errs)


def test_empty_manifest_rejected():
    errs = validate_manifest({})
    assert any("merchant.id is required" in e for e in errs)
    assert any("method" in e for e in errs)
    assert any("PSP" in e for e in errs)
    assert any("bank" in e for e in errs)


def test_negative_weight_rejected():
    m = _valid_manifest()
    m["routes"][0]["weight"] = -1
    errs = validate_manifest(m)
    assert any("weight" in e for e in errs)


def test_weights_accumulate_into_routing():
    m = _valid_manifest()
    norm = manifest_to_graph(m)
    # each method routes to the 3 PSPs with weight 1.0
    upi_routes = dict(norm.graph.routing[Method.UPI])
    assert upi_routes == {"psp_1": 1.0, "psp_2": 1.0, "psp_3": 1.0}
