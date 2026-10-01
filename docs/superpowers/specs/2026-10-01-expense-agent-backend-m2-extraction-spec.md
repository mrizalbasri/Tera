# Backend M2 — Extraction and Retry Spec

## Purpose

Normalize receipt data through a replaceable extractor and recover from
low-quality input before asking for a new receipt.

## FR coverage

FR-02 and FR-03.

## Pipeline

```text
receipt -> quality check -> preprocessing -> extraction
        -> field validation -> confidence check
        -> retry or clarification
```

## Normalized output

- vendor
- receipt date
- total and currency
- category
- line items
- field-level confidence
- warnings and provider metadata

## Behavior

- Begin with a deterministic mock/local extractor.
- Retry only a configured number of times.
- Preserve each attempt and its confidence values.
- Reprocessing must create a new processing run.
- Low confidence on required fields creates a specific clarification request.
- Extractor output is validated before policy or decision logic sees it.

## Acceptance criteria

- Required fields have typed values and field-level confidence.
- Retry count is bounded and visible in the processing trace.
- Failed extraction transitions to `needs_clarification`.
- The user-facing reason explains what must be corrected.
- The same fixture produces the same normalized result in tests.

## Tests

High-confidence extraction, low-confidence total/date, preprocessing retry,
retry exhaustion, unreadable receipt, and malformed provider output.
