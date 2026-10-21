# Ruang kerja karyawan dan finance

User approved this direction in conversation on 2026-10-21 after reviewing the BRD and PRD.

- Keep one application and verified session. Employee routes lead with receipt submission and personal history. Finance routes lead with exception review, all claims, summary, and reports.
- Preserve backend authorization. Workspace links change presentation only; employee accounts cannot gain finance access. Demo links are available only when the backend grants demo/admin access.
- Finance history includes all authorized claims and retains finance navigation while reading evidence. Personal history remains scoped to the current employee.
- Review queue defaults to open work, oldest first. Resolved decisions remain accessible through all claims. Clarification belongs to employees; finance may inspect its evidence without impersonating an employee.
- Approval is a claim decision, not payment confirmation. Use existing mint/teal tokens, typography, visible keyboard focus, and responsive controls. ENERGY 2 / RHYTHM 2 / MOTION 1.
- Validate route authorization, workspace selection, list scopes, queue behavior, frontend tests, Svelte checks, and production build. Browser access was previously blocked by browser policy; report any remaining visual verification limitation honestly.
