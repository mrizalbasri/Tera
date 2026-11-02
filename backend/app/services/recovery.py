"""Recovery uses the same adapters and repositories as HTTP processing."""

import argparse
import json
import logging
from threading import Event, Thread
from app.config import Settings
from app.services.processing import ClaimProcessingService

logger = logging.getLogger(__name__)


def build_processing(settings: Settings) -> ClaimProcessingService:
    from app.api import deps

    backend = deps._backend(settings)
    return deps.get_extraction_service(
        settings=settings, claims=backend.claims, receipts=backend.receipts, storage=backend.file_storage,
        runs=backend.runs, extractions=backend.extractions, attempts=backend.attempts,
        clarifications=backend.clarifications, findings=backend.findings, evaluations=backend.evaluations,
        signals=backend.signals, decisions=backend.decisions, history=backend.history, reviews=backend.reviews,
        audit=backend.audit, duplicate_detector=deps.get_duplicate_detector(backend.history, backend.receipts, backend.extractions),
        anomaly_scorer=deps.get_anomaly_scorer(settings),
        extractor=deps.get_receipt_extractor(settings, deps.get_sensitive_data_masker()),
        validation=deps.get_validation_service(settings), policy_retriever=deps.get_policy_retriever(settings),
        policy_evaluator=deps.get_policy_evaluator(), decider=deps.get_decision_engine(settings),
    )


class RecoveryWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.stopped = Event()
        self.thread = Thread(target=self._run, name="claim-recovery", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        while not self.stopped.wait(self.settings.recovery_interval_seconds):
            try:
                result = build_processing(self.settings).recover_pending()
                if result["recovered"] or result["failed"]:
                    logger.warning("claim recovery batch result=%s", result)
            except Exception:
                logger.error("claim recovery worker could not complete its scan")

    def close(self) -> None:
        self.stopped.set()
        self.thread.join()


def main() -> None:
    from app.config import get_settings
    from app.agent.runtime import close_graph_resources
    from app.api.deps import close_sql_repositories
    from app.integrations.rag.pgvector import close_policy_indexes

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    settings = get_settings()
    if settings.storage_backend != "sql":
        parser.error("recovery requires persistent SQL storage")
    try:
        result = build_processing(settings).recover_pending(limit=args.limit)
        print(json.dumps(result))
        if result["failed"]:
            raise SystemExit(1)
    finally:
        close_graph_resources()
        close_sql_repositories()
        close_policy_indexes()


if __name__ == "__main__":
    main()
