# FR-06 — Duplicate Receipt Detection

## Requirement

Detect exact and likely duplicate receipts using file and claim attributes.

## Detection levels

- Exact match by receipt content hash.
- Likely match by vendor, receipt date, and amount.
- Optional near-match similarity with a configured threshold.

## Result contract

Duplicate signal, confidence, match type, matched claim IDs, compared fields,
and explanation.

## Backend behavior

- Query only permitted historical claim scope.
- Do not mark a claim duplicate without evidence.
- Feed duplicate signals into the decision engine.
- Preserve the signal even if a reviewer overrides the outcome.

## Acceptance criteria

- Identical receipt content is detected.
- Attribute matches are explainable.
- Duplicate search is scoped and does not leak unrelated employee data.
- Duplicate evidence is visible in claim details and timeline.

## Tests

Exact hash match, same vendor/date/amount, partial attribute match, false
positive prevention, and reviewer override preservation.
