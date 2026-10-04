from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import (
    get_claim_repository,
    get_clarification_repository,
    get_clarification_service,
    get_decision_repository,
    get_extraction_attempt_repository,
    get_extraction_repository,
    get_extraction_service,
    get_intake_service,
    get_policy_evaluation_repository,
    get_receipt_repository,
    get_signal_repository,
    get_timeline_service,
    get_validation_finding_repository,
)
from app.config import Settings, get_settings
from app.errors import NotFoundError
from app.repositories.protocols import (
    ClaimRepository,
    DecisionRepository,
    ExtractionAttemptRepository,
    ExtractionRepository,
    PolicyEvaluationRepository,
    ReceiptRepository,
    SignalRepository,
    ValidationFindingRepository,
)
from app.schemas.core import (
    Claim,
    Clarification,
    ClarificationRequest,
    Decision,
    ExtractionAttempt,
    ExtractionResult,
    PolicyEvaluation,
    Receipt,
    Signal,
    ValidationFinding,
)
from app.schemas.core import TimelineEntry
from app.services.clarification import ClarificationService
from app.services.timeline import TimelineService
from app.services.extraction import ExtractionService
from app.services.intake import IntakeService, ReceiptUpload, parse_declared_amount

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimResponse(BaseModel):
    claim: Claim
    receipts: list[Receipt]
    idempotent_replay: bool = False


class ClaimListResponse(BaseModel):
    items: list[Claim]
    total: int


class ClaimDetailResponse(BaseModel):
    claim: Claim
    receipts: list[Receipt]
    extractions: list[ExtractionResult] = []
    attempts: list[ExtractionAttempt] = []
    validation_findings: list[ValidationFinding] = []
    policy_evaluations: list[PolicyEvaluation] = []
    signals: list[Signal] = []
    decisions: list[Decision] = []


class ProcessClaimResponse(BaseModel):
    claim: Claim
    extractions: list[ExtractionResult]
    attempts: list[ExtractionAttempt]
    clarification: ClarificationRequest | None = None
    validation_findings: list[ValidationFinding] = []
    policy_evaluations: list[PolicyEvaluation] = []
    decision: Decision | None = None


class ClarificationListResponse(BaseModel):
    items: list[Clarification]
    total: int


class TimelineResponse(BaseModel):
    items: list[TimelineEntry]
    total: int


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)
    answered_by: str = Field(min_length=1, max_length=100)


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(
    employee_id: str = Form(...),
    currency: str = Form("IDR"),
    declared_amount: str | None = Form(None),
    files: list[UploadFile] = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    settings: Settings = Depends(get_settings),
    service: IntakeService = Depends(get_intake_service),
) -> ClaimResponse:
    uploads = [
        ReceiptUpload(
            filename=upload.filename,
            media_type=upload.content_type,
            content=await upload.read(settings.max_receipt_size_bytes + 1),
        )
        for upload in files
    ]
    claim, receipts, replay = service.create_claim(
        employee_id=employee_id,
        currency=currency,
        declared_amount=parse_declared_amount(declared_amount),
        files=uploads,
        idempotency_key=idempotency_key,
    )
    return ClaimResponse(claim=claim, receipts=receipts, idempotent_replay=replay)


@router.get("", response_model=ClaimListResponse)
def list_claims(
    employee_id: str | None = Query(None),
    claims: ClaimRepository = Depends(get_claim_repository),
) -> ClaimListResponse:
    items = list(claims.list(employee_id=employee_id))
    return ClaimListResponse(items=items, total=len(items))


@router.get("/{claim_id}", response_model=ClaimDetailResponse)
def get_claim(
    claim_id: UUID,
    claims: ClaimRepository = Depends(get_claim_repository),
    receipts: ReceiptRepository = Depends(get_receipt_repository),
    extractions: ExtractionRepository = Depends(get_extraction_repository),
    attempts: ExtractionAttemptRepository = Depends(get_extraction_attempt_repository),
    findings: ValidationFindingRepository = Depends(get_validation_finding_repository),
    evaluations: PolicyEvaluationRepository = Depends(get_policy_evaluation_repository),
    signals: SignalRepository = Depends(get_signal_repository),
    decisions: DecisionRepository = Depends(get_decision_repository),
) -> ClaimDetailResponse:
    claim = claims.get(claim_id)
    if claim is None:
        raise NotFoundError("Claim", str(claim_id))
    receipt_ids = [receipt.id for receipt in receipts.list_for_claim(claim_id)]
    return ClaimDetailResponse(
        claim=claim,
        receipts=list(receipts.list_for_claim(claim_id)),
        extractions=list(extractions.list_for_receipts(receipt_ids)),
        attempts=list(attempts.list_for_claim(claim_id)),
        validation_findings=list(findings.list_for_claim(claim_id)),
        policy_evaluations=list(evaluations.list_for_claim(claim_id)),
        signals=list(signals.list_for_claim(claim_id)),
        decisions=list(decisions.list_for_claim(claim_id)),
    )


@router.post("/{claim_id}/process", response_model=ProcessClaimResponse)
def process_claim(
    claim_id: UUID,
    service: ExtractionService = Depends(get_extraction_service),
) -> ProcessClaimResponse:
    outcome = service.process_claim(claim_id)
    return ProcessClaimResponse(
        claim=outcome.claim,
        extractions=outcome.extractions,
        attempts=outcome.attempts,
        clarification=outcome.clarification,
        validation_findings=outcome.validation_findings,
        policy_evaluations=outcome.policy_evaluations,
        decision=outcome.decision,
    )


@router.get("/{claim_id}/timeline", response_model=TimelineResponse)
def get_claim_timeline(
    claim_id: UUID,
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineResponse:
    items = service.build(claim_id)
    return TimelineResponse(items=items, total=len(items))


@router.get("/{claim_id}/clarifications", response_model=ClarificationListResponse)
def list_clarifications(
    claim_id: UUID,
    service: ClarificationService = Depends(get_clarification_service),
) -> ClarificationListResponse:
    items = service.list_for_claim(claim_id)
    return ClarificationListResponse(items=items, total=len(items))


@router.post(
    "/{claim_id}/clarifications/{clarification_id}/answer",
    response_model=ProcessClaimResponse,
)
def answer_clarification(
    claim_id: UUID,
    clarification_id: UUID,
    request: AnswerRequest,
    service: ClarificationService = Depends(get_clarification_service),
) -> ProcessClaimResponse:
    _clarification, outcome, _replayed = service.submit_answer(
        claim_id,
        clarification_id,
        answer=request.answer,
        answered_by=request.answered_by,
    )
    return ProcessClaimResponse(
        claim=outcome.claim,
        extractions=outcome.extractions,
        attempts=outcome.attempts,
        clarification=outcome.clarification,
        validation_findings=outcome.validation_findings,
        policy_evaluations=outcome.policy_evaluations,
        decision=outcome.decision,
    )
