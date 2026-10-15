"""Reporting endpoints for manager and admin views (FR-14)."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.api.auth import require_admin

from app.api.deps import (
    get_claim_repository,
    get_decision_repository,
    get_processing_run_repository,
    get_signal_repository,
)
from app.repositories.protocols import (
    ClaimRepository,
    DecisionRepository,
    ProcessingRunRepository,
    SignalRepository,
)

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


def _filtered_claims(
    claims: ClaimRepository,
    *,
    employee_id: str | None,
    period_from: date | None,
    period_to: date | None,
):
    items = claims.list(employee_id=employee_id)
    return [
        claim
        for claim in items
        if (period_from is None or claim.submitted_at.date() >= period_from)
        and (period_to is None or claim.submitted_at.date() <= period_to)
    ]


@router.get("/summary", response_model=ReportSummary)
def report_summary(
    period_from: date | None = Query(None),
    period_to: date | None = Query(None),
    employee_id: str | None = Query(None),
    claims: ClaimRepository = Depends(get_claim_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
    runs: ProcessingRunRepository = Depends(get_processing_run_repository),
    signals: SignalRepository = Depends(get_signal_repository),
) -> ReportSummary:
    items = _filtered_claims(
        claims,
        employee_id=employee_id,
        period_from=period_from,
        period_to=period_to,
    )
    decisions_by_claim = {claim.id: list(decisions.list_for_claim(claim.id)) for claim in items}
    runs_by_claim = {claim.id: list(runs.list_for_claim(claim.id)) for claim in items}
    durations = [
        int((run.completed_at - run.started_at).total_seconds() * 1000)
        for claim in items
        for run in runs_by_claim[claim.id]
        if run.started_at is not None and run.completed_at is not None
    ]
    signals_by_claim = {
        claim.id: list(signals.list_for_claim(claim.id)) for claim in items
    }
    duplicate_count = sum(
        signal.signal_type == "duplicate"
        for claim in items
        for signal in signals_by_claim[claim.id]
    )
    anomaly_count = sum(
        signal.signal_type == "anomaly"
        for claim in items
        for signal in signals_by_claim[claim.id]
    )
    manual_claims = sum(1 for claim in items if claim.status in ("escalated", "approved", "rejected") and any(
        decision.created_by == "reviewer" for decision in decisions_by_claim[claim.id]
    ))
    return ReportSummary(
        period_from=period_from,
        period_to=period_to,
        total_claims=len(items),
        approved_claims=sum(claim.status == "approved" for claim in items),
        rejected_claims=sum(claim.status == "rejected" for claim in items),
        pending_claims=sum(claim.status in ("received", "processing", "needs_clarification", "escalated") for claim in items),
        automated_claims=len(items) - manual_claims,
        manual_claims=manual_claims,
        duplicate_count=duplicate_count,
        anomaly_count=anomaly_count,
        average_duration_ms=round(sum(durations) / len(durations)) if durations else None,
        estimated_time_saved_minutes=max(0, (len(items) - manual_claims) * 5),
    )


@router.get("/claims.csv")
def export_claims_csv(
    period_from: date | None = Query(None),
    period_to: date | None = Query(None),
    employee_id: str | None = Query(None),
    claims: ClaimRepository = Depends(get_claim_repository),
):
    items = _filtered_claims(
        claims,
        employee_id=employee_id,
        period_from=period_from,
        period_to=period_to,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["claim_id", "employee_id", "submitted_at", "currency", "declared_amount", "status"])
    for claim in items:
        writer.writerow([
            claim.id,
            claim.employee_id,
            claim.submitted_at.isoformat(),
            claim.currency,
            str(claim.declared_amount) if claim.declared_amount is not None else "",
            claim.status,
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=claims-report.csv"},
    )
