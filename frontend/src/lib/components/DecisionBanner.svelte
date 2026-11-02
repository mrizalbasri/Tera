<script lang="ts">
	import { describeReasonCodes } from '$lib/formatters/reasonCodes';
	import { formatConfidence } from '$lib/formatters/currency';
	import { formatDateTime } from '$lib/formatters/date';
	import type { Decision } from '$lib/types/claim';

	/**
	 * FR-08: banner keputusan hanya merender keputusan yang benar-benar
	 * dikirim backend. Jika belum ada, tampil status menunggu yang jujur —
	 * UI tidak pernah mengarang hasil keputusan.
	 */
	let {
		decision = null,
		waitingNote = 'Agent sedang menilai klaim ini. Keputusan resmi hanya berasal dari backend.'
	}: {
		decision?: Decision | null;
		waitingNote?: string;
	} = $props();

	const OUTCOME_VIEW = {
		approved: { label: 'Disetujui', glyph: '✓', tone: 'success' },
		rejected: { label: 'Ditolak', glyph: '×', tone: 'danger' },
		needs_clarification: { label: 'Perlu klarifikasi', glyph: '?', tone: 'warn' },
		escalated: { label: 'Diteruskan untuk review', glyph: '!', tone: 'warn' }
	} as const;

	const reasons = $derived(decision ? describeReasonCodes(decision.reason_codes) : []);
	const outcomeView = $derived(decision ? OUTCOME_VIEW[decision.outcome] : null);
</script>

{#if decision && outcomeView}
	<div class="decision-banner {outcomeView.tone}" role="status">
		<div class="decision-head">
			<span aria-hidden="true">{outcomeView.glyph}</span>
			<strong>Keputusan: {outcomeView.label}</strong>
		</div>
		<p class="decision-explanation">{decision.explanation}</p>
		{#if reasons.length}
			<ul class="reason-list">
				{#each reasons as reason (reason.label)}
					<li>
						<span class="reason-label">{reason.label}</span>
						{#if reason.explanation}<span class="reason-explanation">{reason.explanation}</span>{/if}
					</li>
				{/each}
			</ul>
		{/if}
		<dl class="decision-meta">
			{#if decision.confidence != null}
				<div><dt>Keyakinan</dt><dd>{formatConfidence(decision.confidence)}</dd></div>
			{/if}
			{#if decision.anomaly_score != null}
				<div><dt>Skor anomali</dt><dd>{formatConfidence(decision.anomaly_score)}</dd></div>
			{/if}
			<div><dt>Waktu</dt><dd>{formatDateTime(decision.created_at)}</dd></div>
			<div>
				<dt>Sumber</dt>
				<dd>{decision.created_by === 'agent' ? 'Agent (otomatis)' : decision.created_by}</dd>
			</div>
		</dl>
	</div>
{:else}
	<div class="decision-banner waiting" role="status">
		<div class="decision-head">
			<span class="spin" aria-hidden="true">⟳</span>
			<strong>Menunggu keputusan</strong>
		</div>
		<p class="decision-explanation">{waitingNote}</p>
	</div>
{/if}

<style>
	.decision-banner {
		margin-top: 0.85rem;
		padding: 0.7rem 0.9rem;
		border-radius: var(--radius-sm);
		font-size: 0.8rem;
		border: 1px solid transparent;
		animation: fadeSlide 0.3s ease-out;
	}

	.decision-banner.success {
		background: rgba(34, 197, 94, 0.1);
		border-color: rgba(34, 197, 94, 0.25);
		color: #15803d;
	}

	.decision-banner.warn {
		background: rgba(245, 158, 11, 0.1);
		border-color: rgba(245, 158, 11, 0.25);
		color: #b45309;
	}

	.decision-banner.danger {
		background: rgba(239, 68, 68, 0.08);
		border-color: rgba(239, 68, 68, 0.2);
		color: #b91c1c;
	}

	.decision-banner.waiting {
		background: rgba(59, 130, 246, 0.07);
		border-color: rgba(59, 130, 246, 0.2);
		color: #1d4ed8;
	}

	.decision-head {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		font-size: 0.82rem;
	}

	.decision-explanation {
		margin: 0.35rem 0 0;
		line-height: 1.5;
		color: inherit;
	}

	.reason-list {
		margin: 0.5rem 0 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.reason-label {
		font-weight: 700;
	}

	.reason-explanation {
		display: block;
		font-size: 0.72rem;
		opacity: 0.85;
	}

	.decision-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem 1.1rem;
		margin: 0.55rem 0 0;
		font-size: 0.7rem;
	}

	.decision-meta div {
		display: flex;
		gap: 0.3rem;
	}

	.decision-meta dt {
		opacity: 0.75;
	}

	.decision-meta dd {
		margin: 0;
		font-weight: 600;
	}

	.spin {
		display: inline-block;
		animation: spinAnim 0.8s linear infinite;
	}

	@keyframes spinAnim {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	@keyframes fadeSlide {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
