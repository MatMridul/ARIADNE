"""Tests for model/graph.py (BUILD_SPEC §5 / BUILD_ORDER step 4)."""

from ariadne.model.entities import Method
from ariadne.model.graph import default_graph


def test_default_graph_topology():
    g = default_graph()
    assert len(g.routing) == 3  # 3 methods
    assert len(g.psps) == 3  # 3 PSPs
    assert len(g.banks) == 2  # 2 banks
    assert g.settles_via == {
        "psp_1": "bank_A",
        "psp_2": "bank_A",
        "psp_3": "bank_B",
    }


def test_psps_for_bank_returns_shared_psps():
    g = default_graph()
    assert sorted(g.psps_for_bank("bank_A")) == ["psp_1", "psp_2"]
    assert g.psps_for_bank("bank_B") == ["psp_3"]


def test_shared_banks_only_bank_a():
    g = default_graph()
    shared = g.shared_banks()
    assert "bank_A" in shared
    assert sorted(shared["bank_A"]) == ["psp_1", "psp_2"]
    # bank_B is used by only one PSP, so it must be excluded.
    assert "bank_B" not in shared


def test_reroute_returns_new_graph_and_leaves_original_unchanged():
    g = default_graph()
    original_upi = list(g.routing[Method.UPI])

    new_g = g.reroute(Method.UPI, "psp_1", "psp_3")

    # A new graph object is returned.
    assert new_g is not g
    # Original graph's routing is untouched.
    assert g.routing[Method.UPI] == original_upi
    assert g.routing is not new_g.routing

    # In the new graph, psp_1 no longer carries UPI and its weight moved to psp_3.
    new_upi = dict(new_g.routing[Method.UPI])
    assert "psp_1" not in new_upi
    assert new_upi["psp_3"] == 1.0
    # Total routing weight is conserved.
    assert sum(dict(original_upi).values()) == sum(new_upi.values())
