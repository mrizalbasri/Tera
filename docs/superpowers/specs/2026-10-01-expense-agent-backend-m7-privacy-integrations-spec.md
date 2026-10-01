# Backend M7 — Privacy and External Integrations Spec

## Purpose

Add OCR, LLM, retrieval, and external storage behind safe interfaces without
making external providers authoritative or exposing sensitive data.

## FR coverage

FR-13.

## Adapter boundaries

- OCR/extraction provider.
- LLM provider.
- Policy retrieval/RAG provider.
- File storage provider.

Adapters accept safe internal inputs and return validated internal schemas.
Provider-specific request/response types stay inside the integration boundary.

## Privacy rules

- Classify fields before external calls.
- Mask or redact sensitive values.
- Keep credentials in environment variables or deployment secrets.
- Store only safe provider metadata.
- Never log raw receipt content or secret-bearing payloads.

## Reliability rules

- Explicit timeout per provider call.
- Bounded retry with backoff.
- Retryable and non-retryable error classes.
- Configurable fallback to local/mock providers.
- Deterministic validation remains authoritative over provider output.

## Acceptance criteria

- Every provider can be replaced by a test double.
- Masking tests prove sensitive fields do not cross the boundary.
- Provider failure cannot produce an approval.
- Provider errors are visible in the processing trace.
- No credential or sensitive payload is committed in fixtures.

## Tests

Masking, timeout, rate limit, malformed provider response, fallback provider,
and deterministic validation after provider failure.
