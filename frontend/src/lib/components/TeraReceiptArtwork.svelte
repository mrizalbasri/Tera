<script lang="ts">
	import { motionInView } from '$lib/actions/motionInView';
	let { compact = false }: { compact?: boolean } = $props();
	const checks = ['Nota diterima', 'Data dibaca', 'Kebijakan diperiksa', 'Duplikat ditinjau', 'Siap ditindaklanjuti'];
</script>

<figure use:motionInView class="receipt-artwork" class:compact>
	<img
		class="curved-receipt"
		src="/brand/tera-receipt-curved.png"
		alt="Ilustrasi nota kertas putih melengkung dengan simbol Tera berwarna mint"
		width="1280"
		height="1280"
		fetchpriority={compact ? 'auto' : 'high'}
		loading={compact ? 'lazy' : 'eager'}
	/>
	<div class="receipt-checks">
		<div class="checks-heading">
			<img src="/logo.webp" width="24" height="24" alt="" />
			<span>Contoh alur Tera</span>
		</div>
		<ul>
			{#each checks as check, index}
				<li style={`--check-delay: ${280 + index * 140}ms`}>
					<span class="check-mark" aria-hidden="true">✓</span>
					<span>{check}</span>
				</li>
			{/each}
		</ul>
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
	}

	.curved-receipt {
		position: absolute;
		width: 94%;
		height: auto;
		top: -3%;
		right: -9%;
		object-fit: contain;
		z-index: 1;
		will-change: transform, opacity;
		backface-visibility: hidden;
	}

	.receipt-checks {
		position: absolute;
		top: 35%;
		left: -3%;
		width: 244px;
		padding: var(--space-5);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-receipt);
		z-index: 2;
		transform: rotate(-3deg);
		will-change: transform, opacity;
		backface-visibility: hidden;
	}

	.checks-heading {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		border-bottom: 1px solid var(--color-border);
		padding-bottom: var(--space-3);
		margin-bottom: var(--space-3);
		font-size: 11px;
		font-weight: 650;
		color: var(--color-ink);
	}

	.checks-heading img {
		object-fit: contain;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--space-4);
	}

	li {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		font-size: 12px;
		color: var(--color-ink);
		line-height: 1.5;
	}

	.check-mark {
		width: 21px;
		height: 21px;
		flex-shrink: 0;
		display: grid;
		place-items: center;
		background: var(--color-primary);
		color: var(--color-inverse);
		border-radius: 50%;
		font-size: 12px;
		font-weight: 700;
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

	/* Entrance Keyframes: Physical, graceful entrance from lateral angles (NOT from the bottom) */
	@keyframes receipt-enter {
		from {
			opacity: 0;
			transform: translateX(36px) translateY(-8px) rotate(2.5deg) scale(0.96);
		}
		to {
			opacity: 1;
			transform: translateX(0) translateY(0) rotate(-1deg) scale(1);
		}
	}

	@keyframes card-enter {
		from {
			opacity: 0;
			transform: translateX(-32px) translateY(8px) rotate(1deg) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateX(0) translateY(-4px) rotate(-3deg) scale(1);
		}
	}

	@keyframes check-arrive {
		from {
			opacity: 0;
			transform: translateX(-14px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes check-stamp {
		0% {
			transform: scale(0);
			opacity: 0;
		}
		65% {
			transform: scale(1.2);
			opacity: 1;
		}
		100% {
			transform: scale(1);
			opacity: 1;
		}
	}

	@keyframes paper-float {
		0%, 100% {
			transform: translateY(0) rotate(-1deg);
		}
		50% {
			transform: translateY(-16px) rotate(1.2deg);
		}
	}

	@keyframes checklist-float {
		0%, 100% {
			transform: translateY(-4px) rotate(-3deg);
		}
		50% {
			transform: translateY(7px) rotate(-1.5deg);
		}
	}

	@media (prefers-reduced-motion: no-preference) {
		.curved-receipt {
			animation: receipt-enter 900ms cubic-bezier(0.16, 1, 0.3, 1) both,
			           paper-float 7s 900ms ease-in-out infinite;
			animation-play-state: running;
		}

		.receipt-checks {
			animation: card-enter 800ms 180ms cubic-bezier(0.16, 1, 0.3, 1) both,
			           checklist-float 6s 980ms ease-in-out infinite;
			animation-play-state: running;
		}

		.receipt-artwork:global(.motion-active) li {
			animation: check-arrive 500ms var(--check-delay) cubic-bezier(0.16, 1, 0.3, 1) backwards;
		}

		.receipt-artwork:global(.motion-active) .check-mark {
			animation: check-stamp 400ms var(--check-delay) cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
		}
	}

	@media (max-width: 768px) and (prefers-reduced-motion: no-preference) {
		.curved-receipt {
			animation-name: receipt-enter, paper-float-mobile;
		}
	}

	@keyframes paper-float-mobile {
		0%, 100% {
			transform: translateY(0) rotate(-1deg);
		}
		50% {
			transform: translateY(-10px) rotate(1deg);
		}
	}

	@media (max-width: 960px) {
		.receipt-checks {
			width: 216px;
			padding: var(--space-4);
		}
		li {
			font-size: 11px;
			gap: var(--space-2);
		}
		ul {
			gap: var(--space-3);
		}
	}

	@media (max-width: 768px) {
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
			width: 46%;
			top: 34%;
			padding: var(--space-3);
		}
		.checks-heading {
			font-size: 9px;
			gap: var(--space-1);
			padding-bottom: var(--space-2);
			margin-bottom: var(--space-2);
		}
		.checks-heading img {
			width: 20px;
			height: 20px;
		}
		li {
			font-size: 10px;
			gap: var(--space-2);
		}
		ul {
			gap: var(--space-3);
		}
		.check-mark {
			width: 17px;
			height: 17px;
			font-size: 10px;
		}
		.compact .receipt-checks {
			width: 46%;
		}
		.compact .curved-receipt {
			right: -3%;
		}
	}

	@media (max-width: 374px) {
		.checks-heading img {
			display: none;
		}
		li, .compact li {
			font-size: 9px;
		}
		ul, .compact ul {
			gap: var(--space-2);
		}
		.receipt-checks {
			padding: var(--space-3) var(--space-2);
		}
	}
</style>
