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


class ExtractedLineItem(SchemaBase):
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    total: Decimal = Field(gt=0)


class FieldConfidence(SchemaBase):
    value: object
    confidence: Decimal = Field(ge=0, le=1)


class ExtractionResult(SchemaBase):
    id: UUID
    receipt_id: UUID
    processing_run_id: UUID | None = None
    vendor: FieldConfidence
    receipt_date: FieldConfidence
    total: FieldConfidence
    currency: FieldConfidence
    category: FieldConfidence
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider: str = Field(min_length=1, max_length=100)
    created_at: datetime


class ExtractionAttempt(SchemaBase):
    attempt: int = Field(ge=1)
    processing_run_id: UUID | None = None
    preprocessing: list[str] = Field(default_factory=list)
    confidence: dict[str, Decimal]
    extraction_id: UUID | None = None
    error_code: str | None = None
    message: str | None = None
    created_at: datetime


class ClarificationRequest(SchemaBase):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    fields: list[str] = Field(min_length=1)


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
    processing_run_id: UUID | None = None
    code: str = Field(min_length=1, max_length=100)
    fields: list[str] = Field(default_factory=list)
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


class ProcessingOutcome(SchemaBase):
    """Internal result of one processing run, reused for idempotent replays."""

    claim: Claim
    extractions: list[ExtractionResult] = Field(default_factory=list)
    attempts: list[ExtractionAttempt] = Field(default_factory=list)
    clarification: ClarificationRequest | None = None
