from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActorType,
    ClaimStatus,
    ClarificationStatus,
    DecisionOutcome,
    ProcessingRunStatus,
    ReviewStatus,
)


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class ClaimCreate(SchemaBase):
    employee_id: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    declared_amount: Decimal | None = Field(default=None, gt=0)


class Claim(SchemaBase):
    id: UUID
    employee_id: str
    status: ClaimStatus = ClaimStatus.RECEIVED
    submitted_at: datetime
    currency: str
    declared_amount: Decimal | None = None
    current_decision_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class Receipt(SchemaBase):
    id: UUID
    claim_id: UUID
    original_filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=100)
    storage_reference: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(min_length=64, max_length=64)
    quality_score: Decimal | None = Field(default=None, ge=0, le=1)
    quality_findings: list[str] = Field(default_factory=list)
    created_at: datetime


class ProcessingRun(SchemaBase):
    id: UUID
    claim_id: UUID
    status: ProcessingRunStatus
    pipeline_version: str = Field(min_length=1, max_length=100)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = Field(default=0, ge=0)
    error_code: str | None = Field(default=None, max_length=100)


class Decision(SchemaBase):
    id: UUID
    claim_id: UUID
    processing_run_id: UUID
    outcome: DecisionOutcome
    reason_codes: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=1, max_length=2000)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    anomaly_score: Decimal | None = Field(default=None, ge=0, le=1)
    created_by: ActorType
    created_at: datetime


class Clarification(SchemaBase):
    id: UUID
    claim_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    answer: str | None = Field(default=None, max_length=2000)
    status: ClarificationStatus
    created_at: datetime
    answered_at: datetime | None = None


class Review(SchemaBase):
    id: UUID
    claim_id: UUID
    status: ReviewStatus
    reviewer_reference: str | None = Field(default=None, max_length=100)
    action: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)
    created_at: datetime
    decided_at: datetime | None = None


class AuditEvent(SchemaBase):
    id: UUID
    aggregate_type: str = Field(min_length=1, max_length=100)
    aggregate_id: UUID
    processing_run_id: UUID | None = None
    sequence_number: int = Field(ge=1)
    actor_type: ActorType
    event_type: str = Field(min_length=1, max_length=100)
    safe_payload: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime
    duration_ms: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    error_code: str | None = Field(default=None, max_length=100)
