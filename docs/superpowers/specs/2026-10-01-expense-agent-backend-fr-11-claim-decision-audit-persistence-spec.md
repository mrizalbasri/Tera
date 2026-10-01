# FR-11 — Claim, Decision, and Tool Audit Persistence

## Requirement

Persist claims, decisions, processing steps, and tool calls so the complete
processing history can be reconstructed.

## Records

Employee, claim, receipt, extraction result, processing run, step result,
policy evaluation, signal, decision, clarification, review, and audit event.

## Audit event

Aggregate ID, run ID, sequence number, actor type, event type, safe payload,
timestamp, duration, retry count, and error classification.

## Rules

- Events are append-only from application behavior.
- Reprocessing creates a new run.
- Earlier successful steps remain visible after later failure.
- Raw receipts, credentials, and unmasked sensitive data are excluded.

## Acceptance criteria

- Claim history is reconstructable.
- Every decision references a processing run.
- Tool/provider calls have status and duration.
- Persistence failures are explicit and do not create false success.

## Tests

Repository CRUD, audit append, failed step preservation, retry history,
safe payload, and decision-to-run linkage.
