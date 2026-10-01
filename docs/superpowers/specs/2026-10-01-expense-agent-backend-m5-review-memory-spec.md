# Backend M5 — Clarification, Review, and Memory Spec

## Purpose

Handle ambiguous claims and human exceptions without losing previous agent
attempts or decisions.

## FR coverage

FR-09, FR-10, and FR-15.

## API contract

- `GET /claims/{claim_id}/clarifications`
- `POST /claims/{claim_id}/clarifications/{clarification_id}/answer`
- `GET /reviews`
- `POST /reviews/{claim_id}/decision`

## Clarification

Store the question, requested fields, status, originating processing run, and
employee answer. An answer creates a new run and recalculates affected
validation/policy results. The original question and decision remain visible.

The multi-person meal scenario must ask for participant count and recalculate
the per-person amount.

## Human review

Escalated claims enter a review queue. Reviewer confirmation or override is a
new decision with reviewer reference, reason, and audit event. An override
does not erase the agent decision.

## Memory boundary

Employee/vendor history is scoped to the permitted employee and vendor.
Conversation context is scoped to one claim. Unrelated employee data must not
be inserted into an agent context.

## Acceptance criteria

- Clarification can resume processing.
- Repeated answer submission is idempotent.
- Review confirmation and override are attributable.
- A claim can finish as approved, rejected, or escalated after clarification.
- History queries do not cross employee boundaries.

## Tests

Participant clarification, low-confidence clarification, review queue, manual
override, duplicate answers, and scoped history retrieval.
