from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import PurePath
from uuid import uuid4

from app.audit.events import record_audit_event
from app.config import Settings
from app.domain.enums import ActorType, ClaimStatus
from app.errors import ApplicationError, ErrorCode
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    FileStorage,
    ReceiptQualityChecker,
    ReceiptRepository,
)
from app.schemas.core import Claim, Receipt

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": {b"\xff\xd8\xff"},
    "image/png": {b"\x89PNG\r\n\x1a\n"},
    "application/pdf": {b"%PDF-"},
}
MAX_FILENAME_LENGTH = 255


@dataclass(frozen=True)
class ReceiptUpload:
    """Transport-independent receipt input; the HTTP layer converts UploadFile."""

    filename: str | None
    media_type: str | None
    content: bytes


@dataclass(frozen=True)
class PreparedReceipt:
    filename: str
    media_type: str
    content: bytes
    content_hash: str
    quality_score: float
    quality_findings: list[str]


class IntakeService:
    def __init__(
        self,
        claims: ClaimRepository,
        receipts: ReceiptRepository,
        storage: FileStorage,
        quality: ReceiptQualityChecker,
        audit: AuditRepository,
        settings: Settings,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._storage = storage
        self._quality = quality
        self._audit = audit
        self._settings = settings

    def create_claim(
        self,
        *,
        employee_id: str,
        currency: str,
        declared_amount: Decimal | None,
        files: list[ReceiptUpload],
        idempotency_key: str | None,
    ) -> tuple[Claim, list[Receipt], bool]:
        employee_id = employee_id.strip()
        currency = currency.strip().upper()
        if not employee_id:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM, "employee_id is required.", 422
            )
        if len(currency) != 3 or not currency.isalpha():
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM, "currency must be a three-letter code.", 422
            )
        if not files:
            raise ApplicationError(
                ErrorCode.RECEIPT_REQUIRED, "At least one receipt is required.", 422
            )

        if idempotency_key:
            existing = self._claims.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing, list(self._receipts.list_for_claim(existing.id)), True

        prepared: list[PreparedReceipt] = []
        seen_hashes: set[str] = set()
        for upload in files:
            candidate = self._prepare_receipt(upload, seen_hashes)
            existing_claim_id = self._receipts.find_claim_id_by_content_hash(
                candidate.content_hash
            )
            if existing_claim_id:
                raise ApplicationError(
                    ErrorCode.DUPLICATE_RECEIPT,
                    "A receipt with the same content has already been submitted.",
                    409,
                    {"claim_id": str(existing_claim_id)},
                )
            seen_hashes.add(candidate.content_hash)
            prepared.append(candidate)

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
        self._claims.save(claim)
        receipts: list[Receipt] = []
        for candidate in prepared:
            reference = self._storage.put(
                candidate.content,
                filename=candidate.filename,
                media_type=candidate.media_type,
            )
            receipt = Receipt(
                id=uuid4(),
                claim_id=claim.id,
                original_filename=candidate.filename,
                media_type=candidate.media_type,
                storage_reference=reference,
                content_hash=candidate.content_hash,
                quality_score=Decimal(str(candidate.quality_score)),
                quality_findings=candidate.quality_findings,
                created_at=now,
            )
            self._receipts.save(receipt)
            receipts.append(receipt)
        record_audit_event(
            self._audit,
            aggregate_type="claim",
            aggregate_id=claim.id,
            event_type="claim.received",
            actor_type=ActorType.EMPLOYEE,
            safe_payload={
                "receipt_count": len(receipts),
                "media_types": [receipt.media_type for receipt in receipts],
            },
        )
        # Registered only after the claim and all receipts are stored so a
        # partial failure can never be replayed as a complete submission.
        if idempotency_key:
            self._claims.register_idempotency_key(idempotency_key, claim.id)
        return claim, receipts, False

    def _prepare_receipt(
        self, upload: ReceiptUpload, seen_hashes: set[str]
    ) -> PreparedReceipt:
        filename = _safe_filename(upload.filename)
        if not filename:
            raise ApplicationError(
                ErrorCode.INVALID_FILE, "A filename is required.", 422
            )
        media_type = upload.media_type or ""
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise ApplicationError(
                ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                "Only JPG, PNG, and PDF files are supported.",
                415,
            )
        content = upload.content
        if len(content) > self._settings.max_receipt_size_bytes:
            raise ApplicationError(
                ErrorCode.FILE_TOO_LARGE,
                "Receipt exceeds the maximum allowed size.",
                413,
                {"max_bytes": self._settings.max_receipt_size_bytes},
            )
        if not content:
            raise ApplicationError(
                ErrorCode.INVALID_FILE, "Receipt file is empty.", 422
            )
        expected_signatures = ALLOWED_MEDIA_TYPES[media_type]
        if not any(content.startswith(signature) for signature in expected_signatures):
            raise ApplicationError(
                ErrorCode.INVALID_FILE,
                "Receipt content does not match its declared media type.",
                422,
            )
        content_hash = sha256(content).hexdigest()
        if content_hash in seen_hashes:
            raise ApplicationError(
                ErrorCode.DUPLICATE_RECEIPT,
                "The same receipt was uploaded more than once.",
                409,
            )
        score, findings = self._quality.check(content, media_type=media_type)
        return PreparedReceipt(
            filename=filename,
            media_type=media_type,
            content=content,
            content_hash=content_hash,
            quality_score=score,
            quality_findings=findings,
        )


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
            ErrorCode.INVALID_CLAIM, "declared_amount must be a valid decimal.", 422
        ) from exc
    if amount <= 0:
        raise ApplicationError(
            ErrorCode.INVALID_CLAIM,
            "declared_amount must be greater than zero.",
            422,
        )
    return amount
