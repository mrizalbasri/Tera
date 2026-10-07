<script lang="ts">
	import { onMount } from 'svelte';
	import Toast from '$lib/components/Toast.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { listReviews, decideReview, CURRENT_REVIEWER_ID } from '$lib/api/reviews';
	import { ApiError } from '$lib/api/client';
	import { showToast } from '$lib/stores/toast.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDateTime } from '$lib/formatters/date';
	import { formatCurrency, formatConfidence } from '$lib/formatters/currency';
	import { describeReasonCodes } from '$lib/formatters/reasonCodes';
	import type { ReviewQueueItem, Signal } from '$lib/types/claim';

	let queue = $state<ReviewQueueItem[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let searchQuery = $state('');

	// FR-10: keputusan reviewer selalu lewat konfirmasi + alasan eksplisit
	let decisionTarget = $state<ReviewQueueItem | null>(null);
	let decisionAction = $state<'approve' | 'reject'>('approve');
	let decisionReason = $state('');
	let submittingDecision = $state(false);
	let decisionError = $state<string | null>(null);

	// Bukti signal (duplikat/anomali) yang sedang dilihat reviewer
	let activeSignals = $state<ReviewQueueItem | null>(null);

	let pendingCount = $derived(queue.filter((item) => item.review.status === 'open').length);
	let decidedCount = $derived(queue.length - pendingCount);
	let filteredQueue = $derived(
		queue.filter((item) => {
			const q = searchQuery.trim().toLowerCase();
			if (!q) return true;
			return (
				shortClaimRef(item.claim.id).toLowerCase().includes(q) ||
				item.claim.employee_id.toLowerCase().includes(q)
			);
		})
	);

	async function load() {
		loading = true;
		loadError = null;
		try {
			const response = await listReviews();
			queue = response.items;
		} catch (error) {
			loadError = error instanceof ApiError ? error.message : 'Terjadi kesalahan tak terduga.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	function openDecisionModal(item: ReviewQueueItem, action: 'approve' | 'reject') {
		decisionTarget = item;
		decisionAction = action;
		decisionReason = '';
		decisionError = null;
	}

	function closeDecisionModal() {
		if (submittingDecision) return;
		decisionTarget = null;
		decisionError = null;
	}

	async function submitDecision() {
		if (!decisionTarget || submittingDecision) return;
		const reason = decisionReason.trim();
		if (!reason) {
			decisionError = 'Alasan keputusan wajib diisi.';
			return;
		}
		submittingDecision = true;
		decisionError = null;
		try {
			const response = await decideReview({
				claimId: decisionTarget.claim.id,
				action: decisionAction,
				reason
			});
			showToast(
				`✅ Klaim ${shortClaimRef(response.claim.id)} ${
					decisionAction === 'approve' ? 'disetujui' : 'ditolak'
				} — tercatat atas nama ${response.review.reviewer_reference ?? CURRENT_REVIEWER_ID}.`,
				'success'
			);
			decisionTarget = null;
			await load();
		} catch (error) {
			decisionError = error instanceof ApiError ? error.message : 'Gagal mengirim keputusan.';
		} finally {
			submittingDecision = false;
		}
	}

	function primaryReason(item: ReviewQueueItem): string {
		const codes = item.decision ? describeReasonCodes(item.decision.reason_codes) : [];
		return codes[0]?.label ?? 'Perlu review';
	}

	function severityLabel(severity: Signal['severity']): string {
		return severity === 'blocking' ? 'Blocking' : severity === 'warning' ? 'Peringatan' : 'Info';
	}

	function exportToCSV() {
		if (loading || queue.length === 0) {
			showToast('Tidak ada data untuk diekspor.', 'error');
			return;
		}
		const headers = ['ID Klaim', 'Karyawan', 'Diajukan', 'Nominal', 'Status Klaim', 'Status Review', 'Alasan'];
		const rows = queue.map((item) => [
			item.claim.id,
			item.claim.employee_id,
			formatDateTime(item.claim.submitted_at),
			item.claim.declared_amount ?? '',
			item.claim.status,
			item.review.status,
			item.decision?.explanation ?? ''
		]);
		const csv = [
			headers.join(','),
			...rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(','))
		].join('\n');
		const link = document.createElement('a');
		link.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
		link.download = `antrean-review-${new Date().toISOString().slice(0, 10)}.csv`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		showToast('Laporan CSV berhasil diunduh.', 'success');
	}
</script>

<svelte:head>
	<title>Review & Eskalasi Klaim | Expense Agent</title>
</svelte:head>

<Toast />

<main>
	<header class="header">
		<div>
			<a href="/" class="back-link">← Kembali ke Beranda</a>
			<p class="eyebrow">Admin & Finance Review Portal</p>
			<h1>Review & Eskalasi Klaim</h1>
			<p class="subtitle">
				Tinjau nota operasional yang membutuhkan persetujuan manual (nominal di atas limit, skor anomali, atau nota kurang jelas).
			</p>
		</div>
		<div class="header-actions">
			<button class="btn-secondary" onclick={exportToCSV}>
				📥 Unduh CSV (FR-14)
			</button>
		</div>
	</header>

	<!-- Ringkasan Cepat -->
	<section class="stats-grid">
		<div class="stat-card urgent">
			<span class="stat-label">Perlu Review Manual</span>
			<span class="stat-value">{pendingCount}</span>
			<span class="stat-hint">{pendingCount > 0 ? 'Menunggu keputusan reviewer' : 'Semua antrean selesai! 🎉'}</span>
		</div>
		<div class="stat-card">
			<span class="stat-label">Selesai Ditinjau</span>
			<span class="stat-value">{decidedCount}</span>
			<span class="stat-hint">Keputusan terekam sebagai jejak audit</span>
		</div>
		<div class="stat-card">
			<span class="stat-label">Total Antrean Eskalasi</span>
			<span class="stat-value">{queue.length}</span>
			<span class="stat-hint">Diteruskan agent ke reviewer manusia (FR-10)</span>
		</div>
	</section>

	<!-- Filter & Search Bar -->
	<div class="toolbar">
		<div class="search-box">
			🔍 <input type="text" placeholder="Cari ID klaim atau nama karyawan..." bind:value={searchQuery} />
		</div>
	</div>

	<!-- Tabel Antrean Review -->
	<section class="table-container">
		<div class="table-header">
			<h2>Daftar Antrean Klaim (Eskalasi)</h2>
			<span class="badge-count">{pendingCount} Klaim Perlu Tindakan</span>
		</div>

		{#if loading}
			<div class="queue-state" role="status">
				<span class="spin" aria-hidden="true">⟳</span> Memuat antrean review...
			</div>
		{:else if loadError}
			<div class="queue-state error" role="alert">
				<p>{loadError}</p>
				<button type="button" class="btn-approve" onclick={load}>Coba lagi</button>
			</div>
		{:else if filteredQueue.length === 0}
			<div class="empty-state">
				<p>{queue.length === 0 ? 'Antrean kosong — tidak ada klaim yang dieskalasi.' : 'Tidak ada klaim yang cocok dengan pencarian.'}</p>
			</div>
		{:else}
			<table class="review-table">
				<thead>
					<tr>
						<th>ID & Karyawan</th>
						<th>Diajukan</th>
						<th>Nominal</th>
						<th>Alasan Eskalasi AI</th>
						<th>Status</th>
						<th>Aksi</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredQueue as item (item.review.id)}
						<tr class:resolved={item.review.status !== 'open'}>
							<td>
								<strong>{shortClaimRef(item.claim.id)}</strong>
								<div class="user-sub">{item.claim.employee_id}</div>
							</td>
							<td>{formatDateTime(item.claim.submitted_at)}</td>
							<td class="amount">{formatCurrency(item.claim.declared_amount, item.claim.currency)}</td>
							<td>
								<span class="badge {item.decision?.outcome === 'rejected' ? 'danger' : 'warning'}">{primaryReason(item)}</span>
								<p class="ai-reason">{item.decision?.explanation ?? 'Agent meneruskan klaim ini ke reviewer manusia.'}</p>
								<button class="btn-inspect" onclick={() => (activeSignals = item)}>
									🔍 Lihat Bukti & Log AI
								</button>
							</td>
							<td>
								<StatusBadge status={item.claim.status} size="sm" />
								<div class="review-state">
									{item.review.status === 'open' ? '⏳ Menunggu review' : `✓ Review selesai${item.review.reviewer_reference ? ` · ${item.review.reviewer_reference}` : ''}`}
								</div>
							</td>
							<td>
								{#if item.review.status === 'open'}
									<div class="action-buttons">
										<button class="btn-approve" onclick={() => openDecisionModal(item, 'approve')}>Setujui</button>
										<button class="btn-reject" onclick={() => openDecisionModal(item, 'reject')}>Tolak</button>
									</div>
								{:else}
									<span class="text-done">Selesai</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
</main>

<!-- Modal Bukti & Audit Trail (FR-06/07/12) — hanya data dari API -->
{#if activeSignals}
	<div class="modal-backdrop" role="presentation">
		<div class="modal-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Bukti dan log AI klaim">
			<div class="modal-header">
				<div>
					<span class="eyebrow">Audit Trail & Bukti Signal</span>
					<h3>Klaim {shortClaimRef(activeSignals.claim.id)} · {activeSignals.claim.employee_id}</h3>
				</div>
				<button class="btn-close" onclick={() => (activeSignals = null)}>✕</button>
			</div>

			<div class="modal-body">
				<!-- Kolom Kiri: Ringkasan klaim dari API -->
				<div class="receipt-mockup">
					<div class="receipt-paper">
						<div class="receipt-header">
							<h4>Ringkasan Klaim</h4>
							<p>Diajukan: {formatDateTime(activeSignals.claim.submitted_at)}</p>
							<p class="receipt-dash">--------------------------------</p>
						</div>
						<div class="receipt-items">
							<div class="receipt-row"><span>Nominal</span><span>{formatCurrency(activeSignals.claim.declared_amount, activeSignals.claim.currency)}</span></div>
							<div class="receipt-row"><span>Status klaim</span><span>{activeSignals.claim.status}</span></div>
							<div class="receipt-row"><span>Status review</span><span>{activeSignals.review.status}</span></div>
						</div>
						{#if activeSignals.decision}
							<div class="receipt-dash">--------------------------------</div>
							<div class="receipt-total">
								<strong>Keyakinan:</strong>
								<strong>{formatConfidence(activeSignals.decision.confidence)}</strong>
							</div>
							<div class="ocr-watermark">
								<span>Keputusan backend · {formatDateTime(activeSignals.decision.created_at)}</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Kolom Kanan: Keputusan + Signal duplikat/anomali -->
				<div class="audit-log">
					<h4>Keputusan Agent (FR-08)</h4>
					<p class="ai-reason">{activeSignals.decision?.explanation ?? 'Belum ada keputusan backend.'}</p>
					{#if activeSignals.decision}
						<div class="reason-chips">
							{#each describeReasonCodes(activeSignals.decision.reason_codes) as reason (reason.label)}
								<span class="tag">{reason.label}</span>
							{/each}
						</div>
					{/if}

					<h4 style="margin-top: 1.1rem;">Signal Duplikat & Anomali (FR-06/07)</h4>
					{#if activeSignals.signals.length === 0}
						<p class="ai-reason">Tidak ada signal dari backend untuk klaim ini.</p>
					{:else}
						<div class="timeline">
							{#each activeSignals.signals as signal (signal.id)}
								<div class="timeline-item">
									<div class="timeline-badge {signal.severity === 'blocking' ? 'WARN' : 'PASS'}">
										{signal.signal_type === 'duplicate' ? '⧉' : '⚠'}
									</div>
									<div class="timeline-content">
										<strong>{signal.signal_type === 'duplicate' ? 'Duplikat' : 'Anomali'} · {severityLabel(signal.severity)}</strong>
										<p>{signal.explanation}</p>
										{#if signal.score != null}<p class="signal-meta">Skor: {formatConfidence(signal.score)}</p>{/if}
										{#if signal.matched_claim_ids.length}
											<p class="signal-meta">Klaim terkait: {signal.matched_claim_ids.map((id) => shortClaimRef(id)).join(', ')}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}

					<div class="modal-actions-bar">
						{#if activeSignals.review.status === 'open'}
							<button class="btn-approve full" onclick={() => openDecisionModal(activeSignals!, 'approve')}>
								✓ Setujui Klaim Ini
							</button>
							<button class="btn-reject full" onclick={() => openDecisionModal(activeSignals!, 'reject')}>
								✕ Tolak Klaim
							</button>
						{:else}
							<p class="status-summary">
								Review selesai{activeSignals.review.reviewer_reference ? ` oleh ${activeSignals.review.reviewer_reference}` : ''}: <strong>{activeSignals.review.action ?? '-'}</strong>
							</p>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Modal Konfirmasi Keputusan (FR-10: konfirmasi eksplisit + alasan wajib) -->
{#if decisionTarget}
	<div class="modal-backdrop" role="presentation">
		<div class="modal-dialog decision-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Konfirmasi keputusan review">
			<div class="modal-header">
				<div>
					<span class="eyebrow">Konfirmasi Keputusan</span>
					<h3>{decisionAction === 'approve' ? '✓ Setujui' : '✕ Tolak'} klaim {shortClaimRef(decisionTarget.claim.id)}</h3>
				</div>
				<button class="btn-close" onclick={closeDecisionModal}>✕</button>
			</div>
			<div class="decision-modal-body">
				<p class="ai-reason">
					Keputusan ini akan dicatat sebagai keputusan resmi atas nama
					<strong>{CURRENT_REVIEWER_ID}</strong> dan tidak dapat diubah dari UI.
				</p>
				<label class="reason-label" for="decision-reason">Alasan keputusan (wajib)</label>
				<textarea
					id="decision-reason"
					bind:value={decisionReason}
					rows="3"
					placeholder={decisionAction === 'approve' ? 'Contoh: Nota dan konteks klarifikasi sudah meyakinkan.' : 'Contoh: Tidak sesuai kebijakan perusahaan.'}
				></textarea>
				{#if decisionError}
					<p class="decision-error" role="alert">{decisionError}</p>
				{/if}
				<div class="modal-actions-bar">
					<button class="btn-secondary" type="button" onclick={closeDecisionModal} disabled={submittingDecision}>
						Batal
					</button>
					<button
						class="{decisionAction === 'approve' ? 'btn-approve' : 'btn-reject'} full"
						type="button"
						onclick={submitDecision}
						disabled={submittingDecision}
					>
						{submittingDecision ? 'Mengirim...' : decisionAction === 'approve' ? '✓ Konfirmasi Persetujuan' : '✕ Konfirmasi Penolakan'}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	main {
		max-width: 1140px;
		margin: 0 auto;
		padding: 2.5rem 2rem;
		box-sizing: border-box;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
	}

	.back-link {
		color: #55745a;
		text-decoration: none;
		font-weight: 600;
		font-size: 0.9rem;
		display: inline-block;
		margin-bottom: 0.6rem;
	}

	.eyebrow {
		margin: 0 0 0.35rem;
		color: #55745a;
		font-size: 0.8rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	h1 {
		margin: 0;
		font-size: 2.3rem;
		letter-spacing: -0.04em;
		color: #172018;
	}

	.subtitle {
		margin: 0.5rem 0 0;
		color: #5b665c;
		font-size: 1rem;
		max-width: 650px;
	}

	.btn-secondary {
		background: #ffffff;
		border: 1px solid #c9d6c7;
		color: #27452a;
		padding: 0.65rem 1.1rem;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		font-size: 0.9rem;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
	}

	.btn-secondary:hover {
		background: #f4f7f3;
	}

	/* Stats */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1.2rem;
		margin-bottom: 2rem;
	}

	.stat-card {
		background: #ffffff;
		border: 1px solid #dce4da;
		border-radius: 12px;
		padding: 1.4rem;
		display: flex;
		flex-direction: column;
	}

	.stat-card.urgent {
		border-color: #f0c57c;
		background: #fffdf8;
	}

	.stat-label {
		font-size: 0.82rem;
		font-weight: 600;
		color: #637064;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		font-size: 2.2rem;
		font-weight: 800;
		color: #172018;
		margin: 0.4rem 0;
	}

	.stat-card.urgent .stat-value {
		color: #b45309;
	}

	.stat-hint {
		font-size: 0.85rem;
		color: #7b887c;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		gap: 1rem;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.2rem;
		flex-wrap: wrap;
	}

	.search-box {
		background: white;
		border: 1px solid #dce4da;
		border-radius: 8px;
		padding: 0.5rem 0.85rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		min-width: 260px;
	}

	.search-box input {
		border: none;
		outline: none;
		width: 100%;
		font-size: 0.9rem;
	}



	/* Table */
	.table-container {
		background: #ffffff;
		border: 1px solid #dce4da;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
	}

	.table-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.2rem 1.5rem;
		border-bottom: 1px solid #eef2ed;
	}

	.table-header h2 {
		margin: 0;
		font-size: 1.25rem;
		color: #172018;
	}

	.badge-count {
		background: #fef3c7;
		color: #92400e;
		font-weight: 600;
		font-size: 0.8rem;
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
	}

	.review-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
	}

	.review-table th {
		background: #f9faf8;
		padding: 0.9rem 1.2rem;
		font-size: 0.82rem;
		font-weight: 700;
		color: #556356;
		text-transform: uppercase;
		border-bottom: 1px solid #e2e8e0;
	}

	.review-table td {
		padding: 1.1rem 1.2rem;
		border-bottom: 1px solid #f0f4ef;
		vertical-align: top;
		font-size: 0.92rem;
	}

	tr.resolved {
		background: #fafbfa;
		opacity: 0.75;
	}

	.user-sub {
		font-size: 0.85rem;
		color: #2b392c;
		font-weight: 600;
		margin-top: 0.2rem;
	}



	.tag {
		background: #edf3ec;
		color: #2e5434;
		padding: 0.2rem 0.55rem;
		border-radius: 6px;
		font-size: 0.78rem;
		font-weight: 600;
	}

	.amount {
		font-weight: 700;
		color: #1b261c;
		white-space: nowrap;
	}

	.badge {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.2rem 0.5rem;
		border-radius: 6px;
		margin-bottom: 0.35rem;
	}

	.badge.warning { background: #fef3c7; color: #92400e; }
	.badge.danger { background: #fee2e2; color: #991b1b; }

	.ai-reason {
		margin: 0 0 0.5rem;
		font-size: 0.82rem;
		color: #5d6b5e;
		line-height: 1.35;
	}

	.btn-inspect {
		background: none;
		border: 1px dashed #7a947d;
		color: #2a4c2e;
		font-size: 0.78rem;
		font-weight: 600;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		cursor: pointer;
	}

	.btn-inspect:hover {
		background: #eaf1e8;
	}


	.action-buttons {
		display: flex;
		gap: 0.4rem;
	}

	.btn-approve {
		background: #36593b;
		color: white;
		border: none;
		border-radius: 6px;
		padding: 0.45rem 0.8rem;
		font-weight: 600;
		font-size: 0.82rem;
		cursor: pointer;
	}

	.btn-approve:hover { background: #27422b; }

	.btn-reject {
		background: #ffffff;
		color: #b91c1c;
		border: 1px solid #fca5a5;
		border-radius: 6px;
		padding: 0.45rem 0.8rem;
		font-weight: 600;
		font-size: 0.82rem;
		cursor: pointer;
	}

	.btn-reject:hover { background: #fef2f2; }

	.text-done {
		color: #889689;
		font-size: 0.85rem;
		font-style: italic;
	}

	.empty-state {
		padding: 3rem;
		text-align: center;
		color: #7b887c;
	}

	/* Modal */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(18, 25, 19, 0.55);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 999;
		backdrop-filter: blur(2px);
	}

	.modal-dialog {
		background: white;
		width: 90%;
		max-width: 860px;
		border-radius: 14px;
		overflow: hidden;
		box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15);
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}

	.modal-header {
		padding: 1.2rem 1.6rem;
		border-bottom: 1px solid #eef2ed;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.modal-header h3 {
		margin: 0.2rem 0 0;
		color: #172018;
		font-size: 1.3rem;
	}

	.btn-close {
		background: none;
		border: none;
		font-size: 1.3rem;
		cursor: pointer;
		color: #637064;
	}

	.modal-body {
		padding: 1.6rem;
		display: grid;
		grid-template-columns: 1fr 1.3fr;
		gap: 1.5rem;
		overflow-y: auto;
	}

	/* Receipt Mockup */
	.receipt-mockup {
		background: #f0f3ef;
		padding: 1rem;
		border-radius: 8px;
		display: flex;
		justify-content: center;
	}

	.receipt-paper {
		background: white;
		width: 100%;
		padding: 1.2rem;
		border-radius: 4px;
		box-shadow: 0 4px 6px rgba(0,0,0,0.05);
		font-family: monospace;
		font-size: 0.85rem;
		color: #2b392c;
	}

	.receipt-header h4 {
		margin: 0 0 0.3rem;
		font-size: 0.95rem;
		text-align: center;
	}

	.receipt-header p {
		margin: 0;
		text-align: center;
		color: #6d7b6f;
	}

	.receipt-dash {
		text-align: center;
		color: #cbd5cb;
		margin: 0.6rem 0;
	}

	.receipt-row {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.4rem;
	}

	.receipt-total {
		display: flex;
		justify-content: space-between;
		font-size: 0.95rem;
		margin-top: 0.5rem;
	}

	.ocr-watermark {
		margin-top: 1.2rem;
		background: #eaf3e8;
		color: #2e5434;
		padding: 0.4rem;
		border-radius: 4px;
		text-align: center;
		font-size: 0.75rem;
		font-weight: bold;
	}

	/* Timeline Audit */
	.audit-log h4 {
		margin: 0 0 1rem;
		color: #172018;
	}

		.timeline {
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.timeline-item {
		display: flex;
		gap: 0.8rem;
		align-items: flex-start;
	}

	.timeline-badge {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		font-weight: bold;
		flex-shrink: 0;
	}

	.timeline-badge.PASS { background: #dcfce7; color: #166534; }
	.timeline-badge.WARN { background: #fef3c7; color: #92400e; }

	.timeline-content strong {
		font-size: 0.85rem;
		color: #202b21;
	}

	.timeline-content p {
		margin: 0.2rem 0 0;
		font-size: 0.8rem;
		color: #5d6b5e;
		line-height: 1.35;
	}

	.modal-actions-bar {
		margin-top: 1.5rem;
		display: flex;
		gap: 0.6rem;
		padding-top: 1rem;
		border-top: 1px solid #eef2ed;
	}

	.btn-approve.full, .btn-reject.full {
		flex: 1;
		padding: 0.65rem;
		font-size: 0.88rem;
	}

	.status-summary {
		font-size: 0.9rem;
		color: #556356;
		margin: 0;
	}
	/* Queue states (loading / error) */
	.queue-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 3rem;
		color: #637064;
		font-weight: 600;
	}

	.queue-state.error {
		flex-direction: column;
		gap: 0.75rem;
		color: #b91c1c;
	}

	.queue-state .spin {
		display: inline-block;
		animation: reviewSpin 0.8s linear infinite;
		font-size: 1.2rem;
	}

	@keyframes reviewSpin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.review-state {
		font-size: 0.75rem;
		color: #637064;
		margin-top: 0.3rem;
	}

	.reason-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin-bottom: 0.5rem;
	}

	.signal-meta {
		font-size: 0.72rem;
		color: #637064;
		margin: 0.15rem 0 0;
	}

	/* Decision modal */
	.decision-dialog {
		max-width: 480px;
		width: min(480px, 92vw);
	}

	.decision-modal-body {
		padding: 0 1.5rem 1.5rem;
	}

	.reason-label {
		display: block;
		font-size: 0.82rem;
		font-weight: 700;
		color: #2b392c;
		margin: 0.9rem 0 0.35rem;
	}

	.decision-modal-body textarea {
		width: 100%;
		box-sizing: border-box;
		border: 1px solid #c9d6c7;
		border-radius: 8px;
		padding: 0.65rem 0.8rem;
		font: inherit;
		font-size: 0.9rem;
		resize: vertical;
		outline: none;
	}

	.decision-modal-body textarea:focus {
		border-color: #36593b;
		box-shadow: 0 0 0 3px rgba(54, 89, 59, 0.12);
	}

	.decision-error {
		margin: 0.5rem 0 0;
		font-size: 0.8rem;
		font-weight: 600;
		color: #b91c1c;
	}
</style>