# Frontend FR-15 — Claim History and Conversation Context

## Goal

Show relevant claim/vendor history and clarification context without mixing
unrelated employee data.

## Surface

Claim detail history panel and clarification conversation history.

## Behavior

Render only history returned by the authorized API response, with clear scope
and timestamps. Separate current claim context from historical references.
Conversation messages are ordered and immutable after submission.

## Acceptance criteria

- History identifies its scope and relation to the current claim.
- Unrelated employee/vendor records are never inferred or displayed.
- Historical context remains available after a new processing run.
- Conversation order and author are accessible and stable.

