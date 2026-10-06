"""
Deterministic investigation orchestrator (Phase 1-2 scope, no paid LLM needed):

    question -> hybrid retrieval -> evidence-sufficiency check
             -> rule-based finding assembly -> risk scoring -> structured JSON

This is intentionally NOT a free-text LLM generator: every field is derived
from retrieved evidence with a traceable rule, which is what "no evidence, no
conclusion" requires. Swap in a local Ollama model for prose generation of the
`finding` narrative once you have it running locally -- see docs/architecture.md
for exactly where that plugs in (`_summarize` below).
"""
import re
from datetime import datetime
from backend.app.retrieval.hybrid_search import HybridIndex
from backend.app.copilot.risk_scoring import score
from backend.app.copilot.llm_client import get_llm_client
from backend.app.copilot.citation_guard import validate_finding
from backend.app.db.session import SessionLocal
from backend.app.db.models import Investigation, Finding, FindingEvidence, AuditEvent

MIN_RELEVANCE = 0.02  # below this, we do not have "sufficient evidence"


def _find_policy_requirement(results):
    for r in results:
        if r["document_type"] == "policy":
            return r
    return None


def _find_evidence_rows(results, quarter_keyword=None):
    rows = [r for r in results if r["document_type"] == "evidence_csv"]
    if quarter_keyword:
        rows = [r for r in rows if quarter_keyword in r["text"]]
    return rows


def _evidence_status_from_rows(rows, period_specific: bool):
    """period_specific=False means the question didn't name a reporting
    period (e.g. "what frequency is required" rather than "was Q3
    completed"). In that case we deliberately do NOT scan evidence rows for
    Missing/Partial signals: `rows` in that case is whatever evidence_csv
    chunks happened to rank near the policy text on general vocabulary
    overlap -- it might include rows from a quarter never asked about, and
    scanning them for "Missing"/"Partial" produced real false positives
    during evaluation (a general policy question about MFA was reported as
    "missing" evidence purely because an unrelated Q4 gap chunk ranked
    nearby). For a general/policy question, finding the policy at all IS
    the complete answer; period-specific status only makes sense when a
    period was actually asked about."""
    if not period_specific:
        return "complete"
    if not rows:
        return "missing"
    text = " ".join(r["text"] for r in rows)
    if "evidence_status=Missing" in text:
        return "missing"
    if "evidence_status=Partial" in text or "approval_status=Pending" in text:
        return "partial"
    return "complete"


def _summarize(policy_chunk, evidence_rows, evidence_status, question=None, supporting=None):
    """Try the local LLM (if enabled and reachable) for a richer narrative;
    always fall back to the citation-safe rule-based template, and always
    validate whatever the LLM produced before trusting it."""
    template = _template_summary(evidence_status)

    llm = get_llm_client()
    policy_text = policy_chunk["text"][:400] if policy_chunk else ""
    evidence_texts = [r["text"][:300] for r in evidence_rows]
    llm_narrative = llm.generate_finding_narrative(question or "", policy_text, evidence_texts)

    if llm_narrative is None:
        return template, "template"

    check = validate_finding(llm_narrative, supporting or [], evidence_status)
    if not check.valid:
        return template, "template-fallback-after-failed-llm-validation"

    return llm_narrative, "llm"


def _template_summary(evidence_status):
    if evidence_status == "missing":
        return "No indexed evidence was found for the requested period."
    if evidence_status == "partial":
        return "Partial evidence was found, but it does not fully satisfy the policy requirement (e.g. missing approval)."
    return "Evidence was found and appears to satisfy the policy requirement."


def _persist(question, control_id, user_id, result: dict) -> dict:
    """Write the investigation, finding, evidence links, and an audit event.
    This is what makes the system's output traceable end to end, per the
    project's core "auditability" requirement -- not just a JSON blob."""
    session = SessionLocal()
    try:
        inv = Investigation(title=question[:120], question=question, created_by=user_id)
        session.add(inv)
        session.flush()

        finding = Finding(
            investigation_id=inv.id,
            control_id=control_id,
            risk_level=result.get("risk_level"),
            risk_score=result.get("risk_score"),
            finding_text=result.get("finding"),
            evidence_status=result.get("evidence_status"),
            confidence=result.get("confidence"),
            requires_human_review=result.get("requires_human_review", True),
            narrative_source=result.get("narrative_source", "template"),
            limitations=result.get("limitations"),
        )
        session.add(finding)
        session.flush()

        for e in result.get("supporting_evidence", []):
            session.add(FindingEvidence(
                finding_id=finding.id, chunk_id=e.get("chunk_id"),
                document_name=e.get("document_name"), quote=e.get("quote"),
                relevance_score=None,
            ))

        session.add(AuditEvent(
            event_type="investigation_created", user_id=user_id,
            investigation_id=inv.id, finding_id=finding.id,
            detail={"question": question, "evidence_status": result.get("evidence_status")},
        ))
        session.commit()

        result["investigation_id"] = inv.id
        result["finding_id"] = finding.id
        return result
    finally:
        session.close()


def investigate(question: str, control_id: str = "AC-6", user_id: str = "anonymous", persist: bool = True) -> dict:
    idx = HybridIndex()
    # Scope retrieval to this module's own document types. Without this, adding
    # the SEC and vendor-risk modules' evidence chunks to the shared corpus
    # measurably diluted BM25/TF-IDF rankings for access-control questions --
    # a real regression caught by this project's own test suite (see the git
    # history / README for the concrete before/after). Each investigation
    # module should search its own relevant slice of the corpus, not the
    # whole thing, as the number of modules grows.
    ACCESS_CONTROL_DOC_TYPES = {"policy", "evidence_csv", "metadata_csv", "control_catalog"}
    results = idx.search(question, k=20,
                          metadata_filter=lambda c: c["document_type"] in ACCESS_CONTROL_DOC_TYPES)

    sufficient = any(r["relevance_score"] >= MIN_RELEVANCE for r in results)
    policy_chunk = _find_policy_requirement(results)

    quarter_match = re.search(r"Q[1-4]\s*2025|2025\s*Q[1-4]", question, re.IGNORECASE)
    quarter_keyword = None
    if quarter_match:
        q = re.search(r"Q[1-4]", quarter_match.group(0), re.IGNORECASE).group(0).upper()
        quarter_keyword = f"2025-{q}"

    evidence_rows = _find_evidence_rows(results, quarter_keyword)
    evidence_status = _evidence_status_from_rows(evidence_rows, period_specific=bool(quarter_keyword))

    if not sufficient or not policy_chunk:
        result = {
            "question": question,
            "evidence_status": "insufficient",
            "finding": "Insufficient evidence found.",
            "supporting_evidence": [],
            "requires_human_review": True,
            "limitations": "The system could not retrieve sufficient supporting material for this question.",
        }
        return _persist(question, control_id, user_id, result) if persist else result

    age_score = 40 if evidence_status == "partial" else (100 if evidence_status == "missing" else 10)
    confidence = 0.85 if evidence_status != "missing" else 0.5
    risk = score(control_id, evidence_status, age_score, confidence)

    supporting = []
    if policy_chunk:
        supporting.append({
            "document_name": policy_chunk["document_name"],
            "chunk_id": policy_chunk["chunk_id"],
            "section": policy_chunk["section_or_row"],
            "quote": policy_chunk["text"][:220],
        })
    for r in (evidence_rows[:3] if quarter_keyword else []):
        supporting.append({
            "document_name": r["document_name"], "chunk_id": r["chunk_id"],
            "section": r["section_or_row"], "quote": r["text"][:220],
        })

    narrative, narrative_source = _summarize(policy_chunk, evidence_rows, evidence_status,
                                              question=question, supporting=supporting)

    result = {
        "question": question,
        "control_id": control_id,
        "evidence_status": evidence_status,
        "risk_level": risk["risk_level"],
        "risk_score": risk["risk_score"],
        "risk_components": risk["components"],
        "narrative_source": narrative_source,  # "template" or "llm"
        "finding": narrative,
        "policy_requirement": policy_chunk["text"][:300] if policy_chunk else None,
        "supporting_evidence": supporting,
        "confidence": confidence,
        "requires_human_review": evidence_status != "complete",
        "limitations": "This is a rule-based v1 orchestrator (no LLM). The finding narrative is templated, not generated -- see orchestrator.py docstring for the local-LLM swap point.",
    }

    # Final safety net: validate the assembled result regardless of which
    # narrative source produced it. If this ever fails, something upstream
    # has a bug -- don't ship a finding that can't be traced to evidence.
    final_check = validate_finding(result["finding"], result["supporting_evidence"], result["evidence_status"])
    if not final_check.valid:
        result["finding"] = _template_summary(evidence_status)
        result["narrative_source"] = "template-fallback-after-final-check"
        result["limitations"] += f" [citation guard caught: {'; '.join(final_check.reasons)}]"

    return _persist(question, control_id, user_id, result) if persist else result


if __name__ == "__main__":
    import json
    result = investigate("Was the Q3 2025 privileged-access review completed and approved for CoreBanking?")
    print(json.dumps(result, indent=2))
