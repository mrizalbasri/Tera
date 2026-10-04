"""Duplicate detection over prior claims (FR-06).

Exact matches use receipt content hashes; likely matches compare vendor,
receipt date, and total. Evidence always names the matched claims and the
compared fields so a reviewer can verify the call.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums import DuplicateMatchType, Severity, SignalType
from app.repositories.protocols import (
    ClaimHistoryRepository,
    ExtractionRepository,
    ReceiptRepository,
)
from app.schemas.core import Claim, ExtractionResult, Receipt, Signal

LIKELY_MATCH_CONFIDENCE = Decimal("0.9")
EXACT_MATCH_CONFIDENCE = Decimal("1.0")


class AttributeDuplicateDetector:
    version = "attributes-v1"

    def __init__(
        self,
        history: ClaimHistoryRepository,
        receipts: ReceiptRepository,
        extractions: ExtractionRepository,
    ) -> None:
        self._history = history
        self._receipts = receipts
        self._extractions = extractions

    def find_matches(
        self,
        *,
        claim: Claim,
        receipts: Sequence[Receipt],
        processing_run_id: UUID,
    ) -> list[Signal]:
        signals: list[Signal] = []
        signals.extend(self._exact_matches(claim, receipts, processing_run_id))
        signals.extend(self._likely_matches(claim, receipts, processing_run_id))
        return signals

    def _exact_matches(
        self, claim: Claim, receipts: Sequence[Receipt], run_id: UUID
    ) -> list[Signal]:
        signals: list[Signal] = []
        for receipt in receipts:
            matched = self._receipts.find_claim_id_by_content_hash(
                receipt.content_hash
            )
            if matched is None or matched == claim.id:
                continue
            signals.append(
                self._signal(
                    claim=claim,
                    run_id=run_id,
                    match_type=DuplicateMatchType.EXACT_HASH,
                    confidence=EXACT_MATCH_CONFIDENCE,
                    matched_claim_ids=[matched],
                    compared_fields=["content_hash"],
                    evidence={"receipt_id": str(receipt.id)},
                    explanation=(
                        f"Receipt content hash matches a receipt of claim {matched}."
                    ),
                )
            )
        return signals

    def _likely_matches(
        self, claim: Claim, receipts: Sequence[Receipt], run_id: UUID
    ) -> list[Signal]:
        own = list(self._extractions.list_for_receipts([r.id for r in receipts]))
        if not own:
            return []
        signals: list[Signal] = []
        seen_claims: set[UUID] = set()
        for own_result in own:
            # Vendor history (FR-15) scopes the candidate set; the remaining
            # attributes must also match before a signal is raised.
            candidates = self._history.list_for_vendor(
                str(own_result.vendor.value), exclude_claim_id=claim.id
            )
            for other in candidates:
                if other.id in seen_claims:
                    continue
                other_receipts = self._receipts.list_for_claim(other.id)
                for other_result in self._extractions.list_for_receipts(
                    [r.id for r in other_receipts]
                ):
                    if not self._attributes_match(own_result, other_result):
                        continue
                    seen_claims.add(other.id)
                    signals.append(
                        self._signal(
                            claim=claim,
                            run_id=run_id,
                            match_type=DuplicateMatchType.LIKELY_ATTRIBUTES,
                            confidence=LIKELY_MATCH_CONFIDENCE,
                            matched_claim_ids=[other.id],
                            compared_fields=["vendor", "receipt_date", "total"],
                            evidence={
                                "other_claim_id": str(other.id),
                                "vendor": str(other_result.vendor.value),
                                "receipt_date": str(other_result.receipt_date.value),
                                "total": str(other_result.total.value),
                            },
                            explanation=(
                                f"Same vendor, receipt date, and total as claim "
                                f"{other.id}."
                            ),
                        )
                    )
                    break
        return signals

    @staticmethod
    def _attributes_match(
        own: ExtractionResult, other: ExtractionResult
    ) -> bool:
        return (
            own.vendor.value == other.vendor.value
            and own.receipt_date.value == other.receipt_date.value
            and own.total.value == other.total.value
        )

    def _signal(
        self,
        *,
        claim: Claim,
        run_id: UUID,
        match_type: DuplicateMatchType,
        confidence: Decimal,
        matched_claim_ids: list[UUID],
        compared_fields: list[str],
        evidence: dict[str, object],
        explanation: str,
    ) -> Signal:
        return Signal(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=run_id,
            signal_type=SignalType.DUPLICATE,
            severity=Severity.BLOCKING,
            confidence=confidence,
            match_type=match_type,
            matched_claim_ids=matched_claim_ids,
            compared_fields=compared_fields,
            score=None,
            triggered_rules=["duplicate_detected"],
            evidence=evidence,
            detector_version=self.version,
            explanation=explanation,
            created_at=datetime.now(UTC),
        )
