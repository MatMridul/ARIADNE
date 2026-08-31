"""Phase 1 tests: the static graph's shared-dependency lookups and immutable reroute."""
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph


def test_psps_for_bank_shared_and_control():
    g = default_graph()
    assert g.psps_for_bank("bank_A") == ["psp_1", "psp_2"]
    assert g.psps_for_bank("bank_B") == ["psp_3"]


def test_shared_banks_only_returns_multi_psp_banks():
    g = default_graph()
    shared = g.shared_banks()
    assert shared == {"bank_A": ["psp_1", "psp_2"]}
    assert "bank_B" not in shared  # single PSP -> not a shared dependency


def test_banks_for_method_reaches_both_banks():
    g = default_graph()
    assert g.banks_for_method(Method.UPI) == {"bank_A", "bank_B"}


def test_reroute_returns_new_graph_and_leaves_original_unchanged():
    g = default_graph()
    original_upi = dict(g.routing[Method.UPI])
    g2 = g.reroute(Method.UPI, from_psp="psp_1", to_psp="psp_3")

    # original untouched (immutable-style, for rollback)
    assert dict(g.routing[Method.UPI]) == original_upi
    assert g is not g2

    # in the new graph psp_1 carries no UPI, psp_3 absorbed its weight
    new_weights = dict(g2.routing[Method.UPI])
    assert new_weights["psp_1"] == 0.0
    assert new_weights["psp_3"] == original_upi["psp_1"] + original_upi["psp_3"]


def test_reroute_rejects_psp_not_on_method():
    g = default_graph()
    # remove psp_2 from CARD then try to reroute from it
    g.routing[Method.CARD] = [("psp_1", 1.0), ("psp_3", 1.0)]
    try:
        g.reroute(Method.CARD, from_psp="psp_2", to_psp="psp_1")
        assert False, "expected ValueError"
    except ValueError:
        pass
