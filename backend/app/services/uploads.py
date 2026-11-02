from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.errors import ApplicationError
from app.schemas.core import Claim, Receipt
from app.services.intake import IntakeService, ReceiptUpload, parse_declared_amount


class IncomingReceipt(Protocol):
    @property
    def filename(self) -> str | None: ...

    @property
    def content_type(self) -> str | None: ...

    async def read(self, size: int = -1) -> bytes: ...


class ReceiptUploadService:
    def __init__(self, intake: IntakeService, settings: Settings) -> None:
        self._intake = intake
        self._settings = settings

    async def _read_uploads(self, files: Sequence[IncomingReceipt]) -> list[ReceiptUpload]:
        if len(files) > self._settings.max_receipts_per_claim:
            raise ApplicationError("too_many_receipts", "Too many receipts in one claim.", 422)
        uploads: list[ReceiptUpload] = []
        total_bytes = 0
        for upload in files:
            remaining = self._settings.max_upload_total_bytes - total_bytes
            content = await upload.read(min(self._settings.max_receipt_size_bytes, remaining) + 1)
            if len(content) > self._settings.max_receipt_size_bytes:
                raise ApplicationError("file_too_large", "Receipt exceeds the maximum allowed size.", 413,
                                       {"max_bytes": self._settings.max_receipt_size_bytes})
            total_bytes += len(content)
            if total_bytes > self._settings.max_upload_total_bytes:
                raise ApplicationError("upload_too_large", "Combined receipts exceed the upload limit.", 413)
            uploads.append(ReceiptUpload(upload.filename, upload.content_type, content))
        return uploads

    async def create_claim(
        self, *, employee_id: str, currency: str, declared_amount: str | None,
        files: Sequence[IncomingReceipt], idempotency_key: str | None,
        hide_duplicate_details: bool = False,
    ) -> tuple[Claim, list[Receipt], bool]:
        uploads = await self._read_uploads(files)
        try:
            return await run_in_threadpool(
                self._intake.create_claim,
                employee_id=employee_id,
                currency=currency,
                declared_amount=parse_declared_amount(declared_amount),
                files=uploads,
                idempotency_key=idempotency_key,
            )
        except ApplicationError as exc:
            if hide_duplicate_details and exc.code == "duplicate_receipt":
                raise ApplicationError(exc.code, "Nota ini sudah pernah diajukan.", exc.status_code) from exc
            raise

    async def replace_receipt(self, *, claim_id: UUID, file: IncomingReceipt) -> tuple[Claim, Receipt]:
        uploads = await self._read_uploads([file])
        return await run_in_threadpool(self._intake.replace_receipt, claim_id=claim_id, upload=uploads[0])
