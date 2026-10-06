from backend.app.copilot.citation_guard import validate_finding


def test_rejects_unknown_chunk_id():
    result = validate_finding(
        finding_text="Evidence confirms compliance.",
        supporting_evidence=[{"chunk_id": "totally_made_up_chunk_999", "quote": "..."}],
        evidence_status="complete",
    )
    assert not result.valid
    assert any("unknown chunk_id" in r for r in result.reasons)


def test_rejects_narrative_citing_control_not_in_evidence():
    result = validate_finding(
        finding_text="This satisfies AC-99 fully.",
        supporting_evidence=[{"chunk_id": "control_AC-6", "quote": "Least privilege enforced per AC-6."}],
        evidence_status="complete",
        document_names=["controls.csv"],
    )
    assert not result.valid
    assert any("AC-99" in r for r in result.reasons)


def test_accepts_well_grounded_finding():
    result = validate_finding(
        finding_text="AC-6 appears satisfied based on the cited review.",
        supporting_evidence=[{"chunk_id": "control_AC-6", "quote": "Least privilege enforced per AC-6."}],
        evidence_status="complete",
        document_names=["controls.csv"],
    )
    assert result.valid


def test_abstention_with_no_evidence_is_valid():
    result = validate_finding(
        finding_text="Insufficient evidence found.",
        supporting_evidence=[],
        evidence_status="insufficient",
    )
    assert result.valid
