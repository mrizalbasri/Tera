# Frontend FR-05 — Policy Evaluation

## Goal

Explain how the claim was evaluated against the active policy version.

## Surface

Policy result panel on claim detail.

## Behavior

Show policy version, evaluated rule, actual value, limit, result, and
explanation. Avoid exposing internal retrieval prompts or provider payloads.

## Acceptance criteria

- Passed and failed rules are separately scannable.
- A failed rule includes the limit and actual value when provided.
- The active policy version is visible.
- Policy text is presented as an explanation, not an editable client rule.

