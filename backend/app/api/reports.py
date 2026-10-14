"""Reporting endpoints for manager and admin views (FR-14)."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.auth import require_admin
from app.api.deps import get_claim_repository, get_decision_repository, get_processing_run_repository, get_signal_repository
from app.repositories.protocols import ClaimRepository, DecisionRepository, ProcessingRunRepository, SignalRepository
from app.repositories.query import ClaimFilter
from app.services.reporting import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


class ReportSummary(BaseModel):
    period_from: date | None
    period_to: date | None
    total_claims: int
    approved_claims: int
    rejected_claims: int
    pending_claims: int
    automated_claims: int
    manual_claims: int
    duplicate_count: int
    anomaly_count: int
    average_duration_ms: int | None
    estimated_time_saved_minutes: int


@router.get("/summary", response_model=ReportSummary)
def report_summary(
    period_from: date | None = Query(None), period_to: date | None = Query(None),
    employee_id: str | None = Query(None),
    claims: ClaimRepository = Depends(get_claim_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    runs: ProcessingRunRepository = Depends(get_processing_run_repository),
    signals: SignalRepository = Depends(get_signal_repository),
) -> ReportSummary:
    filters = ClaimFilter(employee_id=employee_id, period_from=period_from, period_to=period_to)
    return ReportSummary(**ReportingService(claims, decisions, runs, signals).summary(filters))


@router.get("/claims.csv")
def export_claims_csv(
    period_from: date | None = Query(None), period_to: date | None = Query(None),
    employee_id: str | None = Query(None), claims: ClaimRepository = Depends(get_claim_repository),
):
    filters = ClaimFilter(employee_id=employee_id, period_from=period_from, period_to=period_to)
    return StreamingResponse(ReportingService(claims).csv_rows(filters), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=claims-report.csv", "Cache-Control": "no-store"})
