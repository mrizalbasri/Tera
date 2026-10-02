from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import PurePath
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.domain.enums import ClaimStatus
from app.errors import ApplicationError, NotFoundError
from app.repositories.memory import InMemoryClaimStore
from app.schemas.core import Claim, Receipt

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": {b"\xff\xd8\xff"},
    "image/png": {b"\x89PNG\r\n\x1a\n"},
    "application/pdf": {b"%PDF-"},
}
MAX_FILENAME_LENGTH = 255


class IntakeService:
    def __init__(self, store: InMemoryClaimStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    async def create_claim(
        self,
        *,
        employee_id: str,
        currency: str,
        declared_amount: Decimal | None,
        files: list[UploadFile],
        idempotency_key: str | None,
    ) -> tuple[Claim, list[Receipt], bool]:
        employee_id = employee_id.strip()
        currency = currency.strip().upper()
        if not employee_id:
            raise ApplicationError("invalid_claim", "employee_id is required.", 422)
        if len(currency) != 3 or not currency.isalpha():
            raise ApplicationError(
                "invalid_claim", "currency must be a three-letter code.", 422
            )
        if not files:
            raise ApplicationError(
                "receipt_required", "At least one receipt is required.", 422
            )

        if idempotency_key:
            existing = self._store.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing, list(self._store.list_receipts(existing.id)), True

        prepared: list[tuple[UploadFile, bytes, str, float, list[str]]] = []
        seen_hashes: set[str] = set()
        for upload in files:
            content, media_type, content_hash, score, findings = (
                await self._prepare_receipt(upload, seen_hashes)
            )
            existing_claim_id = self._store.get_claim_by_content_hash(content_hash)
            if existing_claim_id:
                raise ApplicationError(
                    "duplicate_receipt",
                    "A receipt with the same content has already been submitted.",
                    409,
                    {"claim_id": str(existing_claim_id)},
                )
            seen_hashes.add(content_hash)
            prepared.append((upload, content, content_hash, score, findings))

        now = datetime.now(UTC)
        claim = Claim(
            id=uuid4(),
            employee_id=employee_id,
            status=ClaimStatus.RECEIVED,
            submitted_at=now,
            currency=currency,
            declared_amount=declared_amount,
            created_at=now,
            updated_at=now,
        )
        receipts: list[Receipt] = []
        self._store.save_claim(claim, idempotency_key=idempotency_key)
        for upload, _content, content_hash, score, findings in prepared:
            receipt = Receipt(
                id=uuid4(),
                claim_id=claim.id,
                original_filename=_safe_filename(upload.filename),
                media_type=upload.content_type or "application/octet-stream",
                storage_reference=f"memory://{claim.id}/{uuid4()}",
                content_hash=content_hash,
                quality_score=Decimal(str(score)),
                quality_findings=findings,
                created_at=now,
            )
            self._store.save_receipt(receipt, content=content)
            receipts.append(receipt)
        return claim, receipts, False

    async def _prepare_receipt(
        self, upload: UploadFile, seen_hashes: set[str]
    ) -> tuple[bytes, str, str, float, list[str]]:
        filename = _safe_filename(upload.filename)
        if not filename:
            raise ApplicationError("invalid_file", "A filename is required.", 422)
        if upload.content_type not in ALLOWED_MEDIA_TYPES:
            raise ApplicationError(
                "unsupported_media_type",
                "Only JPG, PNG, and PDF files are supported.",
                415,
            )
        content = await upload.read(self._settings.max_receipt_size_bytes + 1)
        if len(content) > self._settings.max_receipt_size_bytes:
            raise ApplicationError(
                "file_too_large",
                "Receipt exceeds the maximum allowed size.",
                413,
                {"max_bytes": self._settings.max_receipt_size_bytes},
            )
        if not content:
            raise ApplicationError("invalid_file", "Receipt file is empty.", 422)
        expected_signatures = ALLOWED_MEDIA_TYPES[upload.content_type]
        if not any(content.startswith(signature) for signature in expected_signatures):
            raise ApplicationError(
                "invalid_file",
                "Receipt content does not match its declared media type.",
                422,
            )
        content_hash = sha256(content).hexdigest()
        if content_hash in seen_hashes:
            raise ApplicationError(
                "duplicate_receipt",
                "The same receipt was uploaded more than once.",
                409,
            )
        findings: list[str] = []
        if upload.content_type.startswith("image/") and len(content) < 100:
            findings.append("image_may_be_unreadable")
        if upload.content_type == "application/pdf" and b"%%EOF" not in content:
            findings.append("pdf_metadata_incomplete")
        score = 0.5 if findings else 1.0
        return content, upload.content_type, content_hash, score, findings


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return ""
    name = PurePath(filename).name.strip()
    if not name or len(name) > MAX_FILENAME_LENGTH:
        return ""
    return name


def parse_declared_amount(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ApplicationError(
            "invalid_claim", "declared_amount must be a valid decimal.", 422
        ) from exc
    if amount <= 0:
        raise ApplicationError(
            "invalid_claim", "declared_amount must be greater than zero.", 422
        )
    return amount
