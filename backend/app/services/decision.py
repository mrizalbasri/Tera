"""Conservative decision precedence per FR-08.

1. Blocking validation findings (invalid/missing data) -> needs_clarification.
2. A duplicate signal -> rejected.
3. A blocking policy violation -> rejected.
4. High anomaly, low confidence, or amount above the escalation threshold
   -> escalated.
5. Otherwise -> approved.

A provider can never set a final decision; this engine is the only writer.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.config import Settings
from app.domain.enums import ActorType, DecisionOutcome, Severity, SignalType
from app.schemas.core import (
    Claim,
    Decision,
    PolicyEvaluation,
    Signal,
    ValidationFinding,
)


class DecisionEngine:
    version = "decision-v1"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def decide(
        self,
        *,
        claim: Claim,
        total: Decimal,
        confidence: Decimal | None,
        findings: list[ValidationFinding],
        evaluations: list[PolicyEvaluation],
        signals: list[Signal],
        policy_version: int | None,
        processing_run_id: UUID,
        answered_codes: set[str] | None = None,
    ) -> Decision:
        blocking_findings = [
            finding
            for finding in findings
            if not finding.passed and finding.severity == Severity.BLOCKING
        ]
        duplicate_signals = [
            signal for signal in signals if signal.signal_type == SignalType.DUPLICATE
        ]
        policy_violations = [
            evaluation
            for evaluation in evaluations
            if not evaluation.passed and evaluation.severity == Severity.BLOCKING
        ]
        blocking_violations = [
            evaluation for evaluation in policy_violations if not evaluation.clarifiable
        ]
        clarifiable_violations = [
            evaluation for evaluation in policy_violations if evaluation.clarifiable
        ]
        anomaly = next(
            (signal for signal in signals if signal.signal_type == SignalType.ANOMALY),
            None,
        )
        anomaly_score = anomaly.score if anomaly is not None else None

        if blocking_findings:
            outcome = DecisionOutcome.NEEDS_CLARIFICATION
            reason_codes = [
                finding.reason_code or finding.rule_id
                for finding in blocking_findings
            ]
            explanation = (
                "Claim data needs correction before it can be decided: "
                + "; ".join(sorted(reason_codes))
                + "."
            )
        elif duplicate_signals:
            outcome = DecisionOutcome.REJECTED
            reason_codes = ["duplicate_receipt"]
            explanation = "; ".join(signal.explanation for signal in duplicate_signals)
        elif blocking_violations:
            outcome = DecisionOutcome.REJECTED
            reason_codes = [
                evaluation.reason_code or evaluation.rule_id
                for evaluation in blocking_violations
            ]
            explanation = (
                "Claim rejected by policy: "
                + "; ".join(
                    evaluation.explanation for evaluation in blocking_violations
                )
            )
        elif clarifiable_violations:
            answered = answered_codes or set()
            pending = [
                evaluation
                for evaluation in clarifiable_violations
                if self._clarification_code(evaluation) not in answered
            ]
            if pending:
                outcome = DecisionOutcome.NEEDS_CLARIFICATION
                reason_codes = [
                    self._clarification_code(evaluation) for evaluation in pending
                ]
                explanation = (
                    pending[0].explanation + " Please answer the clarification."
                )
            else:
                outcome = DecisionOutcome.REJECTED
                reason_codes = [
                    evaluation.reason_code or evaluation.rule_id
                    for evaluation in clarifiable_violations
                ]
                explanation = (
                    "Claim still fails policy after clarification: "
                    + "; ".join(
                        evaluation.explanation
                        for evaluation in clarifiable_violations
                    )
                )
        else:
            escalation_reasons = self._escalation_reasons(
                total, confidence, anomaly_score
            )
            if escalation_reasons:
                outcome = DecisionOutcome.ESCALATED
                reason_codes = escalation_reasons
                explanation = (
                    "Claim escalated for human review: "
                    + "; ".join(escalation_reasons)
                    + "."
                )
            else:
                outcome = DecisionOutcome.APPROVED
                reason_codes = ["within_policy", "confidence_sufficient"]
                explanation = (
                    "Claim passed validation, policy, duplicate, and anomaly "
                    "checks and is within the auto-approve limit."
                )

        return Decision(
            id=uuid4(),
            claim_id=claim.id,
            processing_run_id=processing_run_id,
            outcome=outcome,
            reason_codes=reason_codes,
            explanation=explanation[:2000],
            confidence=confidence,
            anomaly_score=anomaly_score,
            source_signal_ids=[signal.id for signal in signals],
            policy_version=policy_version,
            created_by=ActorType.AGENT,
            created_at=datetime.now(UTC),
        )

    def _clarification_code(self, evaluation: PolicyEvaluation) -> str:
        """Map a clarifiable violation to the clarification it should raise."""
        if evaluation.rule_type == "evidence_required":
            return "business_trip_evidence_required"
        return "participant_count_required"

    def _escalation_reasons(
        self,
        total: Decimal,
        confidence: Decimal | None,
        anomaly_score: Decimal | None,
    ) -> list[str]:
        reasons: list[str] = []
        if total > Decimal(str(self._settings.escalation_amount_threshold)):
            reasons.append("escalation_amount_threshold")
        if (
            confidence is not None
            and confidence < Decimal(str(self._settings.auto_approve_min_confidence))
        ):
            reasons.append("confidence_below_auto_approve")
        if (
            anomaly_score is not None
            and anomaly_score
            >= Decimal(str(self._settings.anomaly_escalation_threshold))
        ):
            reasons.append("anomaly_score_high")
        return reasons
