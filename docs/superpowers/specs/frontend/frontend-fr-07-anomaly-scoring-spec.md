# Frontend FR-07 — Anomaly Scoring

## Goal

Display anomaly risk and evidence in a way that supports review without
pretending the score is a definitive accusation.

## Surface

Risk summary on claim detail and reviewer detail.

## Behavior

Show risk level, score where available, contributing evidence, and the action
implied by the backend decision. Use neutral language such as “requires
review” rather than labeling an employee fraudulent.

## Acceptance criteria

- Risk level is available in text and accessible markup.
- Evidence is grouped and readable on small screens.
- A high-risk claim links to the review action when escalated.
- Score formatting is consistent across employee and reviewer views.

