# FR-07 — Anomaly Scoring

## Requirement

Score unusual claim patterns using historical claim data and expose evidence
for the score.

## Initial implementation

Start with a deterministic rule-based scorer over synthetic history. Keep the
interface replaceable by an ML model after enough labeled data exists.

## Signals

- Unusual amount for the category.
- Unusual claim frequency.
- Repeated vendor/date/amount.
- Deviation from the employee's historical pattern.

## Result contract

Score, severity, triggered rules, evidence, scorer version, and explanation.

## Acceptance criteria

- Same input history produces the same score.
- Score factors are visible and auditable.
- Missing history produces a safe neutral result.
- High anomaly score can trigger escalation but cannot silently approve.

## Tests

Normal history, high amount, high frequency, repeated pattern, no history,
threshold boundary, and scorer version compatibility.
