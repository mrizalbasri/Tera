# FR-08 — Explainable Claim Decision

## Requirement

Produce approved, rejected, needs clarification, or escalated outcomes with
structured reasons.

## Decision precedence

1. Missing or invalid required data -> `needs_clarification`.
2. Confirmed duplicate -> `rejected`, unless reviewed override exists.
3. Policy violation -> `rejected`.
4. High anomaly, confidence below 0.8, or amount above Rp500.000 ->
   `escalated`.
5. Otherwise -> `approved`.

Approval requires all mandatory checks to pass, confidence at least 0.8, no
blocking signal, and amount at or below Rp500.000.

## Decision record

Outcome, reason codes, explanation, confidence, anomaly score, source signals,
policy version, processing run, actor type, and timestamp.

## Acceptance criteria

- No decision lacks a reason.
- Decision behavior is deterministic for fixed inputs.
- Provider output cannot directly set the outcome.
- Human overrides create a new decision record.

## Tests

All outcomes, conflicting signals, threshold boundaries, policy violation,
duplicate, low confidence, and anomaly escalation.
