# Workspace refresh and open-PR review

Review date: 20 October 2026. Scope: open PRs #10, #29, #30, #31,
#32, and #33, plus the three pre-existing local UI changes. Changes remain
in pull requests; no PR was merged into `main`.

## Reviewed baselines

| PR | Original head | Base / merge base | Scope |
| --- | --- | --- | --- |
| #10 | `c4da4da` | `58b749a` | Diagram compression |
| #29 | `e294530` | `1478007` | Dashboard search, report filters, review confirmation |
| #30 | `01b6eb4` | `1478007` | Partial receipt evidence and OCR evaluation |
| #31 | `b4b0706` | `1478007` | Complete, consistent review queue and saved decisions |
| #32 | `49415d3` | `1478007` | Upload, mobile accessibility, clarification failure retention |
| #33 | `d6e24e2` | `1478007` | Receipt preview, intake, history, reports, landing motion |

Standards and Spec were reviewed independently. `docs/agents/issue-tracker.md`
is absent; PR metadata, `CONTRIBUTING.md`, `DESIGN.md`, and the frontend team
task documents supplied the available standards and requirements.

## Standards

1. **#33, Unicode receipt headers:** raw filenames could raise a Latin-1
   encoding error. Content responses now use an ASCII fallback and UTF-8
   `filename*`, with `no-store` and `nosniff`. The frontend proxy retains the
   content disposition. Regression coverage includes Unicode and a receipt
   requested through a different claim.
2. **#33, keyboard preview:** the lightbox did not transfer or restore focus.
   It now uses the existing modal focus action. Browser verification confirms
   focus on Close, Escape dismissal, and focus restored to the trigger.
3. **#29, controls:** report buttons overrode the documented minimum with 36px.
   Controls now use 44px minimum targets and spacing tokens, preserving focus
   indicators. The isolated dashboard branch contains its own correction.

No additional actionable Standards finding was identified in the first pass
of #10, #30, #31, or #32. Cosmetic smell heuristics did not justify unrelated
refactoring.

## Spec

1. **#30, field uncertainty:** “vendor clear and unreadable date” invalidated
   the vendor. Predicate boundaries now associate the leading adjective with
   the following field, while preserving coordinated subjects. Added cases
   exercise both directions and ampersand wording.
2. **#33, PDF preview:** PDF uploads exposed image-only controls. Rotation and
   image enlargement are now shown only for images; PDFs retain their iframe
   and original-file link. Browser inspection found one PDF frame and no
   image enlargement control.
3. **#29/#31/#33, saved review:** refreshing a decided claim depended on an
   open-queue entry and hid the result. The detail view now renders the saved
   claim and decision without requiring an open review. Submission errors stay
   beside the evidence, with a reload action, rather than replacing the page.
4. **#33, queue integration:** the simpler pagination implementation omitted
   #31's snapshot, count, and overlap protections. The complete #31 change is
   integrated, including backend membership verification and regressions.
5. **Intake:** processing and outcomes remain inline, text entry appears for
   clarification, retry controls expire after successful processing, and a
   clarification response also renders the complete decision banner.
6. **Dashboard:** authorized claims are paginated before aggregation and
   filtering. Search runs before the eight-row display limit and understands
   Indonesian status names. Employees receive their own backend-authorized
   claims; review/report controls remain restricted to admins.
7. **Replacement evidence, second review:** uploading a clearer receipt could
   replay the old waiting run and re-read superseded evidence. Receipts now
   retain their replacement relationship; claims and processing runs track
   the receipt revision. An explicit process request starts a new run for new
   evidence. Historical receipts remain available for audit; other receipts
   in a multi-receipt claim remain active. The replacement endpoint replaces
   the most recently appended active receipt. Tied timestamps are tested with
   deliberately reverse-ordered UUIDs, so UUID ordering cannot select the wrong
   receipt. Superseded open questions/reviews are cancelled without recording
   an invented answer or human decision. Recovery still waits for explicit
   input. Repeating a completed process request replays its saved decision.

#10 preserves all four PNGs' decoded dimensions and RGBA bytes, and all four
SVGs' text contents. No image-content correction was needed. #31 and #32
remain separately reviewable and are integrated into #33. The PR #33 body is
updated to describe supported reference/employee/amount/status search rather
than promising vendor/notes search unavailable in the claim list contract.

## Visual verification

The design follows the user's approved clean workspace direction and
`DESIGN.md`: teal actions, the existing receipt mark and Plus Jakarta Sans,
quiet navigation, real claim status, and a narrower contextual rail. ENERGY 2,
RHYTHM 2, MOTION 1. The dashboard's primary action is claim intake; the rail
connects pending claims directly to their next action. No invented metrics,
identities, customer claims, or new illustration assets were introduced.

- Desktop dashboard: [screenshot](screenshots/tera-dashboard-2026-10-20.jpg).
- Desktop intake: [screenshot](screenshots/tera-intake-desktop-2026-10-20.jpg).
- Mobile intake: [screenshot](screenshots/tera-intake-mobile-2026-10-20.jpg).
- Dashboard, intake, history, reviews, and reports were checked at widths
  320, 375, 414, 768, and 1440px. All 25 document/main bounds fit the viewport;
  wide tables scroll inside their own region.
- Browser smoke tests exercised sample selection, actual PNG upload,
  low-confidence clarification, clearer receipt upload on the same claim,
  processing without forced navigation, image focus/Escape, mobile menu
  focus/Escape, PDF controls, blank review reason, cancellation, save, and
  persistence after refresh. Duplicate detection correctly remained active
  on synthetic receipts with matching attributes.
- Report validation rejected a reversed date range. Applied employee filters
  matched the summary; direct API verification returned HTTP 200 and exactly
  one CSV row for the selected employee. The browser automation did not
  observe the download event, so browser file-save behavior is not claimed
  as verified.
- No error console entries were recorded for the final intake page.

The scoped design audit found clear hierarchy, purposeful whitespace, existing
brand identity, explicit loading/error/empty states, and usable focus controls.
Pre-emit assessment: Philosophy 4, Hierarchy 5, Execution 4, Specificity 5,
Restraint 5, Variety 4. Legacy styles outside this workspace scope remain.

## Automated validation and limits

- Frontend: 66 tests passed; Svelte check returned 0 errors and 0 warnings;
  production build succeeded.
- Backend final full suite: 540 passed, 53 skipped. The focused receipt/report
  suite passed all eight tests, including the additional review-queue and
  tied-timestamp cases.
- Isolated #30: 79 privacy/extraction tests passed.
- Isolated #29: 29 frontend tests passed, check returned 0 errors and
  0 warnings, production build succeeded.
- PostgreSQL-specific tests require `TEST_POSTGRES_URL` and were skipped.
  Memory and SQLite paths were tested. Browser testing used local demo/mock
  providers and synthetic fixtures; live vision and production Clerk login
  were not exercised. No local `.env`, credentials, downloaded receipt data,
  or temporary fixture scripts are included in the changes.
- JSON model additions have defaults for existing records. No database DDL
  migration is needed. The added `cancelled` review status and receipt revision
  metadata should ship with the corresponding backend and frontend together.
  Legacy replacement records are not retroactively linked. An older backend
  with strict JSON validation requires removal of the added metadata before
  rollback; a frontend rollback can retain this compatible backend.
