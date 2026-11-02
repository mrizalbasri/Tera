from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ActorType,
    ClaimStatus,
    ClarificationStatus,
    DecisionOutcome,
    DuplicateMatchType,
    ProcessingRunStatus,
    ReviewStatus,
    Severity,
    SignalType,
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
    receipt_revision: int = Field(default=0, ge=0)
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
    replaces_receipt_id: UUID | None = None
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
    # True when this result came from the deterministic fallback after a live
    # provider failure; the decision engine must never auto-approve it.
    provider_degraded: bool = False
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
    recovery_count: int = Field(default=0, ge=0)
    receipt_revision: int = Field(default=0, ge=0)
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
    source_signal_ids: list[UUID] = Field(default_factory=list)
    policy_version: int | None = None
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


class Signal(SchemaBase):
    """Structured duplicate/anomaly evidence feeding the decision engine."""

    id: UUID
    claim_id: UUID
    processing_run_id: UUID
    signal_type: SignalType
    severity: Severity
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    match_type: DuplicateMatchType | None = None
    matched_claim_ids: list[UUID] = Field(default_factory=list)
    compared_fields: list[str] = Field(default_factory=list)
    score: Decimal | None = Field(default=None, ge=0, le=1)
    triggered_rules: list[str] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)
    detector_version: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=2000)
    created_at: datetime


class ConversationEntry(SchemaBase):
    """One bounded, safe conversation-context entry for a claim."""

    claim_id: UUID
    role: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1, max_length=2000)
    created_at: datetime


class TimelineEntry(SchemaBase):
    """One ordered, redacted step in a claim's processing story (FR-12)."""

    sequence: int = Field(ge=1)
    timestamp: datetime | None = None
    step_name: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=500)
    processing_run_id: UUID | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error_code: str | None = Field(default=None, max_length=100)
    detail: dict[str, object] = Field(default_factory=dict)
    related_ids: dict[str, str] = Field(default_factory=dict)


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
    validation_findings: list["ValidationFinding"] = Field(default_factory=list)
    policy_evaluations: list["PolicyEvaluation"] = Field(default_factory=list)
    decision: "Decision | None" = None


class ValidationFinding(SchemaBase):
    """Deterministic rule check result attached to a processing run."""

    claim_id: UUID
    processing_run_id: UUID
    extraction_id: UUID | None = None
    rule_id: str = Field(min_length=1, max_length=100)
    passed: bool
    severity: Severity
    actual: object | None = None
    expected: str | None = None
    reason_code: str | None = Field(default=None, max_length=100)
    explanation: str = Field(min_length=1, max_length=2000)


class PolicyRule(SchemaBase):
    rule_id: str = Field(min_length=1, max_length=100)
    rule_type: str = Field(min_length=1, max_length=100)
    limit: Decimal | None = None
    currency: str = "IDR"
    per_person: bool = False
    prohibited_terms: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)


class Policy(SchemaBase):
    policy_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    category: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_to: date | None = None
    rules: list[PolicyRule] = Field(default_factory=list)


class PolicyEvaluation(SchemaBase):
    """Rule-level policy result; the policy version travels with every result."""

    claim_id: UUID
    processing_run_id: UUID
    policy_id: str = Field(min_length=1, max_length=100)
    policy_version: int = Field(ge=1)
    rule_id: str = Field(min_length=1, max_length=100)
    rule_type: str = Field(min_length=1, max_length=100)
    passed: bool
    severity: Severity
    clarifiable: bool = False
    actual_value: object | None = None
    limit: object | None = None
    reason_code: str | None = Field(default=None, max_length=100)
    explanation: str = Field(min_length=1, max_length=2000)
