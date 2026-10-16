# Tera receipt hero

The user explicitly requested the curved paper receipt, mint sparkle, teal/mint sweeping background and checklist composition shown in their brand reference. These brand motifs override the default preference against gradients and decorative sparkles.

The receipt is a transparent illustration generated with the built-in imagegen tool, saved at `frontend/static/brand/tera-receipt-curved.png`. The checklist, text, buttons and ribbon background are separate Svelte/HTML/SVG elements. Receipt amounts and checklist statuses are labeled as illustrative examples.

Generation prompt: Create a transparent foreground illustration for Tera's hero: exquisitely rendered white paper receipt with a strongly visible S-curve, curled corners, paper thickness and soft shadows, diagonal from top right to lower left. One secondary blank white ribbon curls at the upper right. Add a small dimensional four-point lime-mint sparkle at mid-right. Matte paper with subtle teal reflections, gray item lines, small Receipt, Total and Rp450.000 text. Square composition, centered, occupying 85 percent of the canvas, genuine alpha transparency. No UI cards, buttons, browser, people or floor.

Validation after integration: Svelte check returned zero errors and zero warnings; production build passed. Browser checks at 320, 375, 414, 768 and 1440 pixels found no horizontal document overflow and both receipt images loaded. No browser error/warning logs were reported. Desktop light hero, desktop dark campaign and mobile hero screenshots were saved in the task's visualization directory.

The supplied standalone component bundle was also rendered separately on port 5175 without changing its source. Desktop and mobile screenshots were saved separately from the revised project on port 5174.
