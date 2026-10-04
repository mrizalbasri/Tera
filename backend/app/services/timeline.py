"""Claim timeline composition (FR-12).

The timeline is DERIVED from persisted records — runs, attempts, signals,
decisions, clarifications, reviews — so it stays consistent with whatever
storage backend produced them. Entries are ordered, redacted (ids, statuses,
reason codes only), and explain why processing stopped or changed state.
"""

from datetime import datetime
from uuid import UUID

from app.errors import NotFoundError
from app.repositories.protocols import (
    ClaimRepository,
    ClarificationRepository,
    DecisionRepository,
    ExtractionAttemptRepository,
    ProcessingRunRepository,
    ReviewRepository,
    SignalRepository,
)
from app.schemas.core import TimelineEntry


class TimelineService:
    def __init__(
        self,
        claims: ClaimRepository,
        runs: ProcessingRunRepository,
        attempts: ExtractionAttemptRepository,
        decisions: DecisionRepository,
        clarifications: ClarificationRepository,
        reviews: ReviewRepository,
        signals: SignalRepository,
    ) -> None:
        self._claims = claims
        self._runs = runs
        self._attempts = attempts
        self._decisions = decisions
        self._clarifications = clarifications
        self._reviews = reviews
        self._signals = signals

    def build(self, claim_id: UUID) -> list[TimelineEntry]:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        rows: list[tuple[datetime | None, dict]] = []

        def add(
            timestamp: datetime | None,
            step_name: str,
            status: str,
            summary: str,
            **related: str | None,
        ) -> None:
            rows.append(
                (
                    timestamp,
                    {
                        "timestamp": timestamp,
                        "step_name": step_name,
                        "status": status,
                        "summary": summary,
                        "related_ids": {
                            key: value
                            for key, value in related.items()
                            if value is not None
                        },
                    },
                )
            )

        add(
            claim.submitted_at,
            "claim.received",
            "completed",
            f"Claim submitted by {claim.employee_id}.",
            claim_id=str(claim.id),
        )

        runs = self._runs.list_for_claim(claim_id)
        for index, run in enumerate(runs, start=1):
            add(
                run.started_at,
                "run.started",
                "completed",
                f"Run #{index} started (pipeline {run.pipeline_version}).",
                run_id=str(run.id),
            )
            for attempt in self._attempts.list_for_claim(claim_id):
                if attempt.processing_run_id != run.id:
                    continue
                if attempt.error_code:
                    add(
                        attempt.created_at,
                        "extraction_attempt",
                        "failed",
                        f"Attempt {attempt.attempt} failed: {attempt.error_code}.",
                        run_id=str(run.id),
                    )
                else:
                    add(
                        attempt.created_at,
                        "extraction_attempt",
                        "completed",
                        f"Attempt {attempt.attempt} completed"
                        + (
                            f" after {attempt.preprocessing}."
                            if attempt.preprocessing
                            else "."
                        ),
                        run_id=str(run.id),
                    )
            for signal in self._signals.list_for_claim(claim_id):
                if signal.processing_run_id != run.id:
                    continue
                add(
                    signal.created_at,
                    f"signal.{signal.signal_type}",
                    str(signal.severity),
                    signal.explanation,
                    run_id=str(run.id),
                )
            for decision in self._decisions.list_for_claim(claim_id):
                if decision.processing_run_id != run.id:
                    continue
                add(
                    decision.created_at,
                    "decision",
                    str(decision.outcome),
                    f"Decision by {decision.created_by}: "
                    + ", ".join(decision.reason_codes)
                    + ".",
                    run_id=str(run.id),
                    decision_id=str(decision.id),
                )
            for clarification in self._clarifications.list_for_claim(claim_id):
                if clarification.processing_run_id != run.id:
                    continue
                add(
                    clarification.created_at,
                    "clarification",
                    str(clarification.status),
                    clarification.question,
                    run_id=str(run.id),
                )
                if clarification.answered_at is not None:
                    add(
                        clarification.answered_at,
                        "clarification.answered",
                        "completed",
                        "The clarification received an answer; processing resumed.",
                        run_id=str(run.id),
                    )
            add(
                run.completed_at,
                "run.completed",
                str(run.status),
                f"Run #{index} finished as {run.status}."
                + (f" Error: {run.error_code}." if run.error_code else ""),
                run_id=str(run.id),
            )

        for review in self._reviews.list_for_claim(claim_id):
            add(
                review.created_at,
                "review.opened",
                str(review.status),
                "Claim routed to the human review queue.",
            )
            if review.decided_at is not None:
                add(
                    review.decided_at,
                    "review.decided",
                    "completed",
                    f"Reviewer {review.reviewer_reference} chose {review.action}.",
                )

        rows.sort(key=lambda row: (row[0] is not None, row[0] or datetime.min))
        return [
            TimelineEntry(sequence=position, **payload)
            for position, (_, payload) in enumerate(rows, start=1)
        ]
