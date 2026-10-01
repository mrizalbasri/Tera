# Frontend FR-11 — Claim and Audit Persistence

## Goal

Make the persisted claim state and audit context visible and trustworthy.

## Surface

Claim list, claim detail, and timeline.

## Behavior

Load the current claim from `GET /claims/{claim_id}` and refresh after actions.
Display timestamps, current status, and links to historical runs when the API
provides them.

## Acceptance criteria

- Refreshing the detail route reconstructs the same current claim state.
- Stale data is marked or refreshed after a mutation.
- Missing claims produce a meaningful not-found state.
- Audit data is read-only in the frontend.

