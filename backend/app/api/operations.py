from fastapi import APIRouter, Depends, Query, Response

from app.api.auth import require_admin
from app.api.deps import get_claim_repository, get_processing_run_repository, get_extraction_service
from app.repositories.protocols import ClaimRepository, ProcessingRunRepository
from app.services.processing import ClaimProcessingService
from app.services.operations import processing_metrics

router = APIRouter(prefix="/operations", tags=["operations"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
def metrics(response: Response, claims: ClaimRepository = Depends(get_claim_repository),
            runs: ProcessingRunRepository = Depends(get_processing_run_repository)):
    response.headers["Cache-Control"] = "no-store"
    return processing_metrics(claims, runs)


@router.post("/recover")
def recover(limit: int = Query(100, ge=1, le=1000),
            processing: ClaimProcessingService = Depends(get_extraction_service)):
    return processing.recover_pending(limit=limit)
