"""One read model for amounts; never overwrite employee or OCR evidence."""

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from app.schemas.core import Claim, ClaimAmount, ExtractionResult, Receipt


def positive_amount(value: object) -> Decimal | None:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return amount if amount.is_finite() and amount > 0 else None


def resolve_amount(
    claim: Claim, receipts: Sequence[Receipt], extractions: Sequence[ExtractionResult],
) -> ClaimAmount:
    superseded = {receipt.replaces_receipt_id for receipt in receipts}
    active = [receipt for receipt in receipts if receipt.id not in superseded]
    latest = {}
    for extraction in sorted(extractions, key=lambda item: item.created_at):
        latest[extraction.receipt_id] = extraction
    values = []
    for receipt in active:
        extraction = latest.get(receipt.id)
        if extraction is None:
            break
        value = positive_amount(extraction.total.value)
        if value is None or extraction.total_ambiguous or str(extraction.currency.value).upper() != claim.currency:
            break
        values.append(value)
    extracted = sum(values, Decimal("0")) if active and len(values) == len(active) else None
    declared = positive_amount(claim.declared_amount)
    final = positive_amount(claim.final_amount)
    conflict = extracted is not None and declared is not None and extracted != declared
    if final is not None:
        return ClaimAmount(value=final, source="final", complete=True, conflict=conflict)
    if extracted is not None:
        return ClaimAmount(value=extracted, source="extraction", complete=True, conflict=conflict)
    if declared is not None:
        return ClaimAmount(value=declared, source="declared", complete=False)
    return ClaimAmount()


class ClaimAmountService:
    def __init__(self, receipts, extractions):
        self.receipts = receipts
        self.extractions = extractions

    def present_many(self, claims: Sequence[Claim]) -> list[Claim]:
        receipts = list(self.receipts.list_for_claims([claim.id for claim in claims]))
        extractions = list(self.extractions.list_for_receipts([receipt.id for receipt in receipts]))
        by_claim = {}
        by_receipt = {}
        for receipt in receipts:
            by_claim.setdefault(receipt.claim_id, []).append(receipt)
        for extraction in extractions:
            by_receipt.setdefault(extraction.receipt_id, []).append(extraction)
        return [
            claim.model_copy(update={"amount": resolve_amount(
                claim, by_claim.get(claim.id, []),
                [item for receipt in by_claim.get(claim.id, []) for item in by_receipt.get(receipt.id, [])],
            )}) for claim in claims
        ]

    def present(self, claim: Claim) -> Claim:
        return self.present_many([claim])[0]
