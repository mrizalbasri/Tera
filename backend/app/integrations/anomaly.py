"""Deterministic rule-based anomaly scoring over employee history (FR-07).

Rules and weights (detector version ``rule-based-v1``):

- ``amount_spike``: total is at least 3x the average of prior claim totals
  (needs at least 3 prior claims) — +0.4
- ``high_frequency``: at least 3 prior claims within the last 7 days — +0.3
- ``repeated_amount``: at least 2 prior claims with the same declared
  amount — +0.3

Missing history yields a neutral score of 0, and the result is evidence for
the decision engine only — it can escalate, never approve.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums import Severity, SignalType
from app.schemas.core import Claim, Signal

AMOUNT_SPIKE_WEIGHT = Decimal("0.4")
HIGH_FREQUENCY_WEIGHT = Decimal("0.3")
REPEATED_AMOUNT_WEIGHT = Decimal("0.3")
AMOUNT_SPIKE_FACTOR = Decimal("3")
FREQUENCY_WINDOW_DAYS = 7
MIN_HISTORY_FOR_SPIKE = 3
MIN_REPEATED_AMOUNTS = 2
MIN_RECENT_CLAIMS = 3


class RuleBasedAnomalyScorer:
    version = "rule-based-v1"

    def score(
        self,
        *,
        claim: Claim,
        total: Decimal,
        history: Sequence[Claim],
        processing_run_id: UUID,
    ) -> Signal:
        triggered: list[str] = []
        evidence: dict[str, object] = {}
        score = Decimal("0")

        totals = [
            claim_total
            for prior in history
            if (claim_total := prior.declared_amount) is not None
        ]
        if not history:
            explanation = "No claim history exists for this employee."
        else:
            average = sum(totals, Decimal("0")) / len(totals) if totals else None
            if average is not None and len(totals) >= MIN_HISTORY_FOR_SPIKE:
                if total >= AMOUNT_SPIKE_FACTOR * average:
                    score += AMOUNT_SPIKE_WEIGHT
                    triggered.append("amount_spike")
                    evidence["average_prior_total"] = str(average)
                    evidence["claim_total"] = str(total)
            recent = [
                prior
                for prior in history
                if claim.submitted_at - prior.submitted_at
                <= timedelta(days=FREQUENCY_WINDOW_DAYS)
            ]
            if len(recent) >= MIN_RECENT_CLAIMS:
                score += HIGH_FREQUENCY_WEIGHT
                triggered.append("high_frequency")
                evidence["recent_claims"] = len(recent)
            same_amount = [
                prior
                for prior in history
                if prior.declared_amount is not None
                and prior.declared_amount == total
            ]
            if len(same_amount) >= MIN_REPEATED_AMOUNTS:
                score += REPEATED_AMOUNT_WEIGHT
                triggered.append("repeated_amount")
                evidence["prior_claims_with_same_amount"] = len(same_amount)
            explanation = (
                f"Anomaly rules triggered: {', '.join(triggered)}."
                if triggered
                else "Claim history shows no unusual pattern."
            )

        return Signal(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=processing_run_id,
            signal_type=SignalType.ANOMALY,
            severity=Severity.WARNING if score > 0 else Severity.INFO,
            confidence=None,
            match_type=None,
            matched_claim_ids=[],
            compared_fields=[],
            score=min(score, Decimal("1")),
            triggered_rules=triggered,
            evidence=evidence,
            detector_version=self.version,
            explanation=explanation,
            created_at=datetime.now(UTC),
        )
