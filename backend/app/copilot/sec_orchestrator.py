"""
SEC filing risk-intelligence investigation type -- the second investigation
module alongside access_control, sharing the same retrieval index, citation
guard, persistence layer, and risk-scoring formula (backend/app/copilot/
orchestrator.py is the access-control original; this mirrors its shape
rather than importing it, since the two evidence-sufficiency rules differ
enough that sharing one function would need more branching than it's worth).

Evidence comes from `data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv`
(real, sourced facts -- see docs/DATA_SOURCES.md), indexed as `sec_risk_signal`
chunks by the same ingestion pipeline used for access-control evidence.
"""
from datetime import datetime
from backend.app.retrieval.hybrid_search import HybridIndex
from backend.app.copilot.risk_scoring import score
from backend.app.copilot.citation_guard import validate_finding
from backend.app.db.session import SessionLocal
from backend.app.db.models import Investigation, Finding, FindingEvidence, AuditEvent

MIN_RELEVANCE = 0.02
CONTROL_ID = "SEC-1C"


def _persist(question, ticker, user_id, result: dict) -> dict:
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
            finding_id=finding.id, model_version="sec-orchestrator-v1-rule-based",
            detail={"question": question, "ticker": ticker, "evidence_status": result.get("evidence_status")},
        ))
        session.commit()
        result["investigation_id"] = inv.id
        result["finding_id"] = finding.id
        return result
    finally:
        session.close()


def investigate_sec_filing(ticker: str, question: str = None, user_id: str = "anonymous",
                            persist: bool = True) -> dict:
    ticker = ticker.upper().strip()
    question = question or f"Does {ticker}'s most recent 10-K disclose any material cybersecurity incidents?"

    idx = HybridIndex()
    results = idx.filter(
        lambda c: c["document_type"] == "sec_risk_signal" and f"ticker={ticker}" in c["text"]
    )
    ticker_rows = results

    if not ticker_rows:
        result = {
            "question": question, "ticker": ticker, "control_id": CONTROL_ID,
            "evidence_status": "insufficient",
            "finding": f"No indexed SEC filing signals found for ticker '{ticker}'. "
                       f"Run scripts/download_sec_filings.py and re-run ingestion, or check the ticker.",
            "supporting_evidence": [], "requires_human_review": True,
            "limitations": "No sec_risk_signal chunks matched this ticker.",
        }
        return _persist(question, ticker, user_id, result) if persist else result

    incident_rows = [r for r in ticker_rows if "material_incident" in r["text"]]
    evidence_status = "disclosed_incident" if incident_rows else "no_flagged_incidents"
    gap_severity_map = {"disclosed_incident": 65, "no_flagged_incidents": 10}

    supporting = [{
        "document_name": r["document_name"], "chunk_id": r["chunk_id"],
        "section": r["section_or_row"], "quote": r["text"][:220],
    } for r in ticker_rows[:5]]

    confidence = 0.8
    age_score = 30  # SEC signals here are point-in-time facts, not a recertification cycle
    risk = score(CONTROL_ID, evidence_status, age_score, confidence)
    # Reuse risk_scoring's generic GAP_SEVERITY-shaped inputs via evidence_status directly
    # is imprecise for this module's own statuses, so override the gap component explicitly:
    risk["components"]["evidence_gap_severity"] = gap_severity_map[evidence_status]
    risk["risk_score"] = round(
        0.35 * risk["components"]["control_criticality"]
        + 0.30 * risk["components"]["evidence_gap_severity"]
        + 0.20 * risk["components"]["evidence_age_score"]
        + 0.15 * risk["components"]["confidence_penalty"], 1)
    risk["risk_level"] = "high" if risk["risk_score"] >= 80 else ("medium" if risk["risk_score"] >= 50 else "low")

    if evidence_status == "disclosed_incident":
        finding_text = (f"{ticker}'s SEC filings disclose at least one material incident flagged in "
                         f"indexed risk signals. See cited rows for sourced specifics.")
    else:
        finding_text = (f"No material-incident signal is currently indexed for {ticker}. "
                         f"This reflects only the signals in sec_risk_signals.csv, not a full filing review.")

    result = {
        "question": question, "ticker": ticker, "control_id": CONTROL_ID,
        "evidence_status": evidence_status, "risk_level": risk["risk_level"],
        "risk_score": risk["risk_score"], "risk_components": risk["components"],
        "narrative_source": "template",
        "finding": finding_text,
        "supporting_evidence": supporting, "confidence": confidence,
        "requires_human_review": evidence_status == "disclosed_incident",
        "limitations": "Evidence is limited to the curated sec_risk_signals.csv (a handful of "
                       "verified facts per company), not a full parse of the filing. Wiring in "
                       "sec_filing_parser.py's live keyword scan over a fully downloaded 10-K is "
                       "the natural next step for broader coverage.",
    }

    final_check = validate_finding(result["finding"], result["supporting_evidence"], result["evidence_status"])
    if not final_check.valid:
        result["finding"] = "Insufficient validated evidence to report a finding for this ticker."
        result["narrative_source"] = "template-fallback-after-final-check"
        result["limitations"] += f" [citation guard caught: {'; '.join(final_check.reasons)}]"

    return _persist(question, ticker, user_id, result) if persist else result


if __name__ == "__main__":
    import json
    print(json.dumps(investigate_sec_filing("CRWD", persist=False), indent=2))
