# Backend M6 — Persistence, Audit, and Agent Trace Spec

## Purpose

Persist the complete lifecycle and expose an ordered explanation of how a
claim reached its current state.

## FR coverage

FR-11 and FR-12.

## Records

Employee, claim, receipt, extraction result, processing run, step result,
policy evaluation, signal, decision, clarification, review, and audit event.

## Audit event contract

Each event contains aggregate type/ID, processing run, sequence number, actor
type, event type, safe payload, timestamp, duration where relevant, and error
classification where relevant.

## API contract

- `GET /claims/{claim_id}/timeline`

The timeline must contain meaningful steps in stable order and be sufficient to
explain the current decision.

## Reliability rules

- Processing retries create new runs.
- Claim creation and processing use idempotency keys.
- Persistence failures are explicit failures.
- Earlier successful steps are not erased by later failures.
- Audit events are append-only from application behavior.
- Raw receipt content, secrets, and unmasked sensitive data are excluded.

## Acceptance criteria

- A claim can be reconstructed from its timeline.
- Reprocessing preserves previous runs and decisions.
- Repeated requests do not create duplicate claims or conflicting runs.
- Frontend can render the ordered agent trace from one endpoint.

## Tests

Repository integration, timeline ordering, event completeness, retry history,
idempotency, and audit payload safety.
