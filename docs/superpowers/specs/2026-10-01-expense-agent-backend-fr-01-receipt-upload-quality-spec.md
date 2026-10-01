# FR-01 — Receipt Upload and Quality Measurement

## Requirement

Accept JPG, PNG, and PDF receipts and measure whether the submitted document is
usable for processing.

## Backend behavior

- Accept one or more receipts on a claim.
- Validate media type, file size, filename, and storage reference.
- Calculate a content hash for duplicate detection.
- Run a deterministic quality check for readability, file integrity, and
  required metadata.
- Return quality score and structured findings.
- Reject malformed or unsupported input with a typed 4xx error.

## Interfaces

- `POST /claims`
- `GET /claims/{claim_id}`
- `ReceiptQualityChecker`
- `FileStorage`

## Data

Receipt ID, claim ID, media type, safe storage reference, content hash,
quality score, quality findings, and timestamps.

## Acceptance criteria

- Valid JPG, PNG, and PDF files are accepted.
- Unsupported and oversized files are rejected explicitly.
- Quality failures identify the corrective action.
- Raw receipt bytes are never written to logs.

## Tests

Valid files, corrupt files, unsupported media, oversized files, unreadable
image, PDF metadata failure, and exact hash calculation.
