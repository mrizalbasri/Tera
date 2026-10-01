# Backend M4 — Risk and Decision Spec

## Purpose

Convert validation, policy, duplicate, and anomaly results into one
conservative, explainable outcome.

## FR coverage

FR-06, FR-07, and FR-08.

## Duplicate detection

- Exact duplicate by receipt content hash.
- Likely duplicate by vendor, receipt date, and amount.
- Configurable near-match similarity threshold.
- Evidence references the matching claim and compared fields.

## Anomaly scoring

Start with rule-based scoring over synthetic history. Signals may include
unusual amount, unusual frequency, repeated vendor/date/amount, and deviation
from employee history. The scorer must remain replaceable by an ML adapter.

## Decision precedence

1. Missing or invalid required data -> `needs_clarification`.
2. Confirmed duplicate -> `rejected`, unless a reviewer overrides it.
3. Policy violation -> `rejected`.
4. High anomaly, confidence below 0.8, or amount above Rp500.000 -> `escalated`.
5. Otherwise -> `approved`.

Approval requires all mandatory checks to pass, confidence at least 0.8, no
blocking signal, and amount at or below Rp500.000.

## Acceptance criteria

- Every decision contains reason codes and source signals.
- Duplicate and anomaly evidence appears in the decision detail.
- Same input, policy version, and history produce the same result.
- No provider can directly write a final decision.

## Tests

Exact duplicate, near duplicate, normal/anomalous history, policy conflict,
low confidence, over-threshold amount, and all four outcomes.
