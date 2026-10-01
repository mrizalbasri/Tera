# Frontend FR-13 — Sensitive Data Display

## Goal

Prevent accidental disclosure of sensitive data while preserving useful claim
feedback.

## Surface

All routes and shared display components.

## Behavior

Render only fields explicitly supplied for frontend display. Mask identifiers
and personal values according to API metadata. Never display provider secrets,
raw prompt content, or unmasked debug payloads.

## Acceptance criteria

- Sensitive display values have accessible masked labels.
- Error UI does not echo request bodies or tokens.
- Browser-visible logs contain no receipt bytes or personal data.
- Download/export controls use backend-provided safe data only.

