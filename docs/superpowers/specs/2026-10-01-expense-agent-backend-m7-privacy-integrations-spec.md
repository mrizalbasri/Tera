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

## Tooling addendum (2026-10-05, ADR 0002)

The LLM adapter is built with **LangChain** (`langchain`, `langchain-openai`)
pointed at an OpenAI-compatible endpoint (GLM vision via Z.ai), selected by
`PROVIDER_MODE=mock|live`:

- `LlmReceiptExtractor` uses structured output against the existing
  extraction schema; malformed model output remains a classified,
  non-retryable error.
- `SensitiveDataMasker` runs in our code before any prompt leaves the
  boundary — masking stays provable at a single choke point.
- The adapter lives in `app/integrations/` behind the existing
  `ReceiptExtractor` protocol; tests use deterministic mocks and never
  require network access or API keys.
- See [[0002-langchain-langgraph-stack|ADR 0002]] for the full decision and
  guardrails. LangGraph orchestration follows in M7.5; RAG policy retrieval
  and ML anomaly scoring in M7.6.

## Media scope addendum (2026-10-06)

Live vision extraction intentionally accepts JPG and PNG only — the primary
use case is employees photographing receipts. A PDF receipt in live mode is
classified non-retryable (`415 unsupported_media_for_vision`) and degrades to
the mock extractor only when `PROVIDER_FALLBACK=mock`. Intake (M1) still
accepts PDFs for the mock/deterministic path.

The OCR adapter boundary named in this spec is therefore explicitly deferred:
if the demo later requires PDF receipts, the planned route is rendering PDF
pages to images (PyMuPDF or pypdfium2, inside `integrations/`) so they reuse
the same vision extractor and masking choke point — no separate OCR provider
is planned.
