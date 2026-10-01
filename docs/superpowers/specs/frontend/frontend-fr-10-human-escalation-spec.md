# Frontend FR-10 — Human Escalation

## Goal

Give reviewers a focused queue and enough claim context to decide escalated
claims.

## Surface

Routes: `/reviews` and `/reviews/[claimId]`.

## Behavior

List escalated claims with safe summary fields, filters, age, and risk. Detail
view combines extracted data, policy findings, signals, timeline, and decision
actions.

## Acceptance criteria

- Queue loading, empty, failure, and retry states exist.
- Reviewer can open a claim without losing queue filters.
- Decision actions require an explicit confirmation and reason where required.
- Reviewer identity/action is represented from the backend response.

