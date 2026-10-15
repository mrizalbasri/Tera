from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.api.claim_access import ClaimActor, get_claim_actor, require_claim_access

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
from app.errors import ApplicationError, NotFoundError
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
from app.services.claim_visibility import employee_decision, employee_signal, employee_timeline
from app.services.processing import ClaimProcessingService
from app.services.intake import IntakeService, ReceiptUpload, parse_declared_amount

router = APIRouter(prefix="/claims", tags=["claims"], dependencies=[Depends(get_claim_actor)])


class ClaimResponse(BaseModel):
    claim: Claim
    receipts: list[Receipt]
    idempotent_replay: bool = False


class ReplacementReceiptResponse(BaseModel):
    claim: Claim
    receipt: Receipt


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
    answered_by: str | None = Field(default=None, min_length=1, max_length=100)


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(
    employee_id: str | None = Form(None),
    currency: str = Form("IDR"),
    declared_amount: str | None = Form(None),
    files: list[UploadFile] = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    settings: Settings = Depends(get_settings),
    actor: ClaimActor = Depends(get_claim_actor),
    service: IntakeService = Depends(get_intake_service),
) -> ClaimResponse:
    if len(files) > settings.max_receipts_per_claim:
        raise ApplicationError("too_many_receipts", "Too many receipts in one claim.", 422)
    uploads = []
    total_bytes = 0
    for upload in files:
        remaining = settings.max_upload_total_bytes - total_bytes
        content = await upload.read(min(settings.max_receipt_size_bytes, remaining) + 1)
        if len(content) > settings.max_receipt_size_bytes:
            raise ApplicationError("file_too_large", "Receipt exceeds the maximum allowed size.", 413,
                                   {"max_bytes": settings.max_receipt_size_bytes})
        total_bytes += len(content)
        if total_bytes > settings.max_upload_total_bytes:
            raise ApplicationError("upload_too_large", "Combined receipts exceed the upload limit.", 413)
        uploads.append(ReceiptUpload(upload.filename, upload.content_type, content))
    try:
        claim, receipts, replay = await run_in_threadpool(service.create_claim,
            employee_id=actor.employee_id(employee_id),
            currency=currency,
            declared_amount=parse_declared_amount(declared_amount),
            files=uploads,
            idempotency_key=actor.idempotency_key(idempotency_key, "create"),
        )
    except ApplicationError as exc:
        if not actor.admin and exc.code == "duplicate_receipt":
            raise ApplicationError(exc.code, "Nota ini sudah pernah diajukan.", exc.status_code) from exc
        raise
    return ClaimResponse(claim=claim, receipts=receipts, idempotent_replay=replay)


@router.post(
    "/{claim_id}/receipts",
    response_model=ReplacementReceiptResponse,
    status_code=201,
    dependencies=[Depends(require_claim_access)],
)
async def replace_claim_receipt(
    claim_id: UUID,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    actor: ClaimActor = Depends(get_claim_actor),
    service: IntakeService = Depends(get_intake_service),
) -> ReplacementReceiptResponse:
    claim, receipt = await run_in_threadpool(service.replace_receipt,
        claim_id=claim_id,
        upload=ReceiptUpload(
            filename=file.filename,
            media_type=file.content_type,
            content=await file.read(settings.max_receipt_size_bytes + 1),
        ),
    )
    return ReplacementReceiptResponse(claim=claim, receipt=receipt)


@router.get("", response_model=ClaimListResponse)
def list_claims(
    employee_id: str | None = Query(None),
    actor: ClaimActor = Depends(get_claim_actor),
    claims: ClaimRepository = Depends(get_claim_repository),
) -> ClaimListResponse:
    items = list(claims.list(employee_id=employee_id if actor.admin else actor.user_id))
    return ClaimListResponse(items=items, total=len(items))


@router.get("/{claim_id}", response_model=ClaimDetailResponse, dependencies=[Depends(require_claim_access)])
def get_claim(
    claim_id: UUID,
    actor: ClaimActor = Depends(get_claim_actor),
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
        signals=[signal if actor.admin else employee_signal(signal) for signal in signals.list_for_claim(claim_id)],
        decisions=[decision if actor.admin else employee_decision(decision) for decision in decisions.list_for_claim(claim_id)],
    )


@router.post("/{claim_id}/process", response_model=ProcessClaimResponse, dependencies=[Depends(require_claim_access)])
def process_claim(
    claim_id: UUID,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    resume: bool = Query(False),
    actor: ClaimActor = Depends(get_claim_actor),
    service: ClaimProcessingService = Depends(get_extraction_service),
) -> ProcessClaimResponse:
    outcome = service.process_claim(
        claim_id,
        resume=resume,
        idempotency_key=actor.idempotency_key(idempotency_key, f"process:{claim_id}"),
    )
    return ProcessClaimResponse(
        claim=outcome.claim,
        extractions=outcome.extractions,
        attempts=outcome.attempts,
        clarification=outcome.clarification,
        validation_findings=outcome.validation_findings,
        policy_evaluations=outcome.policy_evaluations,
        decision=outcome.decision if actor.admin else employee_decision(outcome.decision),
    )


@router.get("/{claim_id}/timeline", response_model=TimelineResponse, dependencies=[Depends(require_claim_access)])
def get_claim_timeline(
    claim_id: UUID,
    actor: ClaimActor = Depends(get_claim_actor),
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineResponse:
    items = [entry if actor.admin else employee_timeline(entry) for entry in service.build(claim_id)]
    return TimelineResponse(items=items, total=len(items))


@router.get("/{claim_id}/clarifications", response_model=ClarificationListResponse, dependencies=[Depends(require_claim_access)])
def list_clarifications(
    claim_id: UUID,
    service: ClarificationService = Depends(get_clarification_service),
) -> ClarificationListResponse:
    items = service.list_for_claim(claim_id)
    return ClarificationListResponse(items=items, total=len(items))


@router.post(
    "/{claim_id}/clarifications/{clarification_id}/answer",
    response_model=ProcessClaimResponse,
    dependencies=[Depends(require_claim_access)],
)
def answer_clarification(
    claim_id: UUID,
    clarification_id: UUID,
    request: AnswerRequest,
    actor: ClaimActor = Depends(get_claim_actor),
    service: ClarificationService = Depends(get_clarification_service),
) -> ProcessClaimResponse:
    _clarification, outcome, _replayed = service.submit_answer(
        claim_id,
        clarification_id,
        answer=request.answer,
        answered_by=(request.answered_by or actor.user_id) if actor.demo else actor.user_id,
    )
    return ProcessClaimResponse(
        claim=outcome.claim,
        extractions=outcome.extractions,
        attempts=outcome.attempts,
        clarification=outcome.clarification,
        validation_findings=outcome.validation_findings,
        policy_evaluations=outcome.policy_evaluations,
        decision=outcome.decision if actor.admin else employee_decision(outcome.decision),
    )
