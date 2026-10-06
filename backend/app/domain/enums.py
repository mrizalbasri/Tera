from enum import StrEnum


class ClaimStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProcessingRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"


class DecisionOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"


class ClarificationStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    CANCELLED = "cancelled"


class ReviewStatus(StrEnum):
    OPEN = "open"
    DECIDED = "decided"


class ActorType(StrEnum):
    SYSTEM = "system"
    AGENT = "agent"
    EMPLOYEE = "employee"
    REVIEWER = "reviewer"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class SignalType(StrEnum):
    DUPLICATE = "duplicate"
    ANOMALY = "anomaly"


class DuplicateMatchType(StrEnum):
    EXACT_HASH = "exact_hash"
    LIKELY_ATTRIBUTES = "likely_attributes"


class ErrorClassification(StrEnum):
    """Provider failure taxonomy (M7 reliability rules)."""

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
