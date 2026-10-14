# Tera design system

Source: the user's Expense Agent Brand Identity Showcase and clean website references, approved on 2026-10-13. Product name: **Tera**, always with an uppercase T.

## Direction

Modern-minimal, confident sans-serif typography, cool white surfaces, deep teal, and restrained mint. ENERGY 2 / RHYTHM 2 / MOTION 1. The existing receipt logo is the identity asset; its gradient and sparkle belong to the mark, not to every control.

- Marketing: an asymmetric product-led introduction, interactive illustrative receipt workflow, two audience sections, and a compact closing invitation.
- Application: a workbench with quiet navigation, clear page headings, readable tables, and a single primary action for each task.
- Display and body: Plus Jakarta Sans, already used by the project, with Segoe UI fallback. Its compact, rounded forms match the brand reference; weight and scale distinguish headings from data.
- Background #FAFCFB; primary #0F766E; accent #14B8A6; mint #A7F3D0; light #E6F4F1. Dark teal and neutral text maintain readable contrast. Status colors convey actual outcomes.
- Named tokens live in frontend/src/lib/tokens.css. Existing variable names remain aliases so current components share the system.
- A 4px spacing scale, 8px input/button corners, 12px panels, and 44px minimum controls. Tables scroll inside their own region on small screens.
- No glass, decorative pulsing status dots, repeating gradients, invented identities, metrics, or testimonials. Landing workflow samples are explicitly labelled illustrations.
- Updated hero direction: the user explicitly requested the curved white receipt, dimensional folds, mint sparkle, halftone ribbon, and light/dark campaign compositions in their Tera brand board. These are deliberate brand motifs, used on the landing hero and closing campaign only. The generated paper is a transparent foreground asset; checklist text and controls remain HTML. Pill CTAs and the halftone ribbon are retained here to match that explicit reference.
- Motion includes a short staggered hero entrance, a one-time reveal as sections enter the viewport, subtle CTA hover movement, and a collapsing mobile navigation panel. Reduced motion disables these transitions and reveals content immediately. Keyboard focus is immediate and visible.
- Mobile navigation uses an accessible hamburger that becomes an X. Escape closes it and restores focus; choosing a destination closes it too. The receipt caption was removed at the user's explicit request; the checklist retains its “Contoh alur Tera” heading.
- Navbar refinement follows the user's dropdown reference: a white floating bar stays sticky with a small inset from the top. Product opens a two-column panel with a mint introduction and four real application links. On mobile it becomes an inline submenu beneath the hamburger. Escape, clicking outside, and leaving the header by keyboard close the product panel. Closed submenu links are inert.
- The hero background extends behind the floating navbar; a vertical fade softens the top of the mint ribbon. Responsive navbar offsets preserve sticky positioning and keep the headline below the navigation. Reduced hero top padding connects the two areas without a horizontal background seam.
- At the user's request for stronger motion, paper and checklist float independently, checks arrive in sequence, ribbons drift slowly, and audience/FAQ content reveals with staggered timing. Loops pause outside the viewport and in hidden tabs; reduced motion removes the animations. Mobile uses a smaller paper movement.
- Background refinement: wider overlapping teal/mint arcs, a pale circular crop at the upper right, diagonal halftone and irregular ink grain follow the supplied brand board. Keep the light hero copy area clear; use stronger ink and emerald layers for the dark closing campaign. These SVG textures remain confined to the two brand compositions.

## Routes and scope

- `/`: landing page with real links into the application.
- `/pengajuan`: the existing receipt-processing conversation, extracted without removing its upload, retry, retake, clarification, or decision behavior.
- `/claims/new`, `/claims/[claimId]`, `/claims/[claimId]/clarification`: existing form and claim flows.
- `/riwayat`, `/riwayat/[id]`: history and evidence.
- `/reviews`, `/reviews/[claimId]`: review queue and human decisions.
- `/reports`, `/dashboard`: backend reports and real claim aggregates. No fabricated fallback metrics or charts.

## Validation

Run frontend check, tests, and production build. Inspect landing, navigation, workflow controls, upload validation, empty/error states, and CSV actions. Check widths 320, 375, 414, 768, and desktop, keyboard use, and console errors. Record the final Hallmark/antislop audit and verification limitations.
