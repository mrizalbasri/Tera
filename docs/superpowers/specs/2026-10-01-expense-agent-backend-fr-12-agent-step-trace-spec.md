# FR-12 — Agent Step Trace for the Frontend

## Requirement

Expose the ordered steps taken by the agent so the frontend can show progress,
evidence, and failures.

## API

- `GET /claims/{claim_id}/timeline`

## Timeline entries

Step sequence, step name, status, started/finished timestamps, duration,
human-readable summary, safe details, related signal/decision IDs, and error
message when applicable.

## Backend behavior

- Keep ordering stable.
- Include successful, failed, retried, clarification, and review steps.
- Redact sensitive values.
- Return enough context to explain the current decision without exposing
  provider secrets.

## Acceptance criteria

- Frontend can render the complete trace from one endpoint.
- Retry attempts are distinguishable.
- Timeline explains why processing stopped or changed state.
- Events from unrelated claims are never included.

## Tests

Ordering, retry steps, failed step, clarification step, review step, redaction,
and claim scoping.
