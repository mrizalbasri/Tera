# Frontend FR-01 — Receipt Upload

## Goal

Allow an employee to create a claim by selecting a JPG, PNG, or PDF receipt and
submitting only valid, size-compliant files to `POST /claims`.

## Surface

Route: `/claims/new`. Components: file picker, receipt preview/metadata panel,
claim fields, submit button, and inline error summary.

## Behavior

Validate file type and size before submission, show filename and readable
metadata, preserve the selected file while the request is pending, and disable
duplicate submissions. On success navigate to the claim detail route. On
failure retain the form and show the server error.

## Acceptance criteria

- Invalid media types and oversized files are rejected before upload.
- Keyboard users can select and remove a file.
- Upload progress or a pending state is visible.
- No receipt bytes or personal data are logged by the UI.
- A successful response produces a claim ID and navigates to its detail page.

