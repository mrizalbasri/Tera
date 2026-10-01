# FR-15 — Employee and Vendor Claim Memory

## Requirement

Provide relevant claim history per employee/vendor and preserve conversation
context for the current claim.

## Memory boundaries

- Employee/vendor history is scoped to the authorized employee and vendor.
- Conversation context is scoped to one claim.
- Historical data is read as evidence, not as an automatic decision.
- Unrelated employee history must never be inserted into an agent context.

## Data used

- Prior claim dates and amounts.
- Prior vendors and categories.
- Prior duplicate/anomaly signals.
- Current claim clarification messages and answers.

## Interfaces

- `ClaimHistoryRepository`
- `ConversationContextRepository`
- History query in the processing service.

## Acceptance criteria

- History can be queried by employee and vendor.
- Claim context survives retries and clarification.
- Context has a bounded size and safe serialization.
- Missing history produces a neutral result.
- Memory data is visible in audit metadata without leaking unrelated records.

## Tests

Employee isolation, vendor history, empty history, context continuation,
bounded context, duplicate pattern lookup, and unrelated-data exclusion.
