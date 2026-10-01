# FR-09 — Clarification Conversation

## Requirement

Ask for missing or ambiguous information, accept the employee answer, and
recalculate the claim.

## API

- `GET /claims/{claim_id}/clarifications`
- `POST /claims/{claim_id}/clarifications/{clarification_id}/answer`

## Backend behavior

- Store question, requested field, status, originating run, and timestamp.
- Accept typed or structured answers.
- Create a new processing run after an answer.
- Re-run only affected extraction/validation/policy steps where safe.
- Preserve the original question, run, and decision.

The multi-person meal scenario must ask for participant count and recalculate
the per-person amount.

## Acceptance criteria

- Clarification state is visible on the claim.
- Duplicate answer submission is idempotent.
- Invalid answers return actionable errors.
- New decisions reference the clarification response.

## Tests

Participant count, missing business-trip evidence, invalid answer, repeated
answer, and successful resume.
