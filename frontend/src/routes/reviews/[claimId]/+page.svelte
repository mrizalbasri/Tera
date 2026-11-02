<script lang="ts">
	import { page } from '$app/state';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import AnomalyBadge from '$lib/components/AnomalyBadge.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import { getClaim } from '$lib/api/claims';
	import { listReviews, decideReview } from '$lib/api/reviews';
	import { ApiError } from '$lib/api/client';
	import { formatCurrency } from '$lib/formatters/currency';
	import { formatDateTime } from '$lib/formatters/date';
	import type { ClaimDetailResponse, ReviewQueueItem } from '$lib/types/claim';

	let detail = $state<ClaimDetailResponse | null>(null);
	let review = $state<ReviewQueueItem | null>(null);
	let loading = $state(true);
	let error = $state('');
	let decisionError = $state('');
	let action = $state<'approve' | 'reject' | null>(null);
	let reason = $state('');
	let submitting = $state(false);
	let selectedReceiptId = $state('');
	let generation = 0;
	const receipt = $derived(detail?.receipts.find((item) => item.id === selectedReceiptId) ?? detail?.receipts.at(-1));
	const extraction = $derived(detail?.extractions.findLast((item) => item.receipt_id === receipt?.id));

	async function load(claimId = page.params.claimId) {
		if (!claimId) return;
		const request = ++generation;
		loading = true;
		detail = null;
		review = null;
		action = null;
		reason = '';
		submitting = false;
		selectedReceiptId = '';
		error = '';
		decisionError = '';
		try {
			const [claimResponse, reviewResponse] = await Promise.all([getClaim(claimId), listReviews()]);
			if (request !== generation) return;
			detail = claimResponse;
			review = reviewResponse.items.find((item) => item.claim.id === claimId) ?? null;
		} catch (cause) {
			if (request === generation) error = cause instanceof ApiError ? cause.message : 'Detail review tidak dapat dimuat.';
		} finally {
			if (request === generation) loading = false;
		}
	}

	$effect(() => {
		const claimId = page.params.claimId;
		if (claimId) void load(claimId);
		return () => { generation++; };
	});

	async function submitDecision() {
		if (!review || !action || !reason.trim() || submitting) return;
		const request = generation;
		submitting = true;
		decisionError = '';
		try {
			const saved = await decideReview({
				claimId: review.claim.id,
				action,
				reason: reason.trim()
			});
			if (request !== generation) return;
			review = { ...review, claim: saved.claim, review: saved.review, decision: saved.decision };
			if (detail) {
				detail = {
					...detail,
					claim: saved.claim,
					decisions: [...detail.decisions.filter((item) => item.id !== saved.decision.id), saved.decision]
				};
			}
			action = null;
			reason = '';
		} catch (cause) {
			if (request !== generation) return;
			if (cause instanceof ApiError && cause.status === 409) {
				decisionError = 'Status klaim sudah berubah. Muat ulang untuk melihat keputusan terbaru.';
			} else {
				decisionError = cause instanceof ApiError ? cause.message : 'Keputusan tidak dapat disimpan.';
			}
		} finally {
			if (request === generation) submitting = false;
		}
	}
</script>

<svelte:head><title>Detail Review Klaim</title></svelte:head>

<main class="review-detail">
	<a class="back-link" href="/reviews">← Kembali ke antrean review</a>
	{#if loading}
		<p role="status">Memuat detail review...</p>
	{:else if error}
		<div class="state error" role="alert"><p>{error}</p><button type="button" onclick={() => load()}>Muat ulang</button></div>
	{:else if detail}
		<header>
			<div>
				<p class="eyebrow">REVIEWER DETAIL</p>
				<h1>Klaim {detail.claim.id}</h1>
				<p class="muted">{detail.claim.employee_id} · {formatDateTime(detail.claim.submitted_at)}</p>
			</div>
			<div style="display: flex; gap: 8px; align-items: center;">
				{#if detail.decisions.at(-1)?.anomaly_score != null || detail.signals.some((s) => s.signal_type === 'anomaly')}
					<AnomalyBadge
						score={detail.decisions.at(-1)?.anomaly_score}
						signal={detail.signals.find((s) => s.signal_type === 'anomaly')}
						size="md"
					/>
				{/if}
				<StatusBadge status={detail.claim.status} size="sm" />
			</div>
		</header>

			<section class="evidence-workbench" aria-label="Nota dan hasil pembacaan">
				<div class="panel receipt-preview"><h2>Nota yang diperiksa</h2>
					{#if detail.receipts.length > 1}
						<label for="review-receipt">Pilih nota yang diperiksa</label>
						<select id="review-receipt" value={receipt?.id} onchange={(event) => { selectedReceiptId = event.currentTarget.value; }}>
							{#each detail.receipts as item (item.id)}<option value={item.id}>{item.original_filename}</option>{/each}
						</select>
					{/if}
					{#if receipt}
						{#if receipt.media_type.startsWith('image/')}<img src={`/api/claims/${detail.claim.id}/receipts/${receipt.id}/content`} alt={`Nota ${receipt.original_filename}`} />
						{:else if receipt.media_type === 'application/pdf'}<iframe src={`/api/claims/${detail.claim.id}/receipts/${receipt.id}/content`} title="Pratinjau nota PDF"></iframe>{/if}
						<a href={`/api/claims/${detail.claim.id}/receipts/${receipt.id}/content`} target="_blank" rel="noopener noreferrer">Buka berkas asli</a>
					{:else}<p class="muted">Bukti nota belum tersedia.</p>{/if}
				</div>
				<div class="panel extraction-summary"><h2>Hasil pembacaan Tera</h2><p class="muted">Cocokkan informasi berikut dengan bukti nota sebelum mencatat keputusan.</p>
					<dl><div><dt>Vendor</dt><dd>{extraction?.vendor.value == null ? 'Belum terbaca' : String(extraction.vendor.value)}</dd></div><div><dt>Tanggal nota</dt><dd>{extraction?.receipt_date.value == null ? 'Belum terbaca' : String(extraction.receipt_date.value)}</dd></div><div><dt>Total nota</dt><dd>{extraction?.total.value == null ? 'Belum terbaca' : formatCurrency(Number(extraction.total.value), detail.claim.currency)}</dd></div><div><dt>Kategori</dt><dd>{extraction?.category.value == null ? 'Belum terbaca' : String(extraction.category.value)}</dd></div></dl>
					{#if review?.decision}<div class="escalation-reason"><strong>Alasan diteruskan ke reviewer</strong><p>{review.decision.explanation}</p></div>{/if}
					<p class="muted">Disetujui berarti keputusan klaim, belum konfirmasi pembayaran.</p>
				</div>
			</section>
			<section class="grid">
			<div class="panel">
				<h2>Ringkasan klaim</h2>
				<div class="row"><span>Nominal</span><strong>{formatCurrency(detail.claim.declared_amount, detail.claim.currency)}</strong></div>
				<div class="row"><span>Review</span><strong>{review?.review.status ?? (detail.claim.status === 'escalated' ? 'Tidak tersedia di antrean' : 'Tidak ada review terbuka')}</strong></div>
				<div class="row">
					<span>Skor anomali ML</span>
					{#if detail.decisions.at(-1)?.anomaly_score != null || detail.signals.some((s) => s.signal_type === 'anomaly')}
						<AnomalyBadge
							score={detail.decisions.at(-1)?.anomaly_score}
							signal={detail.signals.find((s) => s.signal_type === 'anomaly')}
							size="sm"
						/>
					{:else}
						<strong>-</strong>
					{/if}
				</div>
				<div class="row"><span>Signal</span><strong>{detail.signals.length}</strong></div>
					<a class="button secondary" href={`/admin/claims/${encodeURIComponent(detail.claim.id)}`}>Lihat nota dan hasil pembacaan</a>
				{#if detail.decisions.at(-1)}
					<DecisionBanner decision={detail.decisions.at(-1)} />
				{/if}
			</div>
			<div class="panel">
				<h2>Bukti dan temuan</h2>
				{#if detail.signals.length === 0}
					<p class="muted">Tidak ada signal tambahan.</p>
				{:else}
					{#each detail.signals as signal (signal.id)}
						<div class="evidence">
							<div style="display: flex; justify-content: space-between; align-items: center;">
								<strong>{signal.signal_type} · {signal.severity}</strong>
								{#if signal.signal_type === 'anomaly'}
									<AnomalyBadge score={signal.score} {signal} size="sm" />
								{/if}
							</div>
							<span>{signal.explanation}</span>
							{#if signal.detector_version}
								<small class="muted" style="font-family: monospace;">Detektor: {signal.detector_version}</small>
							{/if}
							{#if signal.evidence && typeof signal.evidence === 'object'}
								{@const ev = signal.evidence as Record<string, unknown>}
								{#if ev.features && typeof ev.features === 'object'}
									<details style="margin-top: 4px; font-size: 12px;">
										<summary style="cursor: pointer; color: var(--color-primary-dark); font-weight: 500;">Fitur analisis ML ({Object.keys(ev.features).length} variabel)</summary>
										<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 4px; padding: 6px; background: var(--color-light, #f8fafc); border-radius: 4px; margin-top: 4px;">
											{#each Object.entries(ev.features as Record<string, unknown>) as [name, val]}
												<div style="font-size: 11px;">
													<span style="color: var(--color-text-muted);">{name}:</span>
													<strong>{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : String(val)}</strong>
												</div>
											{/each}
										</div>
									</details>
								{/if}
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</section>

		{#if decisionError}<div class="state error" role="alert"><p>{decisionError}</p><button type="button" class="secondary" onclick={() => load()} disabled={submitting}>Muat ulang status</button></div>{/if}
		{#if review?.review.status === 'open'}
			<section class="panel decision-panel">
				<h2>Keputusan reviewer</h2>
				{#if !action}
					<div class="actions">
						<button type="button" class="approve" onclick={() => (action = 'approve')}>Setujui klaim</button>
						<button type="button" class="reject" onclick={() => (action = 'reject')}>Tolak klaim</button>
					</div>
				{:else}
					<div class="confirm-box">
						<p>Konfirmasi: <strong>{action === 'approve' ? 'Setujui klaim' : 'Tolak klaim'}</strong></p>
						<textarea bind:value={reason} aria-label="Alasan keputusan" required maxlength="2000" disabled={submitting} placeholder="Alasan keputusan wajib diisi berdasarkan bukti klaim..."></textarea>
						<div class="actions">
							<button type="button" class={action === 'approve' ? 'approve' : 'reject'} onclick={submitDecision} disabled={submitting || !reason.trim()}>
								{submitting ? 'Menyimpan...' : `Ya, simpan ${action === 'approve' ? 'persetujuan' : 'penolakan'}`}
							</button>
							<button type="button" class="secondary" onclick={() => { action = null; reason = ''; }} disabled={submitting}>
								Batal
							</button>
						</div>
					</div>
				{/if}
			</section>
		{/if}
	{/if}
</main>

<style>
	.evidence-workbench { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-5); }
	.receipt-preview img, .receipt-preview iframe { display: block; width: 100%; height: 360px; object-fit: contain; border: 1px solid var(--color-border); background: var(--color-soft); border-radius: var(--radius-sm); }
	.receipt-preview a { display: inline-flex; min-height: 44px; align-items: center; margin-top: var(--space-3); }
	.extraction-summary dl { margin: var(--space-5) 0; }
	.extraction-summary dl > div { display: flex; justify-content: space-between; gap: var(--space-4); border-bottom: 1px solid var(--color-border); padding: var(--space-3) 0; }
	.extraction-summary dt { color: var(--color-text-muted); }
	.extraction-summary dd { margin: 0; font-weight: 600; text-align: right; overflow-wrap: anywhere; min-width: 0; }
	.escalation-reason { padding: var(--space-4); background: var(--color-light); border-radius: var(--radius-sm); }
	.escalation-reason p { margin-bottom: 0; }
	@media (max-width: 900px) { .evidence-workbench { grid-template-columns: minmax(0, 1fr); } }
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
	.actions { display: flex; gap: .75rem; flex-wrap: wrap; }
	.confirm-box { margin-top: 0.5rem; }
	textarea { display: block; width: 100%; min-height: 90px; margin: 0.75rem 0; padding: .75rem; font-family: inherit; }
	button { min-height: 44px; padding: var(--space-3) var(--space-4); cursor: pointer; border-radius: var(--radius-sm); font-size: var(--text-sm); }
	.approve { background: #ecfdf5; color: #166534; border: 1px solid #bbf7d0; font-weight: 600; }
	.reject { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; font-weight: 600; }
	.secondary { background: var(--color-surface, #f8fafc); color: var(--color-text-muted, #64748b); border: 1px solid var(--color-border, #e2e8f0); }
	.error { color: #991b1b; }
</style>
