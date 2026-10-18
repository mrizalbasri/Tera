<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import { getClaim } from '$lib/api/claims';
	import { listReviews, decideReview, CURRENT_REVIEWER_ID } from '$lib/api/reviews';
	import { ApiError } from '$lib/api/client';
	import { formatCurrency } from '$lib/formatters/currency';
	import { formatDateTime } from '$lib/formatters/date';
	import type { ClaimDetailResponse, ReviewQueueItem } from '$lib/types/claim';

	let detail = $state<ClaimDetailResponse | null>(null);
	let review = $state<ReviewQueueItem | null>(null);
	let loading = $state(true);
	let error = $state('');
	let action = $state<'approve' | 'reject' | null>(null);
	let reason = $state('');
	let submitting = $state(false);

	async function load() {
		const claimId = page.params.claimId;
		if (!claimId) return;
		loading = true;
		error = '';
		try {
			const [claimResponse, reviewResponse] = await Promise.all([getClaim(claimId), listReviews()]);
			detail = claimResponse;
			review = reviewResponse.items.find((item) => item.claim.id === claimId) ?? null;
			if (!review) error = 'Klaim ini tidak berada dalam antrean review.';
		} catch (cause) {
			error = cause instanceof ApiError ? cause.message : 'Detail review tidak dapat dimuat.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function submitDecision() {
		if (!review || !action || !reason.trim() || submitting) return;
		submitting = true;
		try {
			await decideReview({
				claimId: review.claim.id,
				action,
				reason: reason.trim(),
				reviewerReference: CURRENT_REVIEWER_ID
			});
			action = null;
			reason = '';
			await load();
		} catch (cause) {
			error = cause instanceof ApiError ? cause.message : 'Keputusan tidak dapat disimpan.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Detail Review Klaim</title></svelte:head>

<main class="review-detail">
	<a class="back-link" href="/reviews">← Kembali ke antrean review</a>
	{#if loading}
		<p role="status">Memuat detail review...</p>
	{:else if error}
		<div class="state error" role="alert">{error}</div>
	{:else if detail && review}
		<header>
			<div>
				<p class="eyebrow">REVIEWER DETAIL</p>
				<h1>Klaim {detail.claim.id}</h1>
				<p class="muted">{detail.claim.employee_id} · {formatDateTime(detail.claim.submitted_at)}</p>
			</div>
			<StatusBadge status={detail.claim.status} size="sm" />
		</header>

		<section class="grid">
			<div class="panel">
				<h2>Ringkasan klaim</h2>
				<div class="row"><span>Nominal</span><strong>{formatCurrency(detail.claim.declared_amount, detail.claim.currency)}</strong></div>
				<div class="row"><span>Review</span><strong>{review.review.status}</strong></div>
				<div class="row"><span>Signal</span><strong>{detail.signals.length}</strong></div>
				{#if detail.decisions.at(-1)}
					<DecisionBanner decision={detail.decisions.at(-1)} />
				{/if}
			</div>
			<div class="panel">
				<h2>Bukti backend</h2>
				{#if detail.signals.length === 0}
					<p class="muted">Tidak ada signal tambahan.</p>
				{:else}
					{#each detail.signals as signal (signal.id)}
						<div class="evidence">
							<strong>{signal.signal_type} · {signal.severity}</strong>
							<span>{signal.explanation}</span>
						</div>
					{/each}
				{/if}
			</div>
		</section>

		{#if review.review.status === 'open'}
			<section class="panel decision-panel">
				<h2>Keputusan reviewer</h2>
				<div class="actions">
					<button type="button" class="approve" onclick={() => (action = 'approve')}>Setujui</button>
					<button type="button" class="reject" onclick={() => (action = 'reject')}>Tolak</button>
				</div>
				{#if action}
					<textarea bind:value={reason} aria-label="Alasan keputusan" required placeholder="Alasan keputusan wajib diisi"></textarea>
					<button type="button" onclick={submitDecision} disabled={submitting || !reason.trim()}>
						{submitting ? 'Menyimpan...' : `Konfirmasi ${action === 'approve' ? 'persetujuan' : 'penolakan'}`}
					</button>
				{/if}
			</section>
		{/if}
	{/if}
</main>

<style>
	.review-detail { max-width: 980px; margin: 0 auto; padding: 2rem 1rem; }
	.back-link, .muted { color: var(--color-text-muted); }
	header { display: flex; justify-content: space-between; align-items: start; gap: 1rem; margin: 2rem 0; }
	.eyebrow { color: var(--color-text-muted); font-size: .75rem; letter-spacing: .12em; }
	h1 { margin: .25rem 0; }
	.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
	.panel { padding: 1.25rem; margin-top: 1rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	h2 { font-size: 1rem; margin-top: 0; }
	.row { display: flex; justify-content: space-between; padding: .55rem 0; border-bottom: 1px solid var(--color-border); }
	.evidence { display: grid; gap: .25rem; padding: .75rem 0; border-bottom: 1px solid var(--color-border); }
	.evidence span { color: var(--color-text-muted); font-size: .9rem; }
	.actions { display: flex; gap: .75rem; }
	textarea { display: block; width: 100%; min-height: 90px; margin: 1rem 0; padding: .75rem; }
	button { padding: .6rem 1rem; cursor: pointer; }
	.approve { color: #166534; } .reject { color: #991b1b; }
	.error { color: #991b1b; }
</style>
