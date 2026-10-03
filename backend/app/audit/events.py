from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.enums import ActorType
from app.repositories.protocols import AuditRepository
from app.schemas.core import AuditEvent


def record_audit_event(
    audit: AuditRepository,
    *,
    aggregate_type: str,
    aggregate_id: UUID,
    event_type: str,
    actor_type: ActorType,
    safe_payload: dict[str, Any] | None = None,
    processing_run_id: UUID | None = None,
    duration_ms: int | None = None,
    retry_count: int = 0,
    error_code: str | None = None,
) -> AuditEvent:
    """Build and append one audit event with safe payload only."""
    event = AuditEvent(
        id=uuid4(),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        processing_run_id=processing_run_id,
        sequence_number=1,
        actor_type=actor_type,
        event_type=event_type,
        safe_payload=safe_payload or {},
        timestamp=datetime.now(UTC),
        duration_ms=duration_ms,
        retry_count=retry_count,
        error_code=error_code,
    )
    return audit.append(event)
