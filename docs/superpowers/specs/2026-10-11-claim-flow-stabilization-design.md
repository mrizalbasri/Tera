# Claim flow stabilization

Scope follows the owner's approval to stabilize the existing pipeline and connect
the frontend before ML and reporting work.

Keep Tera's green identity and Indonesian interface. Use a responsive sidebar,
clear page headings, compact status badges and readable evidence panels. Build
on the existing SvelteKit/FastAPI contracts instead of calculating decisions in
the browser. Keep the existing `/riwayat` and `/review` URLs.

The home page submits receipt files and employee reference, then opens the saved
claim. Processing is a separate explicit action on the claim detail page, so a
provider failure cannot cause the user to resubmit an already saved receipt.
Retain the intake idempotency key while retrying the same form. Clear it when
inputs change. Do not store receipt bytes or employee references in localStorage.

History uses an explicit employee-reference filter; it does not load all claims
automatically. Detail shows receipts, extraction fields/confidence, latest
decision, validation/policy findings, signals, clarification and redacted timeline.
Review uses the backend's open queue, requires reviewer identity and reason,
and asks for confirmation before persisting approve/reject. All request failures
remain visible with retry; successful mutations refresh persisted state.

Use a same-origin SvelteKit API proxy with a server-only configurable backend
origin to avoid browser CORS/environment mismatches in dev and production.
This prototype's reference fields are not authentication or authorization.

Fix issue #12 by classifying Decimal failures during line-item derivation as
non-retryable malformed extraction. No mock fallback, raw numeric values or
provider output in errors. Limit model totals and quantities to 18 decimal
digits with at most six fractional digits before any arithmetic/formatting,
and revalidate structured model instances. Test full processing failure, saved FAILED run,
idempotent replay and retry with corrected output, plus quantity precision cases.

Validate backend pytest, frontend check/build and browser smoke on synthetic
data with mock providers. PostgreSQL integration tests require an isolated test
server and must not use the application's database.
