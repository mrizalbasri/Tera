# FR-14 — Periodic Reporting and Export

## Requirement

Provide summary metrics and structured export for claim operations.

## API

- `GET /reports/summary`
- `GET /reports/export.csv`

Filters include date range, category, employee reference, and status.

## Metrics

- Total claims.
- Approved, rejected, clarification, and escalated counts.
- Automated versus manual outcomes.
- Duplicate and anomaly counts.
- Average processing duration.
- Estimated time saved using a documented formula.

## Export

CSV is the first format with stable headers and safe values. Google Sheets is
a later adapter behind the same reporting boundary and is not required by the
core persistence model.

## Acceptance criteria

- Metrics match persisted records.
- Filters respect employee data scope.
- Empty result sets are explicit and valid.
- Export errors do not mutate claims or decisions.
- CSV headers and value formatting remain stable.

## Tests

Aggregation, filters, employee scoping, empty report, CSV special characters,
date formatting, and export failure.
