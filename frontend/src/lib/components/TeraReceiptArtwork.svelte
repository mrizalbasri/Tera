<script lang="ts">
	import { motionInView } from '$lib/actions/motionInView';
	let { compact = false }: { compact?: boolean } = $props();

	const checks = [
		'Nota diterima & diverifikasi',
		'Data dibaca dengan Vision AI',
		'Kebijakan & plafon diperiksa',
		'Duplikat & anomali ditinjau',
		'Siap disetujui / diteruskan'
	];

	let tiltX = $state(0);
	let tiltY = $state(0);
	let isHovering = $state(false);
	let scanKey = $state(0);

	function onPointerMove(e: PointerEvent) {
		if (compact) return;
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		const px = (e.clientX - rect.left) / rect.width;
		const py = (e.clientY - rect.top) / rect.height;
		// Subtle 3D tilt: max +-6 degrees
		tiltY = (px - 0.5) * 12;
		tiltX = (0.5 - py) * 12;
		isHovering = true;
	}

	function onPointerLeave() {
		tiltX = 0;
		tiltY = 0;
		isHovering = false;
	}

	function retriggerScan() {
		scanKey += 1;
	}
</script>

<figure
	use:motionInView
	class="receipt-artwork"
	class:compact
	class:hovering={isHovering}
	onpointermove={onPointerMove}
	onpointerleave={onPointerLeave}
	style="--tilt-x: {tiltX}deg; --tilt-y: {tiltY}deg;"
>
	<div class="receipt-viewport">
		<div class="receipt-paper-wrap">
			<img
				class="curved-receipt"
				src="/brand/tera-receipt-curved.png"
				alt="Ilustrasi nota kertas putih melengkung dengan simbol Tera berwarna mint"
				width="1280"
				height="1280"
				fetchpriority={compact ? 'auto' : 'high'}
				loading={compact ? 'lazy' : 'eager'}
			/>
			{#if !compact}
				{#key scanKey}
					<div class="ocr-scanner" aria-hidden="true">
						<div class="scan-veil"></div>
						<div class="scan-laser">
							<span class="laser-dot"></span>
						</div>

						<!-- High-tech OCR Bounding Boxes -->
						<div class="ocr-bbox bbox-vendor">
							<span class="bbox-corner tl"></span>
							<span class="bbox-corner br"></span>
							<div class="ocr-tag tag-vendor">
								<span class="tag-pulse"></span>
								<span>SPBU Shell · 99.4%</span>
							</div>
						</div>

						<div class="ocr-bbox bbox-date">
							<span class="bbox-corner tl"></span>
							<span class="bbox-corner br"></span>
							<div class="ocr-tag tag-date">
								<span>18 Okt 2026 · Valid</span>
							</div>
						</div>

						<div class="ocr-bbox bbox-amount">
							<span class="bbox-corner tl"></span>
							<span class="bbox-corner br"></span>
							<div class="ocr-tag tag-amount">
								<span class="tag-pulse"></span>
								<span>Rp 350.000 · 99.8%</span>
							</div>
						</div>

						<div class="ocr-bbox bbox-policy">
							<span class="bbox-corner tl"></span>
							<span class="bbox-corner br"></span>
							<div class="ocr-tag tag-policy">
								<span>✓ Plafon BBM Sesuai</span>
							</div>
						</div>
					</div>
				{/key}
			{/if}
		</div>

		<div class="receipt-checks">
			<div class="checks-heading">
				<div class="heading-left">
					<img src="/logo.webp" width="22" height="22" alt="" />
					<span>Alur Otomatisasi Tera</span>
				</div>
				<div class="live-indicator" title="Vision AI beroperasi secara real-time">
					<span class="ping-ring"></span>
					<span class="ping-dot"></span>
					<span>LIVE</span>
				</div>
			</div>
			<ul>
				{#each checks as check, index}
					<li style={`--check-delay: ${240 + index * 160}ms`}>
						<span class="check-mark" aria-hidden="true">✓</span>
						<span>{check}</span>
					</li>
				{/each}
			</ul>

			{#if !compact}
				<div class="scan-action-row">
					<button type="button" class="rescan-trigger" onclick={retriggerScan} aria-label="Jalankan ulang simulasi scan OCR">
						<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
						</svg>
						<span>Simulasi OCR Ulang</span>
					</button>
				</div>
			{/if}
		</div>
	</div>
</figure>

<style>
	.receipt-artwork {
		position: relative;
		min-width: 0;
		width: 100%;
		aspect-ratio: 1.06;
		margin: 0;
		isolation: isolate;
		perspective: 1200px;
	}

	.receipt-viewport {
		position: relative;
		width: 100%;
		height: 100%;
		transform-style: preserve-3d;
		transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
		transform: rotateX(var(--tilt-x, 0deg)) rotateY(var(--tilt-y, 0deg));
	}

	.curved-receipt {
		position: absolute;
		width: 94%;
		height: auto;
		top: -3%;
		right: -9%;
		object-fit: contain;
		z-index: 1;
		filter: drop-shadow(0 20px 30px rgba(0, 45, 40, 0.12));
		transform-style: preserve-3d;
	}

	.receipt-checks {
		position: absolute;
		top: 35%;
		left: -3%;
		width: 254px;
		padding: var(--space-5);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: 0 16px 36px -6px rgba(0, 45, 40, 0.14), 0 0 0 1px rgba(15, 118, 110, 0.08);
		z-index: 4;
		transform: rotate(-3deg) translateZ(28px);
		backdrop-filter: blur(8px);
		transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.3s ease;
	}

	.receipt-checks:hover {
		transform: rotate(-1deg) translateZ(36px) translateY(-4px);
		box-shadow: 0 22px 42px -6px rgba(0, 45, 40, 0.2), 0 0 0 1px var(--color-primary);
	}

	.checks-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--color-border);
		padding-bottom: var(--space-3);
		margin-bottom: var(--space-3);
	}

	.heading-left {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: 11px;
		font-weight: 700;
		color: var(--color-ink);
	}

	.live-indicator {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 9px;
		font-weight: 800;
		letter-spacing: 0.08em;
		color: var(--color-primary-dark);
		background: rgba(16, 185, 129, 0.12);
		padding: 2px 6px;
		border-radius: var(--radius-pill);
		border: 1px solid rgba(16, 185, 129, 0.25);
	}

	.ping-ring {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #10b981;
		animation: pulse-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
	}

	.ping-dot {
		display: none;
	}

	@keyframes pulse-ping {
		0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
		70% { transform: scale(1.05); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
		100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--space-3);
	}

	li {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		font-size: 11.5px;
		color: var(--color-ink);
		line-height: 1.45;
	}

	.check-mark {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
		display: grid;
		place-items: center;
		background: var(--color-primary);
		color: var(--color-inverse);
		border-radius: 50%;
		font-size: 11px;
		font-weight: 700;
		box-shadow: 0 2px 6px rgba(15, 118, 110, 0.25);
	}

	.scan-action-row {
		margin-top: var(--space-4);
		padding-top: var(--space-3);
		border-top: 1px dashed var(--color-border);
		display: flex;
		justify-content: flex-end;
	}

	.rescan-trigger {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		background: var(--color-light);
		color: var(--color-primary-dark);
		border: 1px solid var(--color-border);
		padding: 3px 8px;
		border-radius: var(--radius-pill);
		font-size: 10px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.rescan-trigger:hover {
		background: var(--color-surface);
		border-color: var(--color-primary);
		transform: scale(1.03);
	}

	.compact {
		aspect-ratio: 1.1;
	}

	.compact .curved-receipt {
		width: 94%;
		top: -7%;
		right: -5%;
	}

	.compact .receipt-checks {
		top: 36%;
		width: 220px;
		padding: var(--space-4);
	}

	.compact li {
		font-size: 11px;
	}

	.compact ul {
		gap: var(--space-3);
	}

	.receipt-paper-wrap {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		transform-style: preserve-3d;
	}

	/* High-Tech OCR Scanner Beam & Bounding Boxes */
	.ocr-scanner {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 3;
		transform-style: preserve-3d;
	}

	.scan-laser {
		position: absolute;
		top: 16%;
		left: 30%;
		width: 62%;
		height: 3px;
		background: linear-gradient(90deg, transparent 0%, #10b981 25%, #34d399 75%, transparent 100%);
		box-shadow: 0 0 14px 2px rgba(52, 211, 153, 0.85), 0 0 4px #fff;
		border-radius: 2px;
		opacity: 0;
	}

	.laser-dot {
		position: absolute;
		right: 15%;
		top: -3px;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: #fff;
		box-shadow: 0 0 10px 3px #34d399;
	}

	.scan-veil {
		position: absolute;
		top: 16%;
		left: 30%;
		width: 62%;
		height: 70px;
		background: linear-gradient(180deg, rgba(52, 211, 153, 0.16) 0%, transparent 100%);
		opacity: 0;
		pointer-events: none;
	}

	/* Bounding boxes placed exactly across the receipt */
	.ocr-bbox {
		position: absolute;
		border: 1px solid rgba(52, 211, 153, 0.7);
		background: rgba(16, 185, 129, 0.08);
		border-radius: 4px;
		opacity: 0;
		transform: scale(0.96);
		transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
		pointer-events: none;
	}

	.bbox-corner {
		position: absolute;
		width: 5px;
		height: 5px;
		border-color: #34d399;
		border-style: solid;
	}

	.bbox-corner.tl {
		top: -1px;
		left: -1px;
		border-width: 2px 0 0 2px;
	}

	.bbox-corner.br {
		bottom: -1px;
		right: -1px;
		border-width: 0 2px 2px 0;
	}

	.bbox-vendor {
		top: 22%;
		right: 10%;
		width: 175px;
		height: 38px;
	}

	.bbox-date {
		top: 36%;
		right: 14%;
		width: 150px;
		height: 32px;
	}

	.bbox-amount {
		top: 49%;
		right: 8%;
		width: 185px;
		height: 42px;
	}

	.bbox-policy {
		top: 67%;
		right: 12%;
		width: 170px;
		height: 34px;
	}

	.ocr-tag {
		position: absolute;
		top: -12px;
		right: -6px;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		background: rgba(15, 23, 42, 0.94);
		color: #34d399;
		border: 1px solid rgba(52, 211, 153, 0.6);
		border-radius: var(--radius-pill);
		font-size: 9.5px;
		font-weight: 700;
		box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
		white-space: nowrap;
		letter-spacing: 0.02em;
	}

	.tag-pulse {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: #34d399;
		animation: pulse-ping 1.5s infinite;
	}

	/* Laser & Bounding box animations */
	@keyframes laser-cycle {
		0% { top: 14%; opacity: 0; }
		10% { opacity: 0.95; }
		85% { opacity: 0.95; }
		100% { top: 78%; opacity: 0; }
	}

	@keyframes veil-cycle {
		0% { top: 14%; opacity: 0; }
		10% { opacity: 0.8; }
		85% { opacity: 0.8; }
		100% { top: 78%; opacity: 0; }
	}

	@keyframes bbox-pop {
		0%, 15% { opacity: 0; transform: scale(0.95); }
		22% { opacity: 1; transform: scale(1.02); }
		28%, 88% { opacity: 1; transform: scale(1); }
		100% { opacity: 0; transform: scale(0.96); }
	}

	@keyframes paper-float {
		0%, 100% { transform: translateY(0) rotate(-1deg); }
		50% { transform: translateY(-16px) rotate(1.2deg); }
	}

	@keyframes checklist-float {
		0%, 100% { transform: translateY(-4px) rotate(-3deg) translateZ(28px); }
		50% { transform: translateY(8px) rotate(-1.5deg) translateZ(32px); }
	}

	@keyframes check-arrive {
		from { opacity: 0; transform: translateX(-12px); }
		to { opacity: 1; transform: translateX(0); }
	}

	@keyframes check-stamp {
		0% { transform: scale(0.5); }
		65% { transform: scale(1.2); }
		100% { transform: scale(1); }
	}

	@media (prefers-reduced-motion: no-preference) {
		.curved-receipt {
			animation: paper-float 8s ease-in-out infinite;
			animation-play-state: paused;
		}

		.receipt-checks {
			animation: checklist-float 7s ease-in-out infinite;
			animation-play-state: paused;
		}

		.receipt-artwork:global(.motion-active) .curved-receipt,
		.receipt-artwork:global(.motion-active) .receipt-checks {
			animation-play-state: running;
		}

		.receipt-artwork:global(.motion-active) .scan-laser {
			animation: laser-cycle 4.5s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) .scan-veil {
			animation: veil-cycle 4.5s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) .bbox-vendor {
			animation: bbox-pop 4.5s 0.4s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) .bbox-date {
			animation: bbox-pop 4.5s 1.2s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) .bbox-amount {
			animation: bbox-pop 4.5s 2.0s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) .bbox-policy {
			animation: bbox-pop 4.5s 2.8s ease-in-out infinite;
		}

		.receipt-artwork:global(.motion-active) li {
			animation: check-arrive 550ms var(--check-delay) cubic-bezier(0.22, 1, 0.36, 1) backwards;
		}

		.receipt-artwork:global(.motion-active) .check-mark {
			animation: check-stamp 450ms var(--check-delay) cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
		}
	}

	@media (max-width: 960px) {
		.receipt-checks {
			width: 224px;
			padding: var(--space-4);
		}
		li {
			font-size: 11px;
			gap: var(--space-2);
		}
		ul {
			gap: var(--space-2);
		}
	}

	@media (max-width: 768px) {
		.receipt-artwork {
			perspective: none;
		}
		.receipt-viewport {
			transform: none !important;
		}
		.ocr-scanner {
			display: none;
		}
		.receipt-artwork {
			max-width: 550px;
			margin-inline: auto;
			aspect-ratio: 1.1;
		}
		.curved-receipt {
			width: 90%;
			right: -3%;
			top: -4%;
		}
		.receipt-checks {
			left: 0;
			width: 52%;
			top: 32%;
			padding: var(--space-3);
			transform: rotate(-2deg);
		}
		.checks-heading {
			padding-bottom: var(--space-2);
			margin-bottom: var(--space-2);
		}
		.heading-left {
			font-size: 9.5px;
		}
		.heading-left img {
			width: 18px;
			height: 18px;
		}
		.live-indicator {
			font-size: 8px;
			padding: 1px 4px;
		}
		li {
			font-size: 10px;
			gap: var(--space-2);
		}
		ul {
			gap: var(--space-2);
		}
		.check-mark {
			width: 16px;
			height: 16px;
			font-size: 10px;
		}
		.scan-action-row {
			display: none;
		}
	}

	@media (max-width: 374px) {
		.heading-left img {
			display: none;
		}
		li {
			font-size: 9px;
		}
	}
</style>
