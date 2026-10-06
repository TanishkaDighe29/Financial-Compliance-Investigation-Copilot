"""Read-side query helpers for the reviewer queue and audit trail views."""
from backend.app.db.session import SessionLocal
from backend.app.db.models import Finding, Investigation, ReviewFeedback, AuditEvent, FindingEvidence


def list_findings(status: str = None, risk_level: str = None):
    session = SessionLocal()
    try:
        q = session.query(Finding)
        if status:
            q = q.filter(Finding.status == status)
        if risk_level:
            q = q.filter(Finding.risk_level == risk_level)
        findings = q.order_by(Finding.created_at.desc()).all()
        return [_finding_to_dict(f, session) for f in findings]
    finally:
        session.close()


def get_finding(finding_id: str):
    session = SessionLocal()
    try:
        f = session.get(Finding, finding_id)
        return _finding_to_dict(f, session) if f else None
    finally:
        session.close()


def _finding_to_dict(f: Finding, session):
    evidence = session.query(FindingEvidence).filter_by(finding_id=f.id).all()
    reviews = session.query(ReviewFeedback).filter_by(finding_id=f.id).all()
    return {
        "finding_id": f.id, "investigation_id": f.investigation_id,
        "control_id": f.control_id, "risk_level": f.risk_level, "risk_score": f.risk_score,
        "finding_text": f.finding_text, "evidence_status": f.evidence_status,
        "confidence": f.confidence, "requires_human_review": f.requires_human_review,
        "status": f.status, "limitations": f.limitations, "narrative_source": f.narrative_source,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "evidence": [{"chunk_id": e.chunk_id, "document_name": e.document_name, "quote": e.quote} for e in evidence],
        "reviews": [{"reviewer": r.reviewer, "decision": r.decision, "comment": r.comment,
                     "timestamp": r.timestamp.isoformat()} for r in reviews],
    }


def submit_review(finding_id: str, reviewer: str, decision: str, comment: str = ""):
    session = SessionLocal()
    try:
        finding = session.get(Finding, finding_id)
        if finding is None:
            return None
        review = ReviewFeedback(finding_id=finding_id, reviewer=reviewer, decision=decision, comment=comment)
        session.add(review)

        status_map = {"accept": "accepted", "reject": "rejected", "request_evidence": "needs_more_evidence"}
        finding.status = status_map.get(decision, finding.status)

        session.add(AuditEvent(
            event_type="review_submitted", user_id=reviewer, finding_id=finding_id,
            investigation_id=finding.investigation_id,
            detail={"decision": decision, "comment": comment},
        ))
        session.commit()
        return _finding_to_dict(finding, session)
    finally:
        session.close()


def get_audit_trail(investigation_id: str = None):
    session = SessionLocal()
    try:
        q = session.query(AuditEvent)
        if investigation_id:
            q = q.filter(AuditEvent.investigation_id == investigation_id)
        events = q.order_by(AuditEvent.timestamp.asc()).all()
        return [{"event_type": e.event_type, "user_id": e.user_id, "investigation_id": e.investigation_id,
                 "finding_id": e.finding_id, "model_version": e.model_version, "detail": e.detail,
                 "timestamp": e.timestamp.isoformat()} for e in events]
    finally:
        session.close()
