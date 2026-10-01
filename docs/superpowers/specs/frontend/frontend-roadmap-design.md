# Expense Agent Frontend Roadmap

## Status

Proposed frontend specification for FR-01 through FR-15. This document defines
the SvelteKit surface that consumes the FastAPI contracts described in the
backend roadmap.

## Frontend responsibilities

The frontend owns employee and reviewer interaction, file selection, form
validation, claim status presentation, clarification conversation, review
actions, timeline visualization, reporting filters, and accessible error
feedback. Business decisions remain authoritative in the backend.

The frontend must not duplicate policy, anomaly, duplicate, or decision logic.
It may explain backend-provided reason codes and display calculated values, but
must never present a locally calculated result as the official decision.

## Proposed routes

| Route | User | Purpose |
|---|---|---|
| `/` | Employee | Claim list and entry point |
| `/claims/new` | Employee | Upload a receipt and submit a claim |
| `/claims/[claimId]` | Employee/reviewer | Claim detail, decision, and timeline |
| `/claims/[claimId]/clarification` | Employee | Answer an open clarification |
| `/reviews` | Reviewer | Review queue for escalated claims |
| `/reviews/[claimId]` | Reviewer | Inspect and decide an escalated claim |
| `/reports` | Manager/admin | Summary metrics and filtered export |

## Shared frontend boundaries

```text
frontend/src/
  lib/
    api/          # typed FastAPI client and error normalization
    components/   # status badge, timeline, file picker, metric card
    formatters/   # currency, date, reason-code labels
    types/        # API response and UI view types
  routes/         # route-level data loading and actions
```

The initial implementation should use SvelteKit route loading and form
actions/fetch with local component state. A state-management library is not
needed until multiple routes require shared live updates.

## Shared interaction rules

- Show a visible loading state for every request that may take longer than one
  animation frame.
- Preserve entered form data when a request fails.
- Normalize API errors into a short user message plus field-level details when
  available.
- Use backend status and reason codes as the source of truth.
- Make status, confidence, and risk understandable without relying on color.
- Never render raw receipt content, provider payloads, or unmasked sensitive
  values in debug output.
- Every destructive or irreversible reviewer action requires confirmation.

## Milestones

1. **Foundation:** shared types, API client, status presentation, base layout.
2. **Intake:** claim list, upload form, receipt quality feedback.
3. **Processing:** claim detail, decision explanation, agent timeline.
4. **Exceptions:** clarification conversation and reviewer queue.
5. **Operations:** reports, filtering, and CSV export.

## Frontend acceptance baseline

- `pnpm check` passes.
- `pnpm build` passes.
- All routes have loading, empty, error, and retry states where applicable.
- Keyboard users can complete upload, clarification, and review flows.
- API failures never appear as successful claims or decisions.
- UI behavior is covered with route/component tests when the test harness is
  introduced.

## FR mapping

| FR | Frontend surface |
|---|---|
| FR-01 | Upload form and quality result |
| FR-02 | Extraction fields and confidence |
| FR-03 | Retry progress and retake request |
| FR-04 | Validation findings |
| FR-05 | Policy findings and limits |
| FR-06 | Duplicate warning |
| FR-07 | Anomaly score and evidence |
| FR-08 | Decision result and reasons |
| FR-09 | Clarification conversation |
| FR-10 | Reviewer queue and escalation |
| FR-11 | Claim detail and persisted status |
| FR-12 | Agent processing timeline |
| FR-13 | Safe display and privacy states |
| FR-14 | Reports and CSV export |
| FR-15 | Claim history and conversation context |

