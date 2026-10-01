# FR-10 — Human Review Escalation

## Requirement

Route high-value, low-confidence, anomalous, or otherwise uncertain claims to
a human reviewer.

## Escalation triggers

- Amount above Rp500.000.
- Confidence below 0.8.
- High anomaly score.
- Policy or duplicate result requiring human judgment.

## API

- `GET /reviews`
- `POST /reviews/{claim_id}/decision`

## Backend behavior

- Place escalated claims in a review queue.
- Include reason codes and evidence in the review payload.
- Record reviewer action and reason.
- Preserve the agent decision when a reviewer confirms or overrides it.
- Create a new final decision after review.

## Acceptance criteria

- Every escalation has a visible reason.
- Reviewer actions are attributable.
- Review state is idempotent.
- A reviewer cannot approve a claim without an auditable action.

## Tests

Each trigger, review confirmation, override, invalid transition, duplicate
review submission, and reviewer reason requirement.
