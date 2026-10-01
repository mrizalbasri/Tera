# FR-13 — Sensitive Data Masking Before External LLM Calls

## Requirement

Mask sensitive data before any receipt or claim content is sent to an
external LLM or provider.

## Backend behavior

- Classify fields before provider calls.
- Mask employee identifiers, contact details, account references, and other
  configured sensitive values.
- Keep an internal mapping only when required for response correlation.
- Store safe provider metadata, not raw secret-bearing payloads.
- Keep credentials in environment or deployment secret storage.

## Interface

`SensitiveDataMasker` returns masked payload, masking metadata, and a safe
correlation reference.

## Acceptance criteria

- Sensitive values cannot cross the external boundary unmasked.
- Masking is deterministic enough to correlate a response safely.
- Provider failures do not bypass masking.
- Logs and audit events contain no raw sensitive payload.

## Tests

Employee data, receipt text, account-like values, nested payloads, missing
fields, provider failure, and masking regression fixtures.
