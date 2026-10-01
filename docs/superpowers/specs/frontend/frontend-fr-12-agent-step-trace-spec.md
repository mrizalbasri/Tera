# Frontend FR-12 — Agent Step Trace

## Goal

Show the ordered work performed by the agent so users can understand progress
and outcome.

## Surface

Timeline component using `GET /claims/{claim_id}/timeline`.

## Behavior

Render step name, status, sequence, duration when safe, timestamp, and concise
result. Expandable details must remain sanitized and should not expose secrets
or raw provider payloads.

## Acceptance criteria

- Timeline order follows the API sequence.
- Running, succeeded, failed, and skipped steps are distinct.
- A failed step includes an actionable explanation.
- Timeline remains usable with keyboard and screen reader navigation.

