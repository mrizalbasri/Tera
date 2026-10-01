# Frontend FR-06 — Duplicate Detection

## Goal

Clearly warn when the backend detects an exact or likely duplicate.

## Surface

Decision summary, duplicate signal panel, and claim timeline.

## Behavior

Show duplicate type, severity, confidence or match score when available, and
safe evidence such as vendor/date/amount. Related claim identifiers may be
shown only when authorized by the API.

## Acceptance criteria

- Confirmed duplicates are presented as blocking when the backend says so.
- Likely duplicates are distinguished from confirmed duplicates.
- Evidence is understandable and does not reveal unrelated private claims.
- The final decision remains the backend decision.

