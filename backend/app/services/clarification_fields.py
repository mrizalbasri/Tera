"""Validate employee confirmations without pretending they are OCR evidence."""

from datetime import date

from app.errors import ApplicationError, ErrorCode
from app.services.claim_amounts import positive_amount

FIELD_LABELS = {
    "vendor": "Nama toko", "receipt_date": "Tanggal nota", "total": "Nominal nota",
    "currency": "Mata uang", "category": "Kategori",
}


def validate_confirmations(fields: list[str], values: dict[str, str]) -> dict[str, str]:
    expected = set(fields) & FIELD_LABELS.keys()
    if set(values) != expected:
        raise ApplicationError(ErrorCode.INVALID_CLAIM, "Lengkapi seluruh isian yang diminta, tanpa menambahkan field lain.", 422)
    cleaned = {}
    for field, raw in values.items():
        value = raw.strip()
        if not value or len(value) > 255:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, f"{FIELD_LABELS[field]} wajib diisi (maksimal 255 karakter).", 422)
        if field == "receipt_date":
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Tanggal nota harus berformat YYYY-MM-DD.", 422) from None
            if parsed.isoformat() != value or parsed > date.today():
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Tanggal nota tidak valid atau berada di masa depan.", 422)
        if field == "total":
            amount = positive_amount(value)
            if amount is None:
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Nominal nota harus berupa angka positif tanpa pemisah ribuan.", 422)
            value = str(amount)
        if field == "currency" and value.upper() != "IDR":
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Mata uang klaim harus IDR.", 422)
        if field == "category":
            from app.services.validation import SUPPORTED_CATEGORIES
            if value not in SUPPORTED_CATEGORIES:
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Pilih kategori pengeluaran yang didukung.", 422)
        cleaned[field] = value
    return cleaned
