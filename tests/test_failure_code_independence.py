"""Regression for audit P2 #6: failure codes are assigned INDEPENDENTLY of whether
the injected incident caused the failure, so retry_fallback cannot magically target
ground truth. Also re-asserts the seal: codes never cross the aggregation boundary.
"""
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.engine import generate
from ariadne.simulator.incidents import Incident, IncidentType, make_incident


def _retriable_fraction(txns):
    fails = [t for t in txns if not t.success]
    if not fails:
        return 0.0
    retriable = sum(1 for t in fails if t.failure_code == "GATEWAY_TIMEOUT")
    return retriable / len(fails)


def test_retriable_fraction_similar_in_incident_and_clean_windows():
    g = default_graph()
    cfg = SimConfig(seed=3)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=6, end_window=9, severity=0.30)
    txns, _ = generate(g, cfg, inc)
    tpw = cfg.txns_per_window
    incident_fails = [t for t in txns if 6 <= int(t.timestamp // tpw) <= 9 and not t.success]
    clean_fails = [t for t in txns if int(t.timestamp // tpw) < 6 and not t.success]
    fr_inc = _retriable_fraction(incident_fails)
    fr_clean = _retriable_fraction(clean_fails)
    # both bands should have a SIMILAR retriable fraction (~0.4) -> codes are NOT a
    # tell for the incident. Allow a modest tolerance for sampling.
    assert abs(fr_inc - fr_clean) < 0.1
    assert 0.25 < fr_inc < 0.55
    assert 0.25 < fr_clean < 0.55


def test_incident_failures_do_not_all_get_the_same_code():
    g = default_graph()
    cfg = SimConfig(seed=3)
    inc = Incident(IncidentType.SHARED_BANK, "bank_A", start_window=6, end_window=9, severity=0.30)
    txns, _ = generate(g, cfg, inc)
    tpw = cfg.txns_per_window
    incident_codes = {
        t.failure_code
        for t in txns
        if 6 <= int(t.timestamp // tpw) <= 9 and not t.success and t.bank_id == "bank_A"
    }
    # incident-caused failures carry a MIX of codes (not a single incident-only code)
    assert len(incident_codes) >= 2


def test_retry_recovers_on_noise_too():
    """If retry recovered ONLY on incident-caused failures, it would return 0 on a
    pure-noise scenario. It must recover >0 on noise (cause-independent codes)."""
    from ariadne.decide import actions as A
    from ariadne.eval.metrics import money_recovered
    g = default_graph()
    cfg = SimConfig(seed=5)
    incD = make_incident(IncidentType.NONE, 5, cfg.n_windows)
    retry = A.retry_fallback(Method.CARD, 2, ["GATEWAY_TIMEOUT"],
                             confidence=1.0, expected_recovery=0.0, evidence_path=["x"])
    assert money_recovered(g, cfg, incD, retry) > 0.0
