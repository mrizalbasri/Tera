"""Claim timeline composition (FR-12).

The timeline is DERIVED from persisted records — receipts, runs, attempts,
extractions, findings, evaluations, signals, decisions, clarifications,
reviews, audit events — so it stays consistent with whatever storage backend
produced them. Entries are ordered deterministically, redacted (ids,
statuses, reason codes only — never receipt bytes or extracted payloads),
and explain why processing stopped or changed state.
"""

from datetime import datetime
from uuid import UUID

from app.errors import NotFoundError
from app.repositories.protocols import (
    AuditRepository,
    ClaimRepository,
    ClarificationRepository,
    DecisionRepository,
    ExtractionAttemptRepository,
    ExtractionRepository,
    PolicyEvaluationRepository,
    ProcessingRunRepository,
    ReceiptRepository,
    ReviewRepository,
    SignalRepository,
    ValidationFindingRepository,
)
from app.schemas.core import TimelineEntry

_EPOCH = datetime.min


class TimelineService:
    def __init__(
        self,
        claims: ClaimRepository,
        receipts: ReceiptRepository,
        runs: ProcessingRunRepository,
        attempts: ExtractionAttemptRepository,
        extractions: ExtractionRepository,
        findings: ValidationFindingRepository,
        evaluations: PolicyEvaluationRepository,
        decisions: DecisionRepository,
        clarifications: ClarificationRepository,
        reviews: ReviewRepository,
        signals: SignalRepository,
        audit: AuditRepository,
    ) -> None:
        self._claims = claims
        self._receipts = receipts
        self._runs = runs
        self._attempts = attempts
        self._extractions = extractions
        self._findings = findings
        self._evaluations = evaluations
        self._decisions = decisions
        self._clarifications = clarifications
        self._reviews = reviews
        self._signals = signals
        self._audit = audit

    def build(self, claim_id: UUID) -> list[TimelineEntry]:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        # (timestamp, kind_rank, insertion_index, fields)
        rows: list[tuple[datetime | None, int, int, dict]] = []
        counter = 0

        def add(
            timestamp: datetime | None,
            kind_rank: int,
            step_name: str,
            status: str,
            summary: str,
            *,
            run_id: UUID | None = None,
            duration_ms: int | None = None,
            error_code: str | None = None,
            detail: dict | None = None,
            related: dict | None = None,
        ) -> None:
            nonlocal counter
            counter += 1
            rows.append(
                (
                    timestamp,
                    kind_rank,
                    counter,
                    {
                        "timestamp": timestamp,
                        "step_name": step_name,
                        "status": status,
                        "summary": summary,
                        "processing_run_id": run_id,
                        "duration_ms": duration_ms,
                        "error_code": error_code,
                        "detail": detail or {},
                        "related_ids": {
                            key: str(value)
                            for key, value in (related or {}).items()
                            if value is not None
                        },
                    },
                )
            )

        receipts = list(self._receipts.list_for_claim(claim_id))
        add(
            claim.submitted_at,
            0,
            "claim.received",
            "completed",
            f"Claim submitted by {claim.employee_id} with {len(receipts)} receipt(s).",
            detail={
                "receipts": [
                    {
                        "receipt_id": str(receipt.id),
                        "filename": receipt.original_filename,
                        "media_type": receipt.media_type,
                        "content_hash": receipt.content_hash[:12],
                        "quality_score": str(receipt.quality_score),
                        "quality_findings": receipt.quality_findings,
                    }
                    for receipt in receipts
                ],
                "currency": claim.currency,
                "declared_amount": str(claim.declared_amount)
                if claim.declared_amount is not None
                else None,
            },
            related={"claim_id": str(claim.id)},
        )

        runs = list(self._runs.list_for_claim(claim_id))
        all_attempts = list(self._attempts.list_for_claim(claim_id))
        saved_extractions = list(
            self._extractions.list_for_receipts([receipt.id for receipt in receipts])
        )
        findings = list(self._findings.list_for_claim(claim_id))
        evaluations = list(self._evaluations.list_for_claim(claim_id))
        signals = list(self._signals.list_for_claim(claim_id))
        decisions = list(self._decisions.list_for_claim(claim_id))
        clarifications = list(self._clarifications.list_for_claim(claim_id))

        for index, run in enumerate(runs, start=1):
            add(
                run.started_at,
                1,
                "run.started",
                "completed",
                f"Run #{index} started (pipeline {run.pipeline_version}).",
                run_id=run.id,
            )
            for attempt in all_attempts:
                if attempt.processing_run_id != run.id:
                    continue
                if attempt.error_code:
                    add(
                        attempt.created_at,
                        2,
                        "extraction_attempt",
                        "failed",
                        f"Attempt {attempt.attempt} failed: {attempt.error_code}.",
                        run_id=run.id,
                        error_code=attempt.error_code,
                    )
                else:
                    add(
                        attempt.created_at,
                        2,
                        "extraction_attempt",
                        "completed",
                        f"Attempt {attempt.attempt} completed"
                        + (
                            f" after {attempt.preprocessing}."
                            if attempt.preprocessing
                            else "."
                        ),
                        run_id=run.id,
                        detail={
                            "confidence": {
                                field: str(value)
                                for field, value in attempt.confidence.items()
                            }
                        },
                    )
            for extraction in saved_extractions:
                if extraction.processing_run_id != run.id:
                    continue
                add(
                    run.started_at,
                    3,
                    "extraction",
                    "completed",
                    f"Extracted vendor '{extraction.vendor.value}' with total "
                    f"{extraction.total.value} {extraction.currency.value}.",
                    run_id=run.id,
                    detail={
                        "extraction_id": str(extraction.id),
                        "receipt_id": str(extraction.receipt_id),
                        "category": str(extraction.category.value),
                    },
                )
            for finding in findings:
                if finding.processing_run_id != run.id:
                    continue
                add(
                    run.started_at,
                    4,
                    "validation",
                    "passed" if finding.passed else "failed",
                    finding.explanation,
                    run_id=run.id,
                    error_code=None if finding.passed else finding.reason_code,
                    detail={
                        "rule_id": finding.rule_id,
                        "severity": str(finding.severity),
                    },
                )
            for evaluation in evaluations:
                if evaluation.processing_run_id != run.id:
                    continue
                add(
                    run.started_at,
                    5,
                    "policy",
                    "passed" if evaluation.passed else "failed",
                    evaluation.explanation,
                    run_id=run.id,
                    error_code=None if evaluation.passed else evaluation.reason_code,
                    detail={
                        "rule_id": evaluation.rule_id,
                        "policy_version": evaluation.policy_version,
                        "limit": str(evaluation.limit)
                        if evaluation.limit is not None
                        else None,
                    },
                )
            for signal in signals:
                if signal.processing_run_id != run.id:
                    continue
                add(
                    signal.created_at,
                    6,
                    f"signal.{signal.signal_type}",
                    str(signal.severity),
                    signal.explanation,
                    run_id=run.id,
                    detail={
                        "triggered_rules": signal.triggered_rules,
                        "detector_version": signal.detector_version,
                        "score": str(signal.score) if signal.score is not None else None,
                        "source": signal.evidence.get("source"),
                        "reason": signal.evidence.get("reason"),
                        "feature_version": signal.evidence.get("feature_version"),
                        "component_scores": signal.evidence.get("component_scores", {}),
                    },
                )
            for decision in decisions:
                if decision.processing_run_id != run.id:
                    continue
                add(
                    decision.created_at,
                    7,
                    "decision",
                    str(decision.outcome),
                    f"Decision by {decision.created_by}: "
                    + ", ".join(decision.reason_codes)
                    + ".",
                    run_id=run.id,
                    detail={"reason_codes": decision.reason_codes},
                    related={"decision_id": str(decision.id)},
                )
            for clarification in clarifications:
                if clarification.processing_run_id != run.id:
                    continue
                add(
                    clarification.created_at,
                    8,
                    "clarification",
                    str(clarification.status),
                    clarification.question,
                    run_id=run.id,
                    detail={"code": clarification.code, "fields": clarification.fields},
                )
                if clarification.answered_at is not None:
                    add(
                        clarification.answered_at,
                        8,
                        "clarification.answered",
                        "completed",
                        "The clarification received an answer; processing resumed.",
                        run_id=run.id,
                    )
            add(
                run.completed_at,
                9,
                "run.completed",
                str(run.status),
                f"Run #{index} finished as {run.status}."
                + (f" Error: {run.error_code}." if run.error_code else ""),
                run_id=run.id,
                duration_ms=int(
                    (run.completed_at - run.started_at).total_seconds() * 1000
                )
                if run.completed_at and run.started_at
                else None,
                error_code=run.error_code,
            )

        for review in self._reviews.list_for_claim(claim_id):
            add(
                review.created_at,
                10,
                "review.opened",
                str(review.status),
                "Claim routed to the human review queue.",
            )
            if review.decided_at is not None:
                add(
                    review.decided_at,
                    10,
                    "review.decided",
                    "completed",
                    f"Reviewer {review.reviewer_reference} chose {review.action}.",
                    detail={"reason": review.reason},
                )

        for event in self._audit.list_for_aggregate("claim", claim_id):
            add(
                event.timestamp,
                11,
                f"audit.{event.event_type}",
                "completed",
                f"{event.actor_type} recorded {event.event_type}.",
                run_id=event.processing_run_id,
                duration_ms=event.duration_ms,
                error_code=event.error_code,
                detail={"sequence": event.sequence_number, **{
                    key: value for key, value in event.safe_payload.items()
                }},
            )

        rows.sort(key=lambda row: (row[0] or _EPOCH, row[1], row[2]))
        return [
            TimelineEntry(sequence=position, **payload)
            for position, (_, _, _, payload) in enumerate(rows, start=1)
        ]
