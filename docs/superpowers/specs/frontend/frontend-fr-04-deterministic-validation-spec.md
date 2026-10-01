# Frontend FR-04 — Deterministic Validation

## Goal

Present validation findings returned by the backend without duplicating rules.

## Surface

Claim detail validation panel and timeline step.

## Behavior

Group findings by pass, warning, and blocking failure. Each finding displays a
stable reason label, affected value, and backend explanation.

## Acceptance criteria

- Every returned validation finding is visible.
- Blocking findings are distinguishable from informational findings without
  color alone.
- The panel identifies whether employee action is required.
- Client-side display logic cannot change the claim decision.

