from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.errors import NotFoundError
from app.repositories.memory import InMemoryClaimStore
from app.schemas.core import Claim, Receipt
from app.services.intake import IntakeService, parse_declared_amount

router = APIRouter(prefix="/claims", tags=["claims"])
store = InMemoryClaimStore()


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


def get_intake_service(settings: Settings = Depends(get_settings)) -> IntakeService:
    return IntakeService(store, settings)


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(
    employee_id: str = Form(...),
    currency: str = Form("IDR"),
    declared_amount: str | None = Form(None),
    files: list[UploadFile] = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    service: IntakeService = Depends(get_intake_service),
) -> ClaimResponse:
    claim, receipts, replay = await service.create_claim(
        employee_id=employee_id,
        currency=currency,
        declared_amount=parse_declared_amount(declared_amount),
        files=files,
        idempotency_key=idempotency_key,
    )
    return ClaimResponse(
        claim=claim,
        receipts=receipts,
        idempotent_replay=replay,
    )


@router.get("", response_model=ClaimListResponse)
def list_claims(
    employee_id: str | None = Query(None),
) -> ClaimListResponse:
    items = list(store.list(employee_id=employee_id))
    return ClaimListResponse(items=items, total=len(items))


@router.get("/{claim_id}", response_model=ClaimDetailResponse)
def get_claim(claim_id: UUID) -> ClaimDetailResponse:
    claim = store.get(claim_id)
    if claim is None:
        raise NotFoundError("Claim", str(claim_id))
    return ClaimDetailResponse(
        claim=claim,
        receipts=list(store.list_receipts(claim_id)),
    )
