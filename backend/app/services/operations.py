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
