# Frontend FR-02 — Extracted Fields

## Goal

Display backend-extracted vendor, date, total, category, line items, and
field-level confidence on the claim detail page.

## Surface

Route: `/claims/[claimId]`, extraction summary component.

## Behavior

Render values exactly as returned by the API, format currency and dates for
reading, and show confidence with text and a non-color indicator. Missing or
low-confidence fields must be obvious without implying that the employee
edited the receipt.

## Acceptance criteria

- All returned fields are displayed with labels.
- Low confidence is announced textually and linked to the relevant field.
- Empty fields show an actionable backend message rather than a blank card.
- The UI never calculates or overwrites the official extracted total.

