from backend.app.ingestion.sec_filing_parser import analyze_filing

FIXTURE = "backend/tests/fixtures/sample_10k_synthetic.html"


def test_separates_risk_factors_from_cybersecurity_section():
    result = analyze_filing(FIXTURE)
    assert result["risk_factors_char_count"] > 0
    assert result["cybersecurity_char_count"] > 0
    assert "material weakness" in result["risk_factors_excerpt"].lower()


def test_flags_material_weakness_and_incident_and_litigation():
    result = analyze_filing(FIXTURE)
    flags = result["risk_keyword_flags"]
    assert "material_weakness" in flags
    assert "data_breach_or_incident" in flags
    assert "litigation_or_investigation" in flags


def test_restatement_flag_only_in_cybersecurity_section_not_risk_factors():
    result = analyze_filing(FIXTURE)
    assert "restatement" in result["cybersecurity_keyword_flags"]
    assert "restatement" not in result["risk_factors_keyword_flags"] if "risk_factors_keyword_flags" in result else True
