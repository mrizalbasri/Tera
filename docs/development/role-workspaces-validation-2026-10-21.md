# Role workspace validation, 2026-10-21

## Result

Employee navigation now leads with Pengajuan baru and Klaim saya. Finance navigation leads with Antrean review, Ringkasan, Semua klaim, and Laporan. The header explicitly identifies Panel admin or Ruang karyawan. Authorized admins can move between workspaces; demo labels identify Demo Karyawan and Demo Admin.

`/admin/claims` loads all authorized claims and shows employee identifiers. `/riwayat` retains its employee filter. Finance evidence stays under `/admin/claims/[id]`; related claim navigation remounts the evidence view when the ID changes. Clarifications display as waiting on the employee in finance evidence.

Review detail displays the latest receipt beside its extracted fields, escalation explanation, and the saved decision controls. The queue retains only open reviews and prioritizes the oldest review creation time. Approval copy explicitly distinguishes a claim decision from payment.

## Validation performed

- `pnpm test`: 79 tests passed across 11 files, including new workspace context and anonymous/member route restrictions for both finance list and detail.
- `pnpm check`: 0 errors, 0 warnings.
- `pnpm build`: passed.
- Local readiness: `/reviews`, `/pengajuan`, `/riwayat`, `/admin/claims`, `/dashboard`, `/reports` returned HTTP 200 in demo mode.
- Seeded three explicitly synthetic demo receipts after confirming `demo_mode=true`: one escalated claim and one clarification for `salesman-001`, plus one approved PDF claim for a second demo employee. This makes the finance queue and personal/all-claims distinction reviewable. These records exist only in demo memory and disappear on backend restart.
- `git diff --check`: passed.
- Backend code and API contracts were not changed. Existing backend role/ownership checks remain the authority. No role-switch URL changes account privileges.

## Design verification limits

The prior browser call was rejected by browser security policy. No alternate browser surface or shell screenshot workaround was used. Fresh visual screenshots, responsive click-through, image/PDF rendering, and keyboard interaction checks remain unverified for this revision. Build success and HTTP readiness do not substitute for these checks. The new PR is a draft pending visual review.

Design follows the existing DESIGN.md: teal/mint for actual hierarchy and selection, established typography, bordered surfaces, and ENERGY 2 / RHYTHM 2 / MOTION 1. Workspace controls wrap, evidence columns collapse at 900px, and mobile navigation retains its existing Escape behavior. These are source-level checks, not a claim of completed visual QA.

No credentials, personal receipts, database changes, payment integration, or extra approval roles were added.
