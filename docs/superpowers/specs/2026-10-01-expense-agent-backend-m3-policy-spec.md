# Backend M3 — Validation and Policy Spec

## Purpose

Apply deterministic checks and versioned reimbursement rules before risk
scoring and final decision-making.

## FR coverage

FR-04 and FR-05.

## Deterministic validation

- Required fields are present.
- Total matches line-item arithmetic when line items exist.
- Date is valid and not in the future.
- Claim is within the 14-day submission window.
- Currency, amount, and category formats are valid.

## Initial policy set

- Meals: maximum Rp75.000 per person per day; receipt required; alcohol
  prohibited.
- Fuel: maximum Rp150.000 per working day; SPBU receipt required.
- Toll/parking: receipt required and amount follows the receipt.
- Hotel: maximum Rp600.000 per night; business-trip evidence required.

## Policy boundary

Policies are versioned data. Start with local policy records and expose a
`PolicyRetriever` interface for future document retrieval/RAG. Evaluation
results must contain rule ID, policy version, actual value, limit, severity,
pass/fail, and explanation.

## Acceptance criteria

- Every failed validation has a stable reason code.
- Policy evaluation is deterministic for a fixed policy version.
- Policy version is attached to every later decision.
- Rules are testable without HTTP or external providers.

## Tests

Valid claim, expired claim, missing receipt, over-limit category, prohibited
item, invalid total/date, unknown category, and policy version selection.
