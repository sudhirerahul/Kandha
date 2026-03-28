# analyze.py — Cost Analyzer router: bill upload, parsing, and savings report
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.analysis import AnalysisSession, SpendReport
from services.dify import DifyClient, get_dify_client
from services.gmi import GMIClient, get_gmi_client
from services.parser import ParsedBill, parse_bill_csv
from services.photon_guard import PhotonGuardClient, get_photon_guard

log = structlog.get_logger()
router = APIRouter(prefix="/analyze", tags=["analyze"])

_MAX_UPLOAD_MB = 50
_MAX_BYTES = _MAX_UPLOAD_MB * 1024 * 1024

# Hetzner hardware reference (simplified pricing — fetch from API in production)
_HETZNER_HARDWARE = [
    {"name": "AX42", "vcpu": 24, "ram_gb": 64, "nvme_tb": 1.92, "price_mo": 58},
    {"name": "AX102", "vcpu": 48, "ram_gb": 128, "nvme_tb": 1.92, "price_mo": 94},
    {"name": "AX162", "vcpu": 96, "ram_gb": 192, "nvme_tb": 3.84, "price_mo": 136},
]


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Returned immediately after a successful upload + analysis."""
    analysis_session_id: str
    status: str
    provider: str
    line_items: int
    total_usd: float
    breakdown: list[dict[str, Any]]
    savings_report: dict[str, Any]
    hardware_recommendations: list[dict[str, Any]]


class SessionSummary(BaseModel):
    """Lightweight session status for polling."""
    analysis_session_id: str
    status: str
    file_name: str


# ── Helpers ───────────────────────────────────────────────────────────────────



def _recommend_hardware(total_usd: float) -> list[dict[str, Any]]:
    """Simple heuristic: recommend 1–3 Hetzner nodes based on current cloud spend."""
    recommendations = []
    for hw in _HETZNER_HARDWARE:
        for node_count in [1, 2, 3]:
            monthly = hw["price_mo"] * node_count
            if monthly < total_usd * 0.6:  # only recommend if saves 40%+
                savings_mo = total_usd - monthly
                recommendations.append(
                    {
                        "provider": "Hetzner",
                        "model": hw["name"],
                        "nodes": node_count,
                        "vcpu_total": hw["vcpu"] * node_count,
                        "ram_gb_total": hw["ram_gb"] * node_count,
                        "price_mo": monthly,
                        "savings_mo": round(savings_mo, 2),
                        "savings_pct": round((savings_mo / total_usd) * 100, 1),
                    }
                )
    # Return top 3 by savings
    return sorted(recommendations, key=lambda r: r["savings_mo"], reverse=True)[:3]


async def _build_savings_report(
    bill: ParsedBill,
    gmi: GMIClient,
    dify: DifyClient,
    user_id: str,
) -> dict[str, Any]:
    """Generate a savings summary using Dify (if configured) or GMI directly."""
    # Try Dify first
    dify_result = await dify.run_analyze_workflow(bill.to_dict(), user_id)
    if dify_result:
        log.info("analyze.savings.via_dify")
        return dify_result

    # Fall back to direct GMI completion
    log.info("analyze.savings.via_gmi")
    top = bill.top_services(8)
    service_list = "\n".join(
        f"- {s.service}: ${s.cost_usd:.2f}/mo" for s in top
    )
    prompt = (
        f"A customer's cloud bill has been parsed. Total: ${bill.total_usd:.2f}/mo on {bill.provider}.\n\n"
        f"Top services by spend:\n{service_list}\n\n"
        "In 3–4 sentences, identify the biggest cost drivers and explain why bare-metal "
        "migration could reduce these costs. Be specific about which services benefit most "
        "from owning hardware vs renting cloud capacity. Keep it under 120 words."
    )
    summary = await gmi.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return {"summary": summary, "source": "gmi"}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_bill(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    gmi: GMIClient = Depends(get_gmi_client),
    dify: DifyClient = Depends(get_dify_client),
    guard: PhotonGuardClient = Depends(get_photon_guard),
    user_id: str = Depends(get_current_user),
) -> UploadResponse:
    """Accept a cloud bill CSV, parse it, generate a savings report, and persist results."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="No file provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="Only CSV and JSON files are supported.")

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_UPLOAD_MB}MB limit.")

    log.info("analyze.upload.received", filename=file.filename, bytes=len(content))

    # Parse the bill
    bill: ParsedBill = parse_bill_csv(content)

    if bill.total_usd == 0:
        raise HTTPException(
            status_code=422,
            detail="Could not extract any cost data from the file. "
                   "Please upload an AWS Cost Explorer CSV, GCP Billing CSV, or Azure Cost Management export.",
        )

    # Generate savings report (Dify → GMI fallback)
    savings_report = await _build_savings_report(bill, gmi, dify, user_id)

    # Screen output and score quality on the summary text
    summary_text = savings_report.get("summary", "")
    if summary_text:
        output_check = await guard.screen_output(summary_text)
        savings_report["summary"] = output_check["filtered"]
        quality_score = await guard.score_quality(
            f"Cloud bill analysis for {bill.provider}, ${bill.total_usd:.2f}/mo",
            summary_text,
        )
        log.info("analyze.quality_score", score=quality_score)

    # Hardware recommendations
    hardware_recs = _recommend_hardware(bill.total_usd)

    # Persist to DB
    session_id = uuid.uuid4()
    db_session = AnalysisSession(
        id=session_id,
        user_id=user_id,
        status="complete",
        file_name=file.filename,
        file_key=f"uploads/{session_id}/{file.filename}",
    )
    db.add(db_session)
    await db.flush()

    spend_report = SpendReport(
        session_id=session_id,
        raw_spend={"rows": len(bill.raw_rows)},
        breakdown=bill.to_dict(),
        total_monthly_usd=bill.total_usd,
        savings_report=savings_report,
        hardware_recommendations=hardware_recs,
    )
    db.add(spend_report)
    await db.flush()

    log.info(
        "analyze.complete",
        session_id=str(session_id),
        provider=bill.provider,
        total_usd=bill.total_usd,
    )

    return UploadResponse(
        analysis_session_id=str(session_id),
        status="complete",
        provider=bill.provider,
        line_items=bill.line_items,
        total_usd=bill.total_usd,
        breakdown=bill.to_dict()["services"],
        savings_report=savings_report,
        hardware_recommendations=hardware_recs,
    )


@router.get("/sessions/{session_id}", response_model=UploadResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Retrieve a completed analysis session by ID."""
    from sqlalchemy import select

    stmt = select(AnalysisSession).where(AnalysisSession.id == uuid.UUID(session_id))
    result = await db.execute(stmt)
    db_session = result.scalar_one_or_none()

    if not db_session:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    if not db_session.spend_report:
        raise HTTPException(status_code=202, detail="Analysis still in progress.")

    report = db_session.spend_report
    return UploadResponse(
        analysis_session_id=str(db_session.id),
        status=db_session.status,
        provider=report.breakdown.get("provider", "unknown"),
        line_items=report.breakdown.get("line_items", 0),
        total_usd=report.total_monthly_usd,
        breakdown=report.breakdown.get("services", []),
        savings_report=report.savings_report,
        hardware_recommendations=report.hardware_recommendations,
    )
