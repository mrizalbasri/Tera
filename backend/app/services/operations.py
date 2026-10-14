import logging
from collections import Counter
from datetime import UTC, datetime

from app.errors import ApplicationError
from app.repositories.query import ClaimFilter

logger = logging.getLogger(__name__)


def recover_pending(processing, *, limit: int = 100) -> dict[str, int]:
    counts = Counter(recovered=0, busy=0, failed=0, scanned=0)
    # Capture candidates before mutations change the filtered result's offsets.
    ids = processing.pending_claim_ids(limit=limit)
    for claim_id in ids:
        counts["scanned"] += 1
        try:
            if processing.recover_claim(claim_id) is not None:
                counts["recovered"] += 1
                logger.warning("recovered interrupted claim claim_id=%s", claim_id)
        except ApplicationError as exc:
            counts["busy" if exc.code == "claim_busy" else "failed"] += 1
        except Exception:
            counts["failed"] += 1
            logger.error("claim recovery failed claim_id=%s", claim_id)
    return dict(counts)


def processing_metrics(claims, runs) -> dict:
    counts = Counter()
    duration_total = duration_count = oldest_seconds = 0
    now = datetime.now(UTC)
    offset = 0
    while batch := claims.page(ClaimFilter(), limit=200, offset=offset):
        offset += len(batch)
        claim_updated = {claim.id: claim.updated_at for claim in batch}
        for claim in batch:
            counts[f"claims_{claim.status}"] += 1
        for run in runs.list_for_claims([c.id for c in batch]):
            counts[f"runs_{run.status}"] += 1
            if run.started_at and run.completed_at:
                duration_total += max(0, int((run.completed_at - run.started_at).total_seconds() * 1000))
                duration_count += 1
            if run.status in ("running", "queued"):
                since = run.started_at or claim_updated[run.claim_id]
                oldest_seconds = max(oldest_seconds, int((now - since).total_seconds()))
    return dict(counts, average_run_duration_ms=round(duration_total / duration_count) if duration_count else None,
                oldest_active_run_seconds=oldest_seconds)
