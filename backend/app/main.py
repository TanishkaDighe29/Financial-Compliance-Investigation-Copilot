"""
FastAPI application exposing the compliance copilot's core endpoints.
Run: uvicorn backend.app.main:app --reload --port 8000
Docs: http://localhost:8000/docs

Mock users for the X-User-Id header (see core/security.py):
  analyst1 (analyst) | reviewer1 (reviewer) | manager1 (compliance_manager)
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from backend.app.retrieval.hybrid_search import HybridIndex
from backend.app.copilot.orchestrator import investigate
from backend.app.copilot.sec_orchestrator import investigate_sec_filing
from backend.app.copilot.vendor_orchestrator import investigate_vendor
from backend.app.db.session import init_db, sync_chunks_to_db
from backend.app.db import repositories as repo
from backend.app.core.security import get_current_user, require_reviewer
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sync_chunks_to_db()
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Financial Compliance Investigation Copilot",
    description="Evidence-grounded decision-support API for compliance/audit investigations. "
                "Educational portfolio prototype -- not legal, audit, or compliance advice.",
    version="0.2.0",
)

# Dev-only CORS: the static reviewer dashboard (frontend/index.html) is opened
# directly from disk or a simple file server, so it needs cross-origin access.
# Tighten this to a specific origin before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static reviewer dashboard from this same app (so `docker compose
# up` needs exactly one container/port). frontend/index.html's API base is
# same-origin-aware, so it works both this way and opened directly from disk.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")

_index = None


def get_index():
    global _index
    if _index is None:
        _index = HybridIndex()
    return _index


class SearchRequest(BaseModel):
    query: str
    k: int = 6


class InvestigationRequest(BaseModel):
    question: str
    control_id: str = "AC-6"


class SecFilingInvestigationRequest(BaseModel):
    ticker: str
    question: Optional[str] = None


class VendorInvestigationRequest(BaseModel):
    vendor: str
    question: Optional[str] = None


class ReviewRequest(BaseModel):
    decision: str  # accept | reject | request_evidence
    comment: Optional[str] = ""


@app.get("/")
def root():
    return {"status": "ok", "service": "financial-compliance-copilot"}


@app.post("/search")
def search(req: SearchRequest):
    return {"results": get_index().search(req.query, k=req.k)}


@app.post("/investigations")
def create_investigation(req: InvestigationRequest, user=Depends(get_current_user)):
    return investigate(req.question, control_id=req.control_id, user_id=user["user_id"])


@app.post("/investigations/sec-filing")
def create_sec_investigation(req: SecFilingInvestigationRequest, user=Depends(get_current_user)):
    """Second investigation module: SEC filing risk intelligence, backed by
    real sourced facts extracted from live SEC EDGAR 10-Ks (see
    docs/DATA_SOURCES.md and data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv).
    Currently covers CRWD; other tickers return an 'insufficient evidence'
    finding until their signals are added (see scripts/download_sec_filings.py)."""
    return investigate_sec_filing(req.ticker, question=req.question, user_id=user["user_id"])


@app.post("/investigations/vendor-risk")
def create_vendor_investigation(req: VendorInvestigationRequest, user=Depends(get_current_user)):
    """Third investigation module: vendor SCRM risk, backed by real CISA
    Vendor SCRM Template questions (public-domain U.S. government work) with
    synthetic fictional-vendor responses (see docs/data_governance.md).
    Known vendors: northstar_cloud, apex_payments, redbridge_data."""
    return investigate_vendor(req.vendor, question=req.question, user_id=user["user_id"])


@app.get("/findings")
def get_findings(status: Optional[str] = None, risk_level: Optional[str] = None, user=Depends(get_current_user)):
    """Reviewer queue: filter by status (pending_review|accepted|rejected|needs_more_evidence)
    and/or risk_level (high|medium|low)."""
    return {"findings": repo.list_findings(status=status, risk_level=risk_level)}


@app.get("/findings/{finding_id}")
def get_finding(finding_id: str, user=Depends(get_current_user)):
    finding = repo.get_finding(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@app.post("/findings/{finding_id}/review")
def review_finding(finding_id: str, req: ReviewRequest, user=Depends(get_current_user)):
    require_reviewer(user)
    if req.decision not in ("accept", "reject", "request_evidence"):
        raise HTTPException(status_code=400, detail="decision must be accept|reject|request_evidence")
    result = repo.submit_review(finding_id, reviewer=user["user_id"], decision=req.decision, comment=req.comment)
    if result is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return result


@app.get("/audit-log")
def audit_log(investigation_id: Optional[str] = None, user=Depends(get_current_user)):
    return {"events": repo.get_audit_trail(investigation_id=investigation_id)}
