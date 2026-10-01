# Frontend FR-08 — Decision Result

## Goal

Present approved, rejected, clarification, and escalated outcomes with clear
reasons.

## Surface

Decision banner on claim detail and claim list status.

## Behavior

Render the backend outcome, reason codes translated through a centralized
formatter, human-readable explanation, confidence, and next action. Terminal
decisions must include their timestamp and source.

## Acceptance criteria

- Every decision has a visible outcome and explanation.
- Status is not communicated by color alone.
- The next action is appropriate for the outcome.
- A failed API response never renders as an approved decision.

