# Frontend FR-09 — Clarification Conversation

## Goal

Let employees answer backend-generated clarification questions and resume
processing.

## Surface

Route: `/claims/[claimId]/clarification`.

## Behavior

Show the question, relevant safe context, answer input, submission state, and
historical messages. Submit to
`POST /claims/{claim_id}/clarifications/{clarification_id}/answer`.

## Acceptance criteria

- Only open clarification requests are answerable.
- Empty answers are rejected with an inline message.
- Submitted answers become read-only history after success.
- Processing resumption and failures are clearly communicated.

