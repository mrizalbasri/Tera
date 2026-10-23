# Role workspace visual QA — 2026-10-23

Follow-up to [the initial validation](role-workspaces-validation-2026-10-21.md) for PR #34, `fix/role-workspaces`.

## Environment and coverage

Rendered in the Codex in-app Chromium browser against this branch's SvelteKit dev server at `http://127.0.0.1:5174`, with an isolated FastAPI demo server at port 8001. Backend configuration: `DEMO_MODE=true`, `FRONTEND_ORIGIN=http://127.0.0.1:5174`, memory storage and mock providers. All receipts and identities in the captures are synthetic.

Viewport overrides were 1440×1000 desktop, 375×812 phone, 320×812 narrow phone, 414×896 wider phone and 768×1024 tablet. These are browser viewport checks with keyboard/mouse input, not physical-device or synthesized-touch tests. Native scrollbars reduce available layout width by 15px on scrolling pages. The viewport override was reset after QA.

| Surface | Rendered checks | Screenshot evidence |
| --- | --- | --- |
| `/pengajuan` | Desktop and 375px; upload instructions, demo sample selection, processing and completed submission | [Desktop](screenshots/role-workspaces-2026-10-23/employee-submission-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/employee-submission-mobile-375.jpg), [result](screenshots/role-workspaces-2026-10-23/employee-submission-result-mobile-375.jpg) |
| `/riwayat` | Desktop and 375px; initially empty, then populated; personal scope, search with no matches, contained table overflow, search focus | [Desktop](screenshots/role-workspaces-2026-10-23/employee-history-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/employee-history-mobile-375.jpg) |
| `/riwayat/[id]` | Desktop and 375/414px; image evidence, employee navigation and clarification link | [Desktop](screenshots/role-workspaces-2026-10-23/employee-evidence-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/employee-evidence-mobile-414.jpg) |
| `/claims/[id]/clarification` | Desktop and 414px; employee context, empty answer disables submit, entering an answer enables it | [Desktop](screenshots/role-workspaces-2026-10-23/employee-clarification-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/employee-clarification-mobile-414.jpg) |
| `/reviews` | Desktop and 320px; populated and empty queue, evidence dialog, navigation, saved approval removes the open review | [Desktop](screenshots/role-workspaces-2026-10-23/finance-queue-desktop-1440.jpg), [narrow navigation](screenshots/role-workspaces-2026-10-23/finance-navigation-mobile-320.jpg) |
| `/reviews/[claimId]` | Desktop, 320/414px and 768px; image beside extraction on desktop, stacked evidence on smaller screens, confirmation validation/cancel/save | [Desktop](screenshots/role-workspaces-2026-10-23/finance-review-desktop-1440.jpg), [320px](screenshots/role-workspaces-2026-10-23/finance-review-mobile-320.jpg), [decision controls](screenshots/role-workspaces-2026-10-23/finance-decision-mobile-320.jpg), [tablet](screenshots/role-workspaces-2026-10-23/finance-review-tablet-768.jpg), [saved decision](screenshots/role-workspaces-2026-10-23/finance-review-saved-desktop-1440.jpg) |
| `/admin/claims` | Desktop and 375px; includes both synthetic employees, personal list excludes the second employee | [Desktop](screenshots/role-workspaces-2026-10-23/finance-claims-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/finance-claims-mobile-375.jpg) |
| `/admin/claims/[id]` | Desktop and 375px; finance navigation retained, related claim remount changes heading/receipt, clarification waits on employee, image zoom opens and Escape restores focus | [Phone evidence](screenshots/role-workspaces-2026-10-23/finance-evidence-mobile-375.jpg) |
| `/dashboard` | Desktop and 375px; populated summary, recent claims, reviewer follow-up links | [Desktop](screenshots/role-workspaces-2026-10-23/finance-summary-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/finance-summary-mobile-375.jpg) |
| `/reports` | Desktop and 375px; filter layout, report summaries; employee filter returns one expected synthetic employee claim | [Desktop](screenshots/role-workspaces-2026-10-23/finance-reports-desktop-1440.jpg), [phone](screenshots/role-workspaces-2026-10-23/finance-reports-mobile-375.jpg) |

## Issues fixed

1. **Approval text lacked contrast.** Workspace CSS made `.approve` text nearly white while the review page retained a pale green background. Use the existing primary teal background/border and dark teal hover token alongside the inverse text.
2. **Review heading collapsed into a narrow column.** A long UUID competed with the status badge in a non-wrapping flex row. Allow the header to wrap and give the title a flexible 320px basis. Long detail links also wrap inside their panel.
3. **Narrow finance navigation exceeded its cells.** Two fixed columns and non-wrapping labels squeezed “Antrean review” beyond its cell. Columns now fit available space, becoming a single column at 320px; labels can wrap.
4. **The body clipped 15px at 320px.** The base 320px minimum body width competed with the native scrollbar. Override that minimum so the workspace fits the available layout width. After the fix, document `scrollWidth` and `clientWidth` both measured 305px at the 320px viewport. At 375px both measured 360px. Wide claim tables retain their own horizontal scroll region.
5. **Filters and evidence tools were too short.** History status buttons were 32px, search inputs could be reduced to 28px by workspace CSS, and receipt tools were 28px. All now measure at least 44px. Remove the history search's local `outline: none` so the existing visible focus ring applies.
6. **Saving a decision relabeled the reviewer reason as the escalation reason.** The browser approval check exposed this state transition: the queue item's latest decision changed after saving. The escalation section now reads the latest `escalated` entry from claim decision history; the decision banner continues to show the saved reviewer explanation. Verified immediately after approval and after reloading.

The existing teal/mint palette, typography, bordered workbench panels, role separation and payment distinction remain intact.

## Interaction and validation results

- Mobile employee and finance menus open; Escape closes them and restores focus to Menu. Selecting a destination closes the menu.
- Image previews loaded successfully. Zoom opens and Escape closes it, restoring focus to its trigger.
- Demo sample submission completed through the browser. An initial 403 was a QA configuration error: the backend still allowed port 5173. Restarting the isolated backend with the matching 5174 origin resolved it; no origin protection was changed in code.
- Reviewer approval was disabled without a reason, enabled after entering one, saved successfully and removed the claim from the open queue. Cancellation was also exercised.
- Browser error/warning logs were empty on the final review-page check.
- `pnpm check`: 0 errors, 0 warnings.
- `pnpm test`: 79 tests passed across 11 files.
- `pnpm build`: passed.
- `git diff --check`: passed.
- Impeccable source detector: two warnings for pre-existing accent borders in `workspace.css` and claim clarification history. Retained to preserve the existing design direction; neither was introduced by this QA patch.

The 23 screenshots cover multiple stages of disposable demo state, including a backend restart and an approval. Counts and claim references therefore vary between captures. They are fresh browser screenshots of this PR's implementation, not production records or simulated UI images.

## Remaining limits

The native embedded PDF viewer remained blank in the in-app browser at desktop and phone sizes. The PDF iframe and existing open-original links were present, but successful PDF page rendering is **not** claimed. Verify native PDF display in a regular supported browser before treating that sub-check as passed. Image evidence rendering is verified.

Physical touch gestures, other browser engines, production Clerk sessions and real payment flows were not exercised. Clarification form validation was checked without submitting its answer. Backend source, permissions, persistence and API contracts were not changed.
