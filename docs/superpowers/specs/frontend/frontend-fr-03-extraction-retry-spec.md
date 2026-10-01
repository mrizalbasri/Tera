# Frontend FR-03 — Extraction Retry

## Goal

Make preprocessing and extraction retries understandable and actionable.

## Surface

Claim detail processing state and receipt-quality feedback.

## Behavior

Show the current attempt, a non-blocking pending state, and the backend's
specific request when extraction remains insufficient. Provide a clear action
to upload a replacement receipt without losing claim context.

## Acceptance criteria

- Retry progress is visible in the agent timeline.
- A failed retry does not appear as a successful extraction.
- The retake action explains the required improvement.
- Network retry is bounded and never creates duplicate claim submissions.

