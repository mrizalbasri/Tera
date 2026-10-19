<script lang="ts">
	import { motionInView } from '$lib/actions/motionInView';
	let { compact = false }: { compact?: boolean } = $props();
	const checks = ['Nota diterima', 'Data dibaca', 'Kebijakan diperiksa', 'Duplikat ditinjau', 'Siap ditindaklanjuti'];
</script>

<figure use:motionInView class="receipt-artwork" class:compact>
	<div class="receipt-paper-wrap">
		<img class="curved-receipt" src="/brand/tera-receipt-curved.png" alt="Ilustrasi nota kertas putih melengkung dengan simbol Tera berwarna mint" width="1280" height="1280" fetchpriority={compact ? 'auto' : 'high'} loading={compact ? 'lazy' : 'eager'} />
		{#if !compact}
			<div class="ocr-scanner" aria-hidden="true">
				<div class="scan-laser"></div>
				<div class="ocr-tag tag-vendor"><span>SPBU Shell · 99%</span></div>
				<div class="ocr-tag tag-amount"><span>Rp 350.000 · 99%</span></div>
				<div class="ocr-tag tag-policy"><span>Plafon Sesuai ✓</span></div>
			</div>
		{/if}
	</div>
	<div class="receipt-checks">
		<div class="checks-heading"><img src="/logo.webp" width="24" height="24" alt="" /><span>Contoh alur Tera</span></div>
		<ul>{#each checks as check, index}<li style={`--check-delay: ${300 + index * 180}ms`}><span class="check-mark" aria-hidden="true">✓</span><span>{check}</span></li>{/each}</ul>
	</div>
</figure>

<style>
	/* Curved paper is the user's requested receipt motif; the checklist stays readable HTML. */
	.receipt-artwork { position: relative; min-width: 0; width: 100%; aspect-ratio: 1.06; margin: 0; isolation: isolate; }
	.curved-receipt { position: absolute; width: 94%; height: auto; top: -3%; right: -9%; object-fit: contain; z-index: 1; }
	.receipt-checks { position: absolute; top: 35%; left: -3%; width: 244px; padding: var(--space-5); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); box-shadow: var(--shadow-receipt); z-index: 2; transform: rotate(-3deg); }
	.checks-heading { display: flex; align-items: center; gap: var(--space-2); border-bottom: 1px solid var(--color-border); padding-bottom: var(--space-3); margin-bottom: var(--space-3); font-size: 11px; font-weight: 650; color: var(--color-ink); }
	.checks-heading img { object-fit: contain; }
	ul { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-4); }
	li { display: flex; align-items: center; gap: var(--space-3); font-size: 12px; color: var(--color-ink); line-height: 1.5; }
	.check-mark { width: 21px; height: 21px; flex-shrink: 0; display: grid; place-items: center; background: var(--color-primary); color: var(--color-inverse); border-radius: 50%; font-size: 12px; font-weight: 700; }
	.compact { aspect-ratio: 1.1; }
	.compact .curved-receipt { width: 94%; top: -7%; right: -5%; }
	.compact .receipt-checks { top: 36%; width: 220px; padding: var(--space-4); }
	.compact li { font-size: 11px; }
	.compact ul { gap: var(--space-3); }
	.receipt-paper-wrap { position: absolute; inset: 0; width: 100%; height: 100%; }
	.ocr-scanner { position: absolute; inset: 0; pointer-events: none; z-index: 3; }
	.scan-laser { position: absolute; top: 18%; left: 32%; width: 55%; height: 2px; background: linear-gradient(90deg, transparent, var(--color-mint), var(--color-accent), transparent); box-shadow: 0 0 10px var(--color-accent); opacity: 0; }
	.ocr-tag { position: absolute; padding: 3px 8px; background: rgba(16, 46, 43, 0.92); color: var(--color-mint); border: 1px solid var(--color-accent); border-radius: var(--radius-pill); font-size: 10px; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.2); white-space: nowrap; opacity: 0; transform: translateY(4px); }
	.tag-vendor { top: 24%; right: 12%; }
	.tag-amount { top: 46%; right: 8%; }
	.tag-policy { top: 66%; right: 16%; }
	@keyframes laser-sweep { 0% { top: 16%; opacity: 0; } 20% { opacity: 0.9; } 80% { opacity: 0.9; } 100% { top: 76%; opacity: 0; } }
	@keyframes tag-appear { 0%, 15% { opacity: 0; transform: translateY(4px); } 25%, 85% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; } }
	@keyframes paper-float { 0%, 100% { transform: translateY(0) rotate(-1deg); } 50% { transform: translateY(-18px) rotate(1.5deg); } }
	@keyframes checklist-float { 0%, 100% { transform: translateY(-5px) rotate(-3deg); } 50% { transform: translateY(7px) rotate(-1deg); } }
	@keyframes check-arrive { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: translateX(0); } }
	@keyframes check-stamp { 0% { transform: scale(.65); } 65% { transform: scale(1.15); } 100% { transform: scale(1); } }
	@media (prefers-reduced-motion: no-preference) {
		.curved-receipt { animation: paper-float 7s ease-in-out infinite; animation-play-state: paused; }
		.receipt-checks { animation: checklist-float 6s ease-in-out infinite; animation-play-state: paused; }
		.receipt-artwork:global(.motion-active) .curved-receipt, .receipt-artwork:global(.motion-active) .receipt-checks { animation-play-state: running; }
		.receipt-artwork:global(.motion-active) .scan-laser { animation: laser-sweep 5s ease-in-out infinite; }
		.receipt-artwork:global(.motion-active) .tag-vendor { animation: tag-appear 5s 0.6s ease-in-out infinite; }
		.receipt-artwork:global(.motion-active) .tag-amount { animation: tag-appear 5s 1.8s ease-in-out infinite; }
		.receipt-artwork:global(.motion-active) .tag-policy { animation: tag-appear 5s 3.0s ease-in-out infinite; }
		.receipt-artwork:global(.motion-active) li { animation: check-arrive 550ms var(--check-delay) cubic-bezier(.22, 1, .36, 1) backwards; }
		.receipt-artwork:global(.motion-active) .check-mark { animation: check-stamp 450ms var(--check-delay) ease-out backwards; }
	}
	@media (max-width: 768px) and (prefers-reduced-motion: no-preference) { .curved-receipt { animation-name: paper-float-mobile; } }
	@keyframes paper-float-mobile { 0%, 100% { transform: translateY(0) rotate(-.5deg); } 50% { transform: translateY(-10px) rotate(1deg); } }
	@media (max-width: 960px) { .receipt-checks { width: 216px; padding: var(--space-4); } li { font-size: 11px; gap: var(--space-2); } ul { gap: var(--space-3); } }
	@media (max-width: 768px) {
		.ocr-scanner { display: none; }
		.receipt-artwork { max-width: 550px; margin-inline: auto; aspect-ratio: 1.1; }
		.curved-receipt { width: 90%; right: -3%; top: -4%; }
		.receipt-checks { left: 0; width: 46%; top: 34%; padding: var(--space-3); }
		.checks-heading { font-size: 9px; gap: var(--space-1); padding-bottom: var(--space-2); margin-bottom: var(--space-2); }
		.checks-heading img { width: 20px; height: 20px; }
		li { font-size: 10px; gap: var(--space-2); }
		ul { gap: var(--space-3); }
		.check-mark { width: 17px; height: 17px; font-size: 10px; }
		.compact .receipt-checks { width: 46%; }
		.compact .curved-receipt { right: -3%; }
	}
	@media (max-width: 374px) { .checks-heading img { display: none; } li, .compact li { font-size: 9px; } ul, .compact ul { gap: var(--space-2); } .receipt-checks { padding: var(--space-3) var(--space-2); } }
</style>
