from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.schemas.core import Claim, ExtractionResult, FieldConfidence, Receipt
from app.services.claim_amounts import resolve_amount


def evidence(value="75000", *, currency="IDR"):
    now = datetime.now(UTC)
    claim = Claim(id=uuid4(), employee_id="synthetic", currency="IDR",
                  submitted_at=now, created_at=now, updated_at=now)
    receipt = Receipt(id=uuid4(), claim_id=claim.id, original_filename="synthetic.pdf",
                      media_type="application/pdf", storage_reference="synthetic",
                      content_hash="a" * 64, created_at=now)
    field = lambda value: FieldConfidence(value=value, confidence=Decimal("0.95"))
    extraction = ExtractionResult(
        id=uuid4(), receipt_id=receipt.id, vendor=field("Synthetic store"),
        receipt_date=field(now.date().isoformat()), total=field(value),
        currency=field(currency), category=field("meals"), provider="mock", created_at=now,
    )
    return claim, receipt, extraction


def test_ocr_amount_does_not_require_declared_amount():
    claim, receipt, extraction = evidence()
    amount = resolve_amount(claim, [receipt], [extraction])
    assert amount.value == Decimal("75000")
    assert amount.source == "extraction"
    assert claim.declared_amount is None


def test_latest_extraction_is_not_double_counted():
    claim, receipt, extraction = evidence()
    latest = extraction.model_copy(update={"id": uuid4(), "total": FieldConfidence(value="80000", confidence=".9")})
    assert resolve_amount(claim, [receipt], [extraction, latest]).value == Decimal("80000")


def test_replacement_excludes_old_receipt():
    claim, receipt, extraction = evidence()
    replacement = receipt.model_copy(update={"id": uuid4(), "replaces_receipt_id": receipt.id})
    new_extraction = extraction.model_copy(update={"id": uuid4(), "receipt_id": replacement.id})
    assert resolve_amount(claim, [receipt, replacement], [extraction, new_extraction]).value == Decimal("75000")


def test_partial_multi_receipt_is_not_a_complete_total():
    claim, receipt, extraction = evidence()
    other = receipt.model_copy(update={"id": uuid4()})
    amount = resolve_amount(claim, [receipt, other], [extraction])
    assert amount.value is None
    assert not amount.complete


def test_missing_amount_is_not_zero():
    claim, receipt, _ = evidence()
    assert resolve_amount(claim, [receipt], []).value is None


def test_malformed_or_wrong_currency_is_not_used():
    for value, currency in [("NaN", "IDR"), ("Infinity", "IDR"), ("-1", "IDR"), ("0", "IDR"), ("100", "USD")]:
        claim, receipt, extraction = evidence(value, currency=currency)
        assert resolve_amount(claim, [receipt], [extraction]).value is None


def test_declared_amount_is_marked_unverified_and_conflicts_are_visible():
    claim, receipt, extraction = evidence()
    claim = claim.model_copy(update={"declared_amount": Decimal("90000")})
    amount = resolve_amount(claim, [receipt], [extraction])
    assert amount.value == Decimal("75000")
    assert amount.conflict
    fallback = resolve_amount(claim, [receipt], [])
    assert fallback.source == "declared"
    assert not fallback.complete
