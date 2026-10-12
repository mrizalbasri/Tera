"""Thin graph steps that delegate business operations to services."""

from uuid import UUID

from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from app.agent.state import ClaimGraphState, ReviewExecution
from app.domain.enums import ProcessingRunStatus
from app.errors import ApplicationError, ErrorCode
from app.repositories.protocols import ClaimRepository, ProcessingRunRepository
from app.schemas.core import Claim, ProcessingRun
from app.services.extraction import ExtractionService


class ClaimNodes:
    def __init__(
        self,
        claims: ClaimRepository,
        runs: ProcessingRunRepository,
        extraction: ExtractionService,
    ) -> None:
        self._claims = claims
        self._runs = runs
        self._extraction = extraction

    def _records(self, state: ClaimGraphState) -> tuple[Claim, ProcessingRun]:
        return (
            self._claims.get(UUID(state["claim_id"])),
            self._runs.get(UUID(state["run_id"])),
        )

    def extract(self, state: ClaimGraphState) -> dict[str, str]:
        claim, run = self._records(state)
        self._extraction.extract_receipts(claim, run)
        run = self._runs.get(run.id)
        return {"stage": "wait_clarification" if run.status == ProcessingRunStatus.NEEDS_CLARIFICATION
                else "validate"}

    def validate(self, state: ClaimGraphState) -> dict[str, str]:
        self._extraction.validate_claim(*self._records(state))
        return {"stage": "evaluate_policy"}

    def evaluate_policy(self, state: ClaimGraphState) -> dict[str, str]:
        self._extraction.evaluate_claim_policy(*self._records(state))
        return {"stage": "detect_duplicates"}

    def detect_duplicates(self, state: ClaimGraphState) -> dict[str, str]:
        self._extraction.detect_duplicates(*self._records(state))
        return {"stage": "score_anomaly"}

    def score_anomaly(self, state: ClaimGraphState) -> dict[str, str]:
        self._extraction.score_anomaly(*self._records(state))
        return {"stage": "decide"}

    def decide(self, state: ClaimGraphState) -> dict[str, str]:
        claim, run = self._records(state)
        self._extraction.decide_claim(claim, run)
        status = self._runs.get(run.id).status
        return {"stage": {
            ProcessingRunStatus.NEEDS_CLARIFICATION: "wait_clarification",
            ProcessingRunStatus.ESCALATED: "wait_review",
        }.get(status, END)}

    @staticmethod
    def wait_clarification(state: ClaimGraphState) -> dict[str, str]:
        answer = interrupt({"claim_id": state["claim_id"], "kind": "clarification"})
        return {"run_id": answer["run_id"], "stage": "extract"}

    @staticmethod
    def wait_review(state: ClaimGraphState) -> dict[str, str]:
        answer = interrupt({"claim_id": state["claim_id"], "kind": "review"})
        return {"run_id": answer["run_id"], "stage": "apply_review"}

    def apply_review(
        self, state: ClaimGraphState, runtime: Runtime[ReviewExecution],
    ) -> dict[str, str]:
        _, run = self._records(state)
        if runtime.context is None:
            raise ApplicationError(ErrorCode.INVALID_CLAIM, "Review input is required.", 409)
        runtime.context.result = runtime.context.apply(run.id)
        self._extraction.complete_run(run, ProcessingRunStatus.SUCCEEDED, [], error_code=None)
        return {"stage": END}
