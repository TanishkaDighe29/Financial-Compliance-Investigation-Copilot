from backend.app.copilot.vendor_orchestrator import investigate_vendor
from backend.app.copilot.citation_guard import validate_finding


def test_northstar_shows_the_one_planted_mfa_gap():
    r = investigate_vendor("northstar_cloud", persist=False)
    assert r["risk_components"]["gaps_found"] == 1
    check = validate_finding(r["finding"], r["supporting_evidence"], r["evidence_status"])
    assert check.valid, check.reasons


def test_apex_payments_shows_all_three_planted_gaps():
    r = investigate_vendor("apex_payments", persist=False)
    assert r["risk_components"]["gaps_found"] == 3
    assert r["risk_components"]["questions_answered"] == 15


def test_redbridge_flagged_as_significant_gaps():
    r = investigate_vendor("redbridge_data", persist=False)
    assert r["evidence_status"] == "significant_gaps"
    assert r["risk_components"]["gaps_found"] >= 10


def test_unknown_vendor_abstains():
    r = investigate_vendor("not_a_real_vendor", persist=False)
    assert r["evidence_status"] == "insufficient"
    assert r["supporting_evidence"] == []
