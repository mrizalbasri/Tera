# FR-04 — Deterministic Claim Validation

## Requirement

Validate extracted data using deterministic rules before policy and decision
processing.

## Rules

- Required fields are present.
- Total matches line-item arithmetic when line items exist.
- Date is valid and not in the future.
- Claim date is within the allowed submission window.
- Amount and currency formats are valid.
- Category is supported.

## Result contract

Each validation result contains rule ID, pass/fail, severity, actual value,
expected constraint, reason code, and explanation.

## Acceptance criteria

- Validation is deterministic for identical input.
- Rule failures are structured signals, not unhandled exceptions.
- Invalid required data blocks approval.
- Validation results are stored with the processing run.

## Tests

Valid data, missing field, total mismatch, future date, expired claim,
malformed amount, unsupported currency, and unknown category.
