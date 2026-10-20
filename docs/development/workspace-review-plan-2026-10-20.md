# Workspace refresh and PR review

The user approved the clean workspace direction on 20 October 2026 and requested
review, fixes, verification, and pushes for the current open pull requests.

## Approved design

- Keep the Tera logo, Plus Jakarta Sans, teal actions, white panels, and named
  tokens from `DESIGN.md`. ENERGY 2 / RHYTHM 2 / MOTION 1.
- Expose Dashboard in workspace navigation. Separate claim overview from intake.
- Dashboard shows real authorized claim counts, searchable recent claims, and
  actionable follow-ups. Never replace failed requests with fabricated data.
- Intake uses one file-selection area, a clear submit action, and contextual
  processing/results. Show text entry when a clarification requires an answer.
- Use the remaining desktop space for receipt guidance and claim context;
  stack the same information on mobile. Preserve upload retry, idempotency,
  replacement, clarification, and decision behavior.
- Keep review and report actions connected to backend permissions and outcomes.

## Execution plan

1. Preserve and review the three pre-existing local UI changes.
2. Review open PRs #10, #29, #30, #31, #32, and #33 against their merge bases,
   repository standards, PR scope, and documented requirements. Use separate
   Standards and Spec reviewers. `docs/agents/issue-tracker.md` is absent;
   GitHub PR metadata and repository requirements supply the review context.
3. Bring the reviewed dashboard/report, queue-consistency, and accessibility
   work into the UI branch without changing the published history.
4. Implement the workspace changes and regression fixes. Add behavior tests
   for correctness bugs; use browser verification for layout and interaction.
5. Run frontend checks, tests, production build, and backend regression suite.
   Inspect desktop and 320/375/414/768px layouts, error/empty states, upload,
   clarification, receipt inspection, review confirmation, and report filters.
6. Re-review the final diff, resolve actionable findings, commit using the
   configured Git identity, push changes, and update the affected PRs.
7. Report remaining external blockers or review limits explicitly. No merge to
   main is part of this change; reviewed fixes stay available in pull requests.

## Acceptance

The workspace must reveal the user's next action without duplicated upload
instructions or unused chat space. Existing authorized flows must remain
operable on mobile and desktop. Review findings must have a fix or an explicit
reason they remain unresolved, and reported checks must match actual results.
