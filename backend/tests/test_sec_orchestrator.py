from backend.app.copilot.sec_orchestrator import investigate_sec_filing


def test_known_ticker_with_real_incident_flags_medium_or_high_risk():
    r = investigate_sec_filing("CRWD", persist=False)
    assert r["evidence_status"] == "disclosed_incident"
    assert r["risk_level"] in ("medium", "high")
    assert len(r["supporting_evidence"]) > 0
    # every cited chunk_id must be real -- reuses the same citation guard as access_control
    from backend.app.copilot.citation_guard import validate_finding
    check = validate_finding(r["finding"], r["supporting_evidence"], r["evidence_status"])
    assert check.valid, check.reasons


def test_unknown_ticker_abstains_rather_than_guessing():
    r = investigate_sec_filing("NOT_A_REAL_TICKER", persist=False)
    assert r["evidence_status"] == "insufficient"
    assert r["supporting_evidence"] == []
