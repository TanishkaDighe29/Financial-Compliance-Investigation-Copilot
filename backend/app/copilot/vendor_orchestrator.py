"""
Vendor-risk investigation type -- the third investigation module, alongside
access_control and sec_orchestrator, sharing the same retrieval index,
citation guard, risk-scoring formula, and persistence layer.

Evidence is a vendor's SCRM questionnaire responses (real CISA Vendor SCRM
Template questions -- see data/frameworks/cisa_scrm/scrm_questions.csv --
answered by a fictional vendor; see docs/data_governance.md). "No" and
"Alternate" answers are treated as gaps; "Yes" is treated as satisfied;
"N/A" is excluded from the gap count.
"""
from backend.app.retrieval.hybrid_search import HybridIndex
from backend.app.copilot.risk_scoring import score
from backend.app.copilot.citation_guard import validate_finding
from backend.app.db.session import SessionLocal
from backend.app.db.models import Investigation, Finding, FindingEvidence, AuditEvent

CONTROL_ID = "SCRM-VENDOR"
KNOWN_VENDORS = {"northstar_cloud", "apex_payments", "redbridge_data"}


def _persist(question, vendor, user_id, result: dict) -> dict:
    session = SessionLocal()
    try:
        inv = Investigation(title=question[:120], question=question, created_by=user_id)
        session.add(inv)
        session.flush()

        finding = Finding(
            investigation_id=inv.id, control_id=CONTROL_ID,
            risk_level=result.get("risk_level"), risk_score=result.get("risk_score"),
            finding_text=result.get("finding"), evidence_status=result.get("evidence_status"),
            confidence=result.get("confidence"), requires_human_review=result.get("requires_human_review", True),
            narrative_source=result.get("narrative_source", "template"),
            limitations=result.get("limitations"),
        )
        session.add(finding)
        session.flush()

        for e in result.get("supporting_evidence", []):
            session.add(FindingEvidence(
                finding_id=finding.id, chunk_id=e.get("chunk_id"),
                document_name=e.get("document_name"), quote=e.get("quote"),
            ))

        session.add(AuditEvent(
            event_type="investigation_created", user_id=user_id, investigation_id=inv.id,
            finding_id=finding.id, model_version="vendor-orchestrator-v1-rule-based",
            detail={"question": question, "vendor": vendor, "evidence_status": result.get("evidence_status")},
        ))
        session.commit()
        result["investigation_id"] = inv.id
        result["finding_id"] = finding.id
        return result
    finally:
        session.close()


def investigate_vendor(vendor: str, question: str = None, user_id: str = "anonymous",
                        persist: bool = True) -> dict:
    vendor_key = vendor.lower().strip().replace(" ", "_")
    question = question or f"What SCRM gaps exist for vendor '{vendor}'?"

    idx = HybridIndex()
    vendor_rows = idx.filter(
        lambda c: c["document_type"] == "vendor_scrm_response" and vendor_key in c["document_name"]
    )

    if not vendor_rows:
        result = {
            "question": question, "vendor": vendor, "control_id": CONTROL_ID,
            "evidence_status": "insufficient",
            "finding": f"No indexed SCRM questionnaire responses found for vendor '{vendor}'. "
                       f"Known vendors: {sorted(KNOWN_VENDORS)}.",
            "supporting_evidence": [], "requires_human_review": True,
            "limitations": "No vendor_scrm_response chunks matched this vendor.",
        }
        return _persist(question, vendor, user_id, result) if persist else result

    gap_rows = [r for r in vendor_rows if "answer=No" in r["text"] or "answer=Alternate" in r["text"]]
    total_answered = len([r for r in vendor_rows if "answer=N/A" not in r["text"]])
    gap_count = len(gap_rows)
    gap_ratio = gap_count / total_answered if total_answered else 0

    if gap_ratio >= 0.3:
        evidence_status, gap_severity = "significant_gaps", 80
    elif gap_ratio > 0:
        evidence_status, gap_severity = "minor_gaps", 45
    else:
        evidence_status, gap_severity = "no_flagged_gaps", 5

    supporting = [{
        "document_name": r["document_name"], "chunk_id": r["chunk_id"],
        "section": r["section_or_row"], "quote": r["text"][:220],
    } for r in (gap_rows[:5] if gap_rows else vendor_rows[:3])]

    confidence = 0.75
    risk = score(CONTROL_ID, "partial", 20, confidence)  # placeholder call to reuse component shape
    criticality = risk["components"]["control_criticality"]
    confidence_penalty = risk["components"]["confidence_penalty"]
    risk_score_val = round(0.35 * criticality + 0.30 * gap_severity + 0.20 * 20 + 0.15 * confidence_penalty, 1)
    risk_level = "high" if risk_score_val >= 80 else ("medium" if risk_score_val >= 50 else "low")

    if evidence_status == "significant_gaps":
        finding_text = (f"{vendor} shows significant SCRM gaps ({gap_count}/{total_answered} answered "
                         f"questions flagged 'No' or 'Alternate'). See cited responses for specifics.")
    elif evidence_status == "minor_gaps":
        finding_text = (f"{vendor} shows a small number of SCRM gaps ({gap_count}/{total_answered}). "
                         f"See cited responses for specifics.")
    else:
        finding_text = f"No 'No'/'Alternate' answers found in {vendor}'s indexed SCRM responses."

    result = {
        "question": question, "vendor": vendor, "control_id": CONTROL_ID,
        "evidence_status": evidence_status, "risk_level": risk_level, "risk_score": risk_score_val,
        "risk_components": {"control_criticality": criticality, "evidence_gap_severity": gap_severity,
                             "evidence_age_score": 20, "confidence_penalty": confidence_penalty,
                             "gaps_found": gap_count, "questions_answered": total_answered},
        "narrative_source": "template",
        "finding": finding_text,
        "supporting_evidence": supporting, "confidence": confidence,
        "requires_human_review": evidence_status != "no_flagged_gaps",
        "limitations": "Evidence is limited to 15 curated CISA SCRM Template questions per vendor "
                       "(synthetic responses), not the full ~90-question template.",
    }

    final_check = validate_finding(result["finding"], result["supporting_evidence"], result["evidence_status"])
    if not final_check.valid:
        result["finding"] = "Insufficient validated evidence to report a finding for this vendor."
        result["narrative_source"] = "template-fallback-after-final-check"
        result["limitations"] += f" [citation guard caught: {'; '.join(final_check.reasons)}]"

    return _persist(question, vendor, user_id, result) if persist else result


if __name__ == "__main__":
    import json
    for v in ("northstar_cloud", "apex_payments", "redbridge_data"):
        print(f"--- {v} ---")
        print(json.dumps(investigate_vendor(v, persist=False), indent=2)[:600])
        print()
