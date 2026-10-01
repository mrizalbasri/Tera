# Backend M0 — Foundation Spec

## Purpose

Establish the backend boundaries and contracts required by all later Expense
Agent features while preserving the current FastAPI health endpoint.

## Scope

- Separate API, schemas, domain, services, repositories, integrations, and
  audit responsibilities.
- Define shared enums for claim, processing, clarification, review, and
  decision states.
- Define typed application errors and a stable error response.
- Centralize environment-driven settings and decision thresholds.
- Define interfaces for persistence, storage, extraction, policy retrieval,
  duplicate detection, anomaly scoring, masking, and export.
- Provide in-memory fakes for unit tests.

## Domain constraints

- A claim is a reimbursement submission and may contain multiple receipts.
- A processing run is one attempt; retrying creates a new run.
- Terminal decisions are preserved and corrected through new decisions.
- Provider failures are explicit errors, never success-shaped fallbacks.

## Outputs

- Package/module boundaries under `backend/app/`.
- Core Pydantic schemas and domain types.
- Provider/repository protocols.
- Standard error mapping.
- Configuration entries with safe local defaults.

## Validation

- Existing `/health` test passes.
- Unit tests cover legal state transitions and invalid transitions.
- Schema tests cover malformed input and error serialization.
- No business logic is introduced into route handlers.
