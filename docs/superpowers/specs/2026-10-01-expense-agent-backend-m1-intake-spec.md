# Backend M1 — Claim Intake Spec

## Purpose

Create the first persistent domain object: a claim with one or more uploaded
receipts, validated before processing.

## FR coverage

FR-01 and the intake portion of FR-11.

## API contract

- `POST /claims`
- `GET /claims`
- `GET /claims/{claim_id}`

The initial upload may use multipart form data. The application use case must
depend on a file-storage interface, not directly on HTTP.

## Behavior

- Accept JPG, PNG, and PDF.
- Reject unsupported media types and oversized files.
- Calculate a content hash.
- Store a safe file reference and metadata.
- Create the claim with `received` status.
- Record a basic receipt quality result.
- Support an idempotency key for repeated submissions.

## Data

Employee reference, claim metadata, receipt metadata, content hash, quality
score/findings, and timestamps are required. Fixtures must be synthetic or
anonymized.

## Acceptance criteria

- Valid upload returns claim and receipt identifiers.
- Claim retrieval exposes current status and receipt metadata.
- Invalid upload returns a typed 4xx response.
- Repeating an idempotency key does not create a second claim.
- Logs contain no raw receipt bytes or sensitive payloads.

## Tests

Valid JPG/PNG/PDF, unsupported file, oversized file, missing metadata, exact
hash duplicate, idempotent retry, and safe logging.
