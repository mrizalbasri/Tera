from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response

from app.api.auth import require_admin
from app.api.deps import get_claim_repository, get_processing_run_repository, get_extraction_service
from app.repositories.protocols import ClaimRepository, ProcessingRunRepository
from app.services.processing import ClaimProcessingService
from app.services.operations import processing_metrics

router = APIRouter(prefix="/operations", tags=["operations"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
def metrics(response: Response, claims: ClaimRepository = Depends(get_claim_repository),
            runs: ProcessingRunRepository = Depends(get_processing_run_repository)) -> dict[str, int | None]:
    response.headers["Cache-Control"] = "no-store"
    return processing_metrics(claims, runs)


@router.post("/recover")
def recover(limit: int = Query(100, ge=1, le=1000),
            processing: ClaimProcessingService = Depends(get_extraction_service)) -> dict[str, int]:
    return processing.recover_pending(limit=limit)


@router.get("/checkpoints")
def list_checkpoints(
    limit: int = Query(50, ge=1, le=200),
    stage: str | None = None,
    processing: ClaimProcessingService = Depends(get_extraction_service),
) -> list[dict[str, Any]]:
    return processing.list_checkpoints(limit=limit, stage_filter=stage)


@router.get("/checkpoints/{claim_id}")
def get_checkpoint(
    claim_id: UUID,
    processing: ClaimProcessingService = Depends(get_extraction_service),
) -> dict[str, Any]:
    return processing.get_checkpoint_detail(claim_id)


@router.post("/checkpoints/{claim_id}/resume")
def resume_checkpoint(
    claim_id: UUID,
    processing: ClaimProcessingService = Depends(get_extraction_service),
) -> dict[str, Any]:
    outcome = processing.recover_claim(claim_id)
    if outcome is None:
        return {"status": "noop", "claim_id": str(claim_id), "message": "Claim is not in a recoverable running/queued state."}
    return {
        "status": "resumed",
        "claim_id": str(claim_id),
        "outcome": outcome.claim.status,
    }
