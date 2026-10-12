"""Claim orchestration. Checkpoints contain references, never receipt content.

Only waiting checkpoints support restart/resume. Domain repositories remain
the source of truth; completed requests replay without executing graph nodes.
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
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
    ) -> None:
        self._claims = claims
        self._runs = runs
        self._extraction = extraction
        self.resources = graph_resources
        self.graph = build_claim_workflow(
            ClaimNodes(claims, runs, extraction), graph_resources.saver,
        )

    def claim_lock(self, claim_id: UUID):
        return self.resources.claim_lock(claim_id)

    @staticmethod
    def _config(claim_id: UUID) -> dict:
        return {"configurable": {"thread_id": str(claim_id)}}

    def process_claim(self, claim_id: UUID, *, resume: bool = False,
                      idempotency_key: str | None = None) -> ProcessingOutcome:
        with self.claim_lock(claim_id):
            return self._process_claim(claim_id, resume=resume, idempotency_key=idempotency_key)

    def resume_clarification(self, claim_id: UUID) -> ProcessingOutcome:
        with self.claim_lock(claim_id):
            self._ensure_waiting(claim_id, "wait_clarification")
            return self._process_claim(claim_id, resume=True)

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
        if snapshot.next:
            if snapshot.next != (stage,):
                raise ApplicationError(ErrorCode.INVALID_CLAIM,
                                       "Claim is not waiting for this action.", 409)
            return
        # Compatibility with M7 claims created before checkpoints existed.
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
        if snapshot.next == ("wait_clarification",):
            self.graph.invoke(Command(resume={"run_id": str(run.id)}), config)
        else:
            self.graph.invoke(self._state(claim.id, run.id, "extract"), config)
        return self._extraction.replay(claim.id, self._runs.get(run.id))

    def _process_claim(
        self,
        claim_id: UUID,
        *,
        resume: bool = False,
        idempotency_key: str | None = None,
    ) -> ProcessingOutcome:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise NotFoundError("Claim", str(claim_id))

        run_key = f"run:{claim_id}:{idempotency_key}" if idempotency_key else None

        latest_run = self._runs.latest_for_claim(claim_id)
        if (
            not resume
            and latest_run is not None
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
                self._await_terminal(keyed_run)
                return self._keyed_result(claim_id, keyed_run)

        run_id = uuid4()
        if run_key and not self._runs.reserve_run_key(run_key, run_id):
            winner = self._runs.get_run_by_key(run_key)
            if winner is None:
                raise ApplicationError(
                    ErrorCode.IDEMPOTENCY_IN_PROGRESS,
                    "A request with this Idempotency-Key is still in progress.",
                    409,
                )
            self._await_terminal(winner)
            return self._keyed_result(claim_id, winner)

        if latest_run is not None and latest_run.status == ProcessingRunStatus.RUNNING:
            raise ApplicationError(
                ErrorCode.INVALID_CLAIM,
                "A processing run is already in progress.",
                409,
            )

        current_status = ClaimStatus(claim.status)
        if current_status is ClaimStatus.RECEIVED:
            claim = self._extraction.transition_claim(claim, ClaimStatus.PROCESSING)
        elif current_status is ClaimStatus.PROCESSING and (
            resume
            or (
                latest_run is not None
                and latest_run.status == ProcessingRunStatus.FAILED
            )
        ):
            pass
        else:
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
            started_at=None,
            completed_at=None,
            retry_count=len(self._runs.list_for_claim(claim_id)),
            error_code=None,
        )
        self._runs.save(run)
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

    def _await_terminal(self, run: ProcessingRun) -> ProcessingRun:
        """Wait briefly for a concurrent winner's run to reach a final state."""
        for _ in range(40):
            if run.status != ProcessingRunStatus.RUNNING:
                return run
            time.sleep(0.05)
            refreshed = self._runs.get(run.id)
            if refreshed is not None:
                run = refreshed
        return run
