# FR-05 — Policy Retrieval and Evaluation

## Requirement

Check claims against versioned policy documents or rules for limits,
categories, and required conditions.

## Backend behavior

- Retrieve the policy relevant to claim category and date.
- Evaluate limits, required receipts, prohibited items, and conditions.
- Return rule-level results with policy version.
- Begin with local policy data and keep retrieval behind an interface for RAG.

## Initial rules

Meals, fuel, toll/parking, hotel, maximum claim age, receipt requirement, and
prohibited alcohol.

## Interfaces

- `PolicyRetriever`
- `PolicyEvaluator`
- `GET /policies/{policy_id}` when policy administration is introduced.

## Acceptance criteria

- Policy version is recorded on every evaluation and decision.
- Each violation has a stable reason code and explanation.
- Policy retrieval failure is explicit and cannot create approval.
- Rules are testable without an external vector store.

## Tests

Category limit, missing receipt, prohibited item, expired policy, no matching
policy, and policy version selection.
