"""Claim orchestration. Checkpoints contain references, never receipt content.

SQL node transactions and completion markers support crash recovery. Domain
repositories remain the source of truth; completed requests replay their records.
"""

import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langgraph.types import Command

from app.agent.nodes import ClaimNodes
from app.agent.runtime import GraphResources
from app.agent.state import ClaimGraphState, ReviewExecution
from app.agent.workflow import build_claim_workflow
from app.domain.enums import ClaimStatus, ProcessingRunStatus
from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.repositories.protocols import ClaimRepository, ProcessingRunRepository
from app.schemas.core import Claim, Decision, ProcessingOutcome, ProcessingRun, Review
from app.services.extraction import ExtractionService, PIPELINE_VERSION

logger = logging.getLogger(__name__)


class ClaimProcessingService:
    """Application entry point for processing, replay, and human-input resume."""

    def __init__(
        self,
        claims: ClaimRepository,
        runs: ProcessingRunRepository,
        extraction: ExtractionService,
        *,
        graph_resources: GraphResources,
        max_recovery_attempts: int = 3,
    ) -> None:
        self._claims = claims
        self._runs = runs
        self._extraction = extraction
        self.resources = graph_resources
        self._max_recovery_attempts = max_recovery_attempts
        self.graph = build_claim_workflow(
            ClaimNodes(claims, runs, extraction), graph_resources.saver, graph_resources,
        )

    def claim_lock(self, claim_id: UUID) -> AbstractContextManager[None]:
        return self.resources.claim_lock(claim_id)

    @staticmethod
    def _config(claim_id: UUID) -> dict[str, Any]:
        return {"configurable": {"thread_id": str(claim_id)}}

    def process_claim(self, claim_id: UUID, *, resume: bool = False,
                      idempotency_key: str | None = None) -> ProcessingOutcome:
        with self.claim_lock(claim_id):
            run = self._runs.latest_for_claim(claim_id)
            if resume and run is not None and run.status in (ProcessingRunStatus.NEEDS_CLARIFICATION, ProcessingRunStatus.ESCALATED):
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Submit the required clarification or review input first.", 409)
            return self._process_claim(claim_id, idempotency_key=idempotency_key)

    def resume_clarification(self, claim_id: UUID) -> ProcessingOutcome:
        with self.claim_lock(claim_id):
            self._ensure_waiting(claim_id, "wait_clarification")
            run = self._runs.latest_for_claim(claim_id)
            if run is None or run.status != ProcessingRunStatus.QUEUED:
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Clarification answer has not queued a run.", 409)
            return self._execute_run(self._claims.get(claim_id), run)

    def queue_clarification(self, claim_id: UUID) -> ProcessingRun:
        """Called inside the transaction that records the clarification answer."""
        claim = self._claims.get(claim_id)
        run = self._runs.latest_for_claim(claim_id)
        if claim is None or claim.status != ClaimStatus.PROCESSING or run is None or run.status != ProcessingRunStatus.NEEDS_CLARIFICATION:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Claim is not ready for a clarification run.", 409)
        return self._runs.save(ProcessingRun(
            id=uuid4(), claim_id=claim_id, status=ProcessingRunStatus.QUEUED,
            pipeline_version=PIPELINE_VERSION, started_at=None,
            receipt_revision=claim.receipt_revision,
            retry_count=len(self._runs.list_for_claim(claim_id)),
        ))

    def ensure_clarification_waiting(self, claim_id: UUID) -> None:
        with self.claim_lock(claim_id):
            run = self._runs.latest_for_claim(claim_id)
            if run is None or run.status != ProcessingRunStatus.NEEDS_CLARIFICATION:
                raise ApplicationError(ErrorCode.INVALID_CLAIM, "Claim is not waiting for clarification.", 409)
            self._ensure_waiting(claim_id, "wait_clarification")

    def resume_review(
        self, claim_id: UUID, apply: Callable[[UUID], tuple[Claim, Decision, Review]],
    ) -> tuple[Claim, Decision, Review]:
        """The callback is request-local; only the new run ID enters resume state."""
        with self.claim_lock(claim_id):
            self._ensure_waiting(claim_id, "wait_review")
            now = datetime.now(UTC)
            run = self._runs.save(ProcessingRun(
                id=uuid4(), claim_id=claim_id, status=ProcessingRunStatus.RUNNING,
                pipeline_version=PIPELINE_VERSION, started_at=now,
                receipt_revision=self._claims.get(claim_id).receipt_revision,
                retry_count=len(self._runs.list_for_claim(claim_id)),
            ))
            execution = ReviewExecution(apply)
            self.graph.invoke(
                Command(resume={"run_id": str(run.id)}), self._config(claim_id),
                context=execution,
            )
            assert execution.result is not None
            return execution.result

    def _ensure_waiting(self, claim_id: UUID, stage: str) -> None:
        config = self._config(claim_id)
        snapshot = self.graph.get_state(config)
        if snapshot.next == (stage,):
            return
        # A terminal domain commit can precede its waiting checkpoint. Rebuild
        # only the interrupt; the completed business node must not run again.
        run = self._runs.latest_for_claim(claim_id)
        expected = (ProcessingRunStatus.NEEDS_CLARIFICATION if stage == "wait_clarification"
                    else ProcessingRunStatus.ESCALATED)
        if run is None or run.status != expected:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Claim is not waiting for this action.", 409)
        self.graph.invoke(self._state(claim_id, run.id, stage), config)

    @staticmethod
    def _state(claim_id: UUID, run_id: UUID, stage: str) -> ClaimGraphState:
        return {"claim_id": str(claim_id), "run_id": str(run_id),
                "pipeline_version": PIPELINE_VERSION, "stage": stage}

    def _execute_run(self, claim: Claim, run: ProcessingRun) -> ProcessingOutcome:
        config = self._config(claim.id)
        snapshot = self.graph.get_state(config)
        try:
            if snapshot.next == ("wait_clarification",):
                self.graph.invoke(Command(resume={"run_id": str(run.id)}), config)
            elif snapshot.next and snapshot.values.get("run_id") == str(run.id):
                self.graph.invoke(None, config)
            else:
                self.graph.invoke(self._state(claim.id, run.id, "extract"), config)
        except ApplicationError as exc:
            current = self._runs.get(run.id)
            if current.status in (ProcessingRunStatus.RUNNING, ProcessingRunStatus.QUEUED):
                with self.resources.transaction():
                    self._extraction.complete_run(current, ProcessingRunStatus.FAILED, [], error_code=exc.code)
            raise
        return self._extraction.replay(claim.id, self._runs.get(run.id))

    def recover_claim(self, claim_id: UUID) -> ProcessingOutcome | None:
        with self.resources.claim_lock(claim_id, timeout=0):
            run = self._runs.latest_for_claim(claim_id)
            claim = self._claims.get(claim_id)
            if claim is None or run is None or run.status not in (ProcessingRunStatus.RUNNING, ProcessingRunStatus.QUEUED):
                return None
            if run.recovery_count >= self._max_recovery_attempts:
                with self.resources.transaction():
                    self._extraction.complete_run(run, ProcessingRunStatus.FAILED, [], error_code="recovery_exhausted")
                raise ApplicationError("recovery_exhausted", "Processing could not be recovered; retry the claim.", 503)
            run = self._runs.save(run.model_copy(update={"recovery_count": run.recovery_count + 1}))
            if claim.status == ClaimStatus.ESCALATED:
                # Review callbacks are request-local. Rollback leaves the review
                # open, and only a fresh authenticated admin input may decide it.
                with self.resources.transaction():
                    self._extraction.complete_run(run, ProcessingRunStatus.FAILED, [], error_code="review_input_required")
                self.graph.invoke(self._state(claim.id, run.id, "wait_review"), self._config(claim.id))
                return self._extraction.replay(claim.id, self._runs.get(run.id))
            return self._execute_run(claim, run)

    def recover_pending(self, *, limit: int = 100) -> dict[str, int]:
        from app.services.operations import recover_pending

        return recover_pending(self, limit=limit)

    def pending_claim_ids(self, *, limit: int) -> Sequence[UUID]:
        return self._runs.pending_claim_ids(limit=limit)

    def get_checkpoint_detail(self, claim_id: UUID) -> dict[str, Any]:
        config = self._config(claim_id)
        snapshot = self.graph.get_state(config)
        history_snapshots = list(self.graph.get_state_history(config))
        claim = self._claims.get(claim_id)
        run = self._runs.latest_for_claim(claim_id)
        history = []
        for s in history_snapshots:
            history.append({
                "checkpoint_id": s.config.get("configurable", {}).get("checkpoint_id"),
                "stage": s.values.get("stage") if s.values else None,
                "next": list(s.next) if s.next else [],
                "step": s.metadata.get("step") if s.metadata else None,
                "source": s.metadata.get("source") if s.metadata else None,
                "created_at": s.created_at,
                "has_interrupts": bool(s.interrupts) if hasattr(s, "interrupts") else False,
            })
        return {
            "claim_id": str(claim_id),
            "status": claim.status if claim else "unknown",
            "run_status": run.status if run else None,
            "stage": snapshot.values.get("stage") if snapshot.values else None,
            "next_nodes": list(snapshot.next) if snapshot.next else [],
            "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
            "created_at": snapshot.created_at,
            "values": snapshot.values if snapshot.values else {},
            "history": history,
        }

    def list_checkpoints(self, *, limit: int = 50, stage_filter: str | None = None) -> list[dict[str, Any]]:
        claims = list(self._claims.list())
        claims.sort(key=lambda c: c.submitted_at, reverse=True)
        results = []
        for claim in claims[:limit]:
            config = self._config(claim.id)
            snapshot = self.graph.get_state(config)
            stage = snapshot.values.get("stage") if snapshot.values else None
            next_nodes = list(snapshot.next) if snapshot.next else []
            if stage_filter and stage != stage_filter:
                continue
            results.append({
                "claim_id": str(claim.id),
                "employee_id": claim.employee_id,
                "status": claim.status,
                "declared_amount": str(claim.declared_amount) if claim.declared_amount is not None else None,
                "currency": claim.currency,
                "submitted_at": claim.submitted_at.isoformat(),
                "stage": stage,
                "next_nodes": next_nodes,
                "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
                "created_at": snapshot.created_at,
            })
        return results

    def _process_claim(
        self,
        claim_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> ProcessingOutcome:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        run_key = f"run:{claim_id}:{idempotency_key}" if idempotency_key else None

        latest_run = self._runs.latest_for_claim(claim_id)
        new_receipt = latest_run is not None and claim.receipt_revision > latest_run.receipt_revision
        if latest_run is not None and latest_run.status in (ProcessingRunStatus.RUNNING, ProcessingRunStatus.QUEUED):
            return self.recover_claim(claim_id)
        if (
            latest_run is not None
            and not new_receipt
            and latest_run.status
            in (
                ProcessingRunStatus.SUCCEEDED,
                ProcessingRunStatus.NEEDS_CLARIFICATION,
                ProcessingRunStatus.ESCALATED,
            )
        ):
            # Repetition without new input replays the recorded run instead of
            # creating a conflicting one (M6 reliability rule).
            return self._extraction.replay(claim_id, latest_run)

        if run_key:
            keyed_run = self._runs.get_run_by_key(run_key)
            if keyed_run is not None:
                return self._keyed_result(claim_id, keyed_run)

        run_id = uuid4()
        current_status = ClaimStatus(claim.status)
        can_retry = (
            current_status is ClaimStatus.PROCESSING
            and latest_run is not None
            and (latest_run.status == ProcessingRunStatus.FAILED or new_receipt)
        )
        if current_status is not ClaimStatus.RECEIVED and not can_retry:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "Claim cannot be processed in its current state.",
                409,
            )

        run = ProcessingRun(
            id=run_id,
            claim_id=claim_id,
            status=ProcessingRunStatus.QUEUED,
            pipeline_version=PIPELINE_VERSION,
            receipt_revision=claim.receipt_revision,
            started_at=None,
            completed_at=None,
            retry_count=len(self._runs.list_for_claim(claim_id)),
            error_code=None,
        )
        with self.resources.transaction():
            if run_key and not self._runs.reserve_run_key(run_key, run_id):
                raise ApplicationError(ErrorCode.IDEMPOTENCY_IN_PROGRESS, "Processing request is in progress.", 409)
            self._runs.save(run)
            if current_status is ClaimStatus.RECEIVED:
                claim = self._extraction.transition_claim(claim, ClaimStatus.PROCESSING)
        logger.info("processing run %s queued for claim %s", run.id, claim_id)
        return self._execute_run(claim, run)

    def _keyed_result(self, claim_id: UUID, run: ProcessingRun) -> ProcessingOutcome:
        """Idempotent result for a keyed repeat: replay, or re-raise failures."""
        if run.status == ProcessingRunStatus.FAILED:
            raise ApplicationError(
                run.error_code or ErrorCode.MALFORMED_EXTRACTION,
                "Receipt extraction failed; please upload a clearer receipt.",
                502,
            )
        return self._extraction.replay(claim_id, run)
