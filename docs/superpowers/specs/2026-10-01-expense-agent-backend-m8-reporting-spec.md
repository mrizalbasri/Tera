# Backend M8 — Reporting and Export Spec

## Purpose

Provide operational summaries and safe exports from claims, processing runs,
signals, decisions, and review data.

## FR coverage

FR-14.

## API contract

- `GET /reports/summary`
- `GET /reports/export.csv`

Filters include date range, category, employee reference, and claim status.

## Metrics

- Total claims.
- Approved, rejected, clarification, and escalated counts.
- Automated versus manual outcomes.
- Duplicate and anomaly counts.
- Average processing duration.
- Estimated time saved using a documented formula.

## Export boundary

CSV is the first supported format with stable headers and safe values. Google
Sheets is a later adapter behind the same reporting/export interface and is
not a core persistence dependency.

## Acceptance criteria

- Summary values match persisted records.
- Filters do not leak unrelated employee data.
- Empty result sets are explicit and valid.
- Export failures do not mutate claim or decision state.
- CSV formatting is stable for frontend/download consumers.

## Tests

Aggregation, date/category/status filters, employee scoping, empty reports,
CSV headers, special characters, and export failure handling.
