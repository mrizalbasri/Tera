# FR-03 — Preprocessing, Retry, and Photo-Again Request

## Requirement

Retry extraction after preprocessing when confidence is low and request a new
receipt when retries cannot produce reliable fields.

## Backend behavior

- Run preprocessing only for eligible quality failures.
- Retry a bounded number of times.
- Record every attempt and its confidence values.
- Stop retrying when confidence passes the configured threshold.
- Create `needs_clarification` with a specific re-upload message after
  exhaustion.

## Data

Processing run, attempt number, preprocessing operation, extractor result,
confidence, error classification, and user action message.

## Acceptance criteria

- Retry count is configurable and bounded.
- Each attempt is visible in the processing trace.
- Retry exhaustion never produces a false approval.
- The response identifies which field or image problem requires correction.

## Tests

Successful retry, retry exhaustion, non-retryable provider error, unreadable
image, and repeated processing idempotency.
