# FR-02 — Structured Receipt Field Extraction

## Requirement

Extract vendor, date, total, line items, and category with field-level
confidence scores.

## Backend behavior

- Define a normalized extraction result independent of OCR/LLM providers.
- Extract vendor, receipt date, total, currency, category, and line items.
- Attach confidence to every required field.
- Preserve warnings and safe provider metadata.
- Validate provider output before returning it to the pipeline.

## Interfaces

- `ReceiptExtractor`
- `POST /claims/{claim_id}/process`
- Extraction result in claim timeline.

## Acceptance criteria

- Required fields use typed values.
- Every required field has a confidence score.
- Malformed provider output becomes a classified processing error.
- Provider-specific response shapes do not leak into domain schemas.

## Tests

Complete extraction, missing field, malformed amount/date, line-item totals,
low confidence, and deterministic mock provider output.
