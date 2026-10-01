# Frontend FR-14 — Reporting and Export

## Goal

Provide managers and admins with summary metrics, filters, and CSV export.

## Surface

Route: `/reports`.

## Behavior

Load `GET /reports/summary`, render claim counts, automated/manual ratio,
anomaly and duplicate counts, duration, and estimated time saved. Filters are
reflected in the request. Export invokes the backend CSV endpoint and reports
failure without changing claim state.

## Acceptance criteria

- Metrics show their period and active filters.
- Empty results are explained rather than rendered as misleading zeros.
- CSV download uses stable backend-provided content.
- Export errors are recoverable and do not discard current filters.

