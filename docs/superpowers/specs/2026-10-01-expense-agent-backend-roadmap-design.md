# Expense Agent Backend Roadmap Design

## Status

Proposed backend design and implementation roadmap covering FR-01 through FR-15.

## Goal

Define the backend boundary, domain model, processing lifecycle, milestones, and
acceptance criteria for the Expense Reimbursement Agent. The roadmap is
intentionally incremental: deterministic and mock-backed behavior must be
stable before OCR, LLM, RAG, and machine-learning integrations are introduced.

The backend must support this target flow:

```text
Claim intake
  -> receipt quality check
  -> field extraction
  -> deterministic validation
  -> policy evaluation
  -> duplicate detection
  -> anomaly scoring
  -> decision
  -> clarification or human review when required
  -> persistence, audit, and reporting
```

## Product boundaries

The backend owns claim processing, policy evaluation, decision recording,
auditability, and reporting data. The frontend owns the employee/reviewer
interaction and presentation of processing steps.

The backend does not initially own authentication, multi-level approval,
WhatsApp/email ingestion, accounting integration, or an on-premise LLM.
Those integrations may be added behind explicit adapters later.

## Domain vocabulary

| Term | Canonical meaning |
|---|---|
| **Claim** | One reimbursement submission made by an employee. A claim may contain one or more receipts. |
| **Receipt** | A receipt document attached to a claim. It has source-file metadata, extracted fields, and quality information. |
| **Employee** | The person submitting a claim. Authentication is outside this prototype, so the backend receives an external employee identifier. |
| **Processing run** | One attempt to process a claim through the pipeline. A retry creates a new run, not a destructive overwrite of the old run. |
| **Policy** | A versioned set of business rules used to evaluate a claim. |
| **Signal** | A structured result from validation, duplicate detection, or anomaly scoring that can influence a decision. |
| **Decision** | The current or historical outcome for a claim: approved, rejected, needs clarification, or escalated. |
| **Clarification** | A question raised when the available receipt or claim context is insufficient to decide safely. |
| **Review** | A human action on an escalated claim. A review may confirm or override an agent decision. |
| **Audit event** | An immutable record of a processing step, tool call, decision, or human action. |

## Domain lifecycle

### Claim status

```text
received
  -> processing
  -> needs_clarification
  -> escalated
  -> approved
  -> rejected
```

`processing` may return to `needs_clarification` or `escalated` after a retry
or clarification response. A terminal decision must not be silently replaced;
corrections and human overrides are recorded as new events and decisions.

### Processing run status

```text
queued -> running -> succeeded
                  -> failed
                  -> needs_clarification
                  -> escalated
```

Each run records its start/end time, pipeline version, step results, errors,
and provider metadata that is safe to retain.

### Decision precedence

The decision engine must apply conservative precedence:

1. Invalid or missing required data produces `needs_clarification`.
2. A confirmed duplicate produces `rejected` unless a human review explicitly
   overrides it.
3. A policy violation produces `rejected`.
4. High anomaly risk, low confidence, or an amount above the escalation
   threshold produces `escalated`.
5. Only a claim passing all required checks can be `approved`.

Every decision stores structured reasons, the signals used, the policy version,
and the processing run that produced it.

## Architecture

The backend remains a modular FastAPI service. Route handlers should translate
HTTP requests into application use cases and should not contain extraction,
policy, duplicate, anomaly, or decision logic.

```text
backend/app/
  main.py
  config.py
  api/              # HTTP routes and dependency wiring
  schemas/          # Pydantic request and response contracts
  domain/           # entities, enums, value objects, decision rules
  services/         # claim-processing use cases and orchestration
  repositories/     # persistence interfaces and implementations
  integrations/     # OCR, LLM, policy retrieval, storage, export adapters
  audit/            # audit event creation and serialization
```

The exact module names may evolve, but the boundaries must remain recognizable:

- **API** handles transport concerns.
- **Schemas** validate external input and shape output.
- **Domain** contains deterministic business behavior.
- **Services** coordinate a complete use case.
- **Repositories** hide persistence details.
- **Integrations** isolate external providers.
- **Audit** records what happened without changing the decision.

## Data model

The persistent model should support at least these records:

### Employee

- `id`
- `external_reference`
- `display_name` or masked label
- timestamps

### Claim

- `id`
- `employee_id`
- `status`
- `submitted_at`
- `currency`
- `declared_amount` when supplied
- `current_decision_id`
- timestamps

### Receipt

- `id`
- `claim_id`
- original filename and media type
- safe storage reference
- content hash
- quality score and quality findings
- timestamps

### Extraction result

- `id`
- `receipt_id`
- processing run
- vendor
- receipt date
- total
- category
- line items
- field-level confidence
- extractor/provider reference

### Processing run and step result

- run status and timestamps
- pipeline version
- step name and sequence
- input/output metadata safe for audit
- retry count
- error classification
- duration

### Policy and policy evaluation

- policy version and effective period
- category and rule definitions
- evaluated rules
- actual values and limits
- pass/fail result
- explanation

### Signal

- signal type: validation, duplicate, anomaly, or quality
- severity
- score where applicable
- structured evidence
- source processing step

### Decision

- decision outcome
- reason codes and human-readable explanation
- confidence and anomaly score
- policy version
- processing run
- created by agent or reviewer
- timestamps

### Clarification and review

- question or requested action
- employee response
- clarification status
- reviewer identity/reference
- reviewer action and reason
- timestamps

### Audit event

- event type
- aggregate type and ID
- processing run
- sequence number
- actor type
- safe event payload
- timestamp

## API surface

The first API contract should be small and stable:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/claims` | Create a claim and attach receipt metadata/file. |
| `GET` | `/claims` | List claims with status and period filters. |
| `GET` | `/claims/{claim_id}` | Return claim, receipt, current decision, and processing summary. |
| `POST` | `/claims/{claim_id}/process` | Start or retry processing idempotently. |
| `GET` | `/claims/{claim_id}/timeline` | Return ordered processing and audit events for the UI. |
| `GET` | `/claims/{claim_id}/clarifications` | Return open and historical clarification requests. |
| `POST` | `/claims/{claim_id}/clarifications/{clarification_id}/answer` | Submit an answer and resume processing. |
| `GET` | `/reviews` | List claims awaiting human review. |
| `POST` | `/reviews/{claim_id}/decision` | Record a reviewer decision or override. |
| `GET` | `/reports/summary` | Return aggregate processing and outcome metrics. |
| `GET` | `/reports/export.csv` | Export filtered claim results as CSV. |

Exact upload transport may be multipart or a storage-reference flow, but the
domain use case must not depend on the HTTP transport.

## Provider interfaces

External dependencies must be replaceable with deterministic test doubles.
Define interfaces for:

- `ReceiptQualityChecker`
- `ReceiptExtractor`
- `PolicyRetriever`
- `DuplicateDetector`
- `AnomalyScorer`
- `SensitiveDataMasker`
- `FileStorage`
- `ClaimRepository`
- `AuditRepository`
- `ReportExporter`

The initial implementations should be local or mock-backed. Provider output
must be parsed into validated internal schemas before it reaches the decision
engine. A provider must never directly set a final claim decision.

## Milestone roadmap

### M0 — Backend foundation

**Purpose:** establish module boundaries and common contracts.

**FR coverage:** supports all later FRs; no user-facing FR is complete yet.

**Work:**

- Introduce application/domain/integration boundaries.
- Add shared error schema and error codes.
- Add status enums and core Pydantic schemas.
- Add configuration for storage, database, provider mode, and thresholds.
- Add structured logging and correlation ID support.
- Define repository and provider interfaces.

**Exit criteria:**

- Existing `/health` behavior remains unchanged.
- Core schemas validate accepted and rejected inputs.
- Unit tests cover status transitions and error serialization.

### M1 — Claim intake and receipt quality

**FR coverage:** FR-01 and the intake part of FR-11.

**Work:**

- Accept JPG, PNG, and PDF receipts.
- Enforce media type and size limits.
- Store safe file references and content hashes.
- Create claims and receipts with initial `received` status.
- Add a deterministic quality checker for file readability and required media metadata.

**Exit criteria:**

- Invalid files return explicit validation errors.
- Valid claims can be created and retrieved.
- Exact duplicate files can be identified by hash.
- No receipt bytes or personal data are written to logs.

### M2 — Extraction, preprocessing, and retry

**FR coverage:** FR-02 and FR-03.

**Work:**

- Define normalized extraction output.
- Add mock/local extractor with field-level confidence.
- Add image preprocessing hook and bounded retries.
- Return a specific clarification request when extraction remains insufficient.
- Persist each extraction attempt and its confidence data.

**Exit criteria:**

- Vendor, date, total, category, and line items have validated shapes.
- Low-confidence fields trigger retry according to configured limits.
- Failed extraction produces a user-actionable message.
- Extraction results are reproducible in tests with fixtures.

### M3 — Deterministic validation and policy evaluation

**FR coverage:** FR-04 and FR-05.

**Work:**

- Validate totals, dates, required fields, currency, and category.
- Represent policy rules as versioned data.
- Implement initial rules from the BRD:
  meal, fuel, toll/parking, hotel, claim age, required receipt,
  prohibited items, and category limits.
- Define a policy retrieval boundary; start with local policy data.
- Persist rule-level evaluation results.

**Exit criteria:**

- Each validation failure has a stable reason code.
- Policy results identify rule, actual value, limit, and explanation.
- Policy version is attached to every decision.
- Tests cover valid, expired, missing-receipt, over-limit, and prohibited-item cases.

### M4 — Duplicate detection, anomaly scoring, and decisions

**FR coverage:** FR-06, FR-07, and FR-08.

**Work:**

- Detect exact file duplicates by hash.
- Detect likely duplicates by vendor, date, and amount.
- Add a rule-based anomaly scorer over synthetic history.
- Produce structured signals with evidence.
- Implement conservative decision precedence and configurable thresholds:
  auto-approve at or below Rp500.000 when confidence is at least 0.8 and
  there is no blocking signal; escalate otherwise when the claim is not
  directly rejectable.

**Exit criteria:**

- Decisions are deterministic for the same input and policy version.
- Approved, rejected, escalated, and clarification outcomes are covered.
- Duplicate and anomaly explanations are visible in the decision payload.
- No decision can be produced without an associated processing run and reason.

### M5 — Clarification, human review, and memory

**FR coverage:** FR-09, FR-10, and FR-15.

**Work:**

- Persist clarification questions and employee answers.
- Resume processing after an answer without erasing prior runs.
- Add a review queue for escalated claims.
- Record reviewer decisions and overrides as new decisions.
- Provide employee/vendor history to the processing service with explicit scope
  and privacy controls.
- Preserve conversation context per claim.

**Exit criteria:**

- Multi-person meal claims can request participant count and recalculate.
- Low-confidence claims can be clarified or escalated.
- Reviewer actions are attributable and auditable.
- Historical context can be queried without mixing unrelated employees.

### M6 — Persistence, audit trail, and agent trace

**FR coverage:** FR-11 and FR-12.

**Work:**

- Persist claims, receipts, runs, steps, signals, decisions, clarifications,
  reviews, and audit events.
- Expose an ordered timeline for the frontend.
- Record tool/provider calls with safe metadata, status, duration, and error.
- Add idempotency for claim creation and processing retries.
- Ensure audit events are append-only from the application perspective.

**Exit criteria:**

- A claim can be reconstructed from its audit timeline.
- Reprocessing creates a new run rather than mutating history.
- The timeline order is stable and contains every meaningful step.
- Repeated requests do not create duplicate claims or conflicting runs.

### M7 — Privacy, masking, and external integrations

**FR coverage:** FR-13.

**Work:**

- Classify fields sent to external providers.
- Mask or redact sensitive values before provider calls.
- Add OCR and LLM adapters behind provider interfaces.
- Add timeout, bounded retry, fallback, and provider error mapping.
- Keep secrets in environment configuration only.
- Retain only safe provider metadata and never raw secret-bearing payloads.

**Exit criteria:**

- Provider adapters can be replaced with mocks in tests.
- Masking tests prove sensitive values do not cross the external boundary.
- Provider failures produce explicit retryable or non-retryable errors.
- Deterministic validation remains authoritative over provider output.

### M8 — Reporting and export

**FR coverage:** FR-14.

**Work:**

- Aggregate claim counts by status and decision source.
- Report automated versus manual processing.
- Report duplicate/anomaly counts and processing duration.
- Estimate time saved using a documented calculation.
- Export filtered results as CSV.
- Define an adapter boundary for Google Sheets without making it mandatory for
  the core API.

**Exit criteria:**

- Summary metrics match persisted claim and decision data.
- CSV export has stable headers and safe values.
- Reports can be filtered by date, category, employee reference, and status.
- Export failures are explicit and do not alter claim state.

## Cross-cutting error and reliability rules

- Invalid client input returns a typed 4xx error with field-level details.
- Domain rule failures are represented as signals, not unexpected exceptions.
- Provider timeouts and rate limits are classified as retryable.
- Persistence failures fail the operation explicitly; they must not produce a
  success-shaped response.
- Retries are bounded and recorded in the processing run.
- A failed step does not erase successful earlier steps.
- A terminal decision is immutable; corrections create a new decision event.
- Logs use claim/run IDs and safe metadata, never raw receipt content or secrets.

## Testing strategy

### Unit tests

- Domain status transitions.
- Validation and policy rules.
- Duplicate matching and anomaly scoring.
- Decision precedence.
- Masking and provider error classification.
- Report aggregation.

### API tests

- Claim creation and retrieval.
- Invalid upload handling.
- Processing and retry behavior.
- Clarification answer flow.
- Review decision flow.
- Timeline ordering.
- Summary and CSV export.

### Contract and integration tests

- Repository implementations against the selected database.
- Provider adapters against mocked external responses.
- Schema compatibility between backend responses and frontend consumers.
- Idempotency under repeated requests.

### Acceptance fixtures

The backend test fixtures should cover the six BRD scenarios:

1. Valid meal claim of Rp60.000 is auto-approved.
2. Meal claim of Rp240.000 requests participant count before recalculation.
3. Identical parking receipt is rejected or flagged as duplicate according to policy.
4. Blurry or unreadable receipt retries and then requests a new image.
5. Claim above Rp500.000 is escalated.
6. Unusual employee spending pattern is flagged with evidence.

All fixtures must be synthetic or anonymized.

## Implementation order

The recommended dependency order is:

```text
M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8
```

M6 is shown after M5 because the user-facing clarification and review flows
make the required timeline concrete, but persistence interfaces should be
introduced in M0 and used incrementally from M1 onward. M7 is intentionally
late: external AI must enrich a stable deterministic pipeline, not define it.

## Definition of done for the backend roadmap

The roadmap is complete when:

- All FR-01 through FR-15 have an implemented path or an explicitly tested
  adapter boundary.
- Every final decision has structured reasons and an audit trail.
- Deterministic validation remains available when external providers fail.
- Synthetic acceptance fixtures pass.
- No real receipts, personal data, credentials, or provider secrets are stored
  in the repository.
- API behavior is documented sufficiently for the SvelteKit frontend to use it.

## Related documents

- [[../../BRD_Expense_Reimbursement_Agent|Business requirements]]
- [[../../architecture/overview|Architecture overview]]
- [[../../architecture/agent-flow|Target agent flow]]
- [[2026-09-30-expense-agent-repository-setup-design|Repository setup design]]
