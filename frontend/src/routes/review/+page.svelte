<script lang="ts">
	import { onMount } from 'svelte';
	import { listReviews, decideReview, CURRENT_REVIEWER_ID } from '$lib/api/reviews';
	import { getClaim } from '$lib/api/claims';
	import { formatCurrency, formatConfidence, toNumber } from '$lib/formatters/currency';
	import { formatDate, formatDateTime } from '$lib/formatters/date';
	import type { ReviewQueueItem, ClaimDetailResponse } from '$lib/types/claim';

	// State antrean review dari backend
	let loading = $state<boolean>(true);
	let error = $state<string | null>(null);
	let reviewQueue = $state<ReviewQueueItem[]>([]);
	let searchQuery = $state<string>('');
	let toastMessage = $state<string | null>(null);

	// State modal inspeksi detail klaim (Audit Trail asli)
	let activeDetail = $state<ClaimDetailResponse | null>(null);
	let loadingDetail = $state<boolean>(false);

	// State modal konfirmasi keputusan (FR-10: wajib ada konfirmasi & alasan reviewer)
	let confirmAction = $state<{
		isOpen: boolean;
		claimId: string;
		action: 'approve' | 'reject';
		reason: string;
		submitting: boolean;
	}>({
		isOpen: false,
		claimId: '',
		action: 'approve',
		reason: '',
		submitting: false
	});

	// Ambil antrean review saat halaman dibuka
	async function fetchReviewQueue() {
		loading = true;
		error = null;
		try {
			const res = await listReviews();
			reviewQueue = res.items;
		} catch (err) {
			console.error('Gagal memuat antrean review:', err);
			error = err instanceof Error ? err.message : 'Gagal terhubung ke backend.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchReviewQueue();
	});

	function showToast(msg: string) {
		toastMessage = msg;
		setTimeout(() => {
			toastMessage = null;
		}, 3500);
	}

	// Buka modal detail untuk melihat audit trail riil dari backend
	async function openInspectModal(claimId: string) {
		loadingDetail = true;
		try {
			activeDetail = await getClaim(claimId);
		} catch (err) {
			console.error('Gagal mengambil detail klaim:', err);
			showToast('❌ Gagal memuat detail nota dari server.');
		} finally {
			loadingDetail = false;
		}
	}

	// Buka dialog konfirmasi alasan sebelum submit ke API backend (FR-10)
	function initiateDecision(claimId: string, action: 'approve' | 'reject') {
		confirmAction = {
			isOpen: true,
			claimId,
			action,
			reason: action === 'approve' ? 'Dokumen dan nominal telah diverifikasi sesuai kebijakan operasional.' : '',
			submitting: false
		};
	}

	// Kirim keputusan reviewer ke backend POST /reviews/{claim_id}/decision
	async function submitDecision() {
		if (!confirmAction.reason.trim()) {
			alert('Mohon cantumkan alasan keputusan reviewer.');
			return;
		}

		confirmAction.submitting = true;
		try {
			await decideReview({
				claimId: confirmAction.claimId,
				action: confirmAction.action,
				reason: confirmAction.reason.trim(),
				reviewerReference: CURRENT_REVIEWER_ID
			});

			showToast(
				confirmAction.action === 'approve'
					? `✅ Klaim berhasil DISETUJUI oleh ${CURRENT_REVIEWER_ID}.`
					: `❌ Klaim berhasil DITOLAK oleh ${CURRENT_REVIEWER_ID}.`
			);

			confirmAction.isOpen = false;
			if (activeDetail?.claim.id === confirmAction.claimId) {
				activeDetail = null;
			}

			// Perbarui antrean dari server
			await fetchReviewQueue();
		} catch (err) {
			console.error('Gagal mengirim keputusan:', err);
			alert('Gagal mengirim keputusan: ' + (err instanceof Error ? err.message : 'Error server'));
		} finally {
			confirmAction.submitting = false;
		}
	}

	// Filter pencarian
	let filteredQueue = $derived(
		reviewQueue.filter((item) => {
			const idMatch = item.claim.id.toLowerCase().includes(searchQuery.toLowerCase());
			const empMatch = item.claim.employee_id.toLowerCase().includes(searchQuery.toLowerCase());
			return idMatch || empMatch;
		})
	);
</script>

<svelte:head>
	<title>Expense Agent - Human Review Portal</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

{#if toastMessage}
	<div class="toast-notification">
		{toastMessage}
	</div>
{/if}

<div class="review-wrapper">
	<!-- Top Navigation Bar -->
	<header class="top-nav">
		<div class="brand">
			<a href="/" class="brand-logo">
				<span class="logo-dot"></span>
				ExpenseAgent
			</a>
			<span class="page-title">/ Human Review Portal (FR-10)</span>
		</div>

		<div class="top-controls">
			<a href="/dashboard" class="btn-dashboard-link">
				📊 Buka Analytics Dashboard
			</a>
			<button class="btn-refresh" onclick={fetchReviewQueue} disabled={loading}>
				{loading ? '⟳ Memuat...' : '⟳ Refresh Antrean'}
			</button>
		</div>
	</header>

	<!-- Stat Cards -->
	<section class="stat-cards-grid">
		<div class="gradient-card orange">
			<div class="card-top">
				<span class="card-icon">⚠️</span>
				<span class="card-title">Antrean Eskalasi Aktif</span>
			</div>
			<div class="card-value">{reviewQueue.length}</div>
			<div class="card-sub">Menunggu tindakan manual reviewer</div>
			<div class="card-wave"></div>
		</div>

		<div class="gradient-card purple">
			<div class="card-top">
				<span class="card-icon">👤</span>
				<span class="card-title">Identitas Reviewer</span>
			</div>
			<div class="card-value small">{CURRENT_REVIEWER_ID}</div>
			<div class="card-sub">Tercatat di backend audit log (FR-10)</div>
			<div class="card-wave"></div>
		</div>

		<div class="gradient-card blue">
			<div class="card-top">
				<span class="card-icon">⚡</span>
				<span class="card-title">Status API Backend</span>
			</div>
			<div class="card-value small">{error ? 'Offline' : 'Connected'}</div>
			<div class="card-sub">{error ? error : 'Tersinkron dengan FastAPI'}</div>
			<div class="card-wave"></div>
		</div>
	</section>

	<!-- Main Table Section -->
	<section class="card-panel">
		<div class="toolbar">
			<div class="search-pill">
				<span class="icon">🔍</span>
				<input
					type="text"
					placeholder="Cari berdasarkan UUID klaim atau ID Karyawan..."
					bind:value={searchQuery}
				/>
			</div>
		</div>

		{#if loading}
			<div class="state-box">
				<p>⏳ Menghubungkan ke backend dan memuat antrean review...</p>
			</div>
		{:else if error}
			<div class="state-box error">
				<p>❌ {error}</p>
				<button class="btn-retry" onclick={fetchReviewQueue}>Coba Lagi</button>
			</div>
		{:else if filteredQueue.length === 0}
			<div class="state-box empty">
				<p class="empty-icon">🎉</p>
				<h3>Semua Antrean Bersih!</h3>
				<p>Tidak ada klaim yang menunggu review manual dari reviewer saat ini.</p>
			</div>
		{:else}
			<div class="table-responsive">
				<table class="modern-table">
					<thead>
						<tr>
							<th>UUID Klaim</th>
							<th>Karyawan</th>
							<th>Diajukan</th>
							<th>Nominal</th>
							<th>Indikasi AI (Signals)</th>
							<th>Status</th>
							<th>Aksi Reviewer</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredQueue as item}
							<tr>
								<td>
									<span class="id-tag" title={item.claim.id}>
										{item.claim.id.slice(0, 8)}...
									</span>
								</td>
								<td><strong>{item.claim.employee_id}</strong></td>
								<td class="date-col">{formatDateTime(item.claim.submitted_at)}</td>
								<td class="amount">{formatCurrency(item.claim.declared_amount)}</td>
								<td class="reason-cell">
									{#if item.signals && item.signals.length > 0}
										{#each item.signals as sig}
											<span class="reason-badge danger">{sig.signal_type}: {sig.severity}</span>
											<p class="reason-desc">{sig.explanation}</p>
										{/each}
									{:else if item.decision}
										<span class="reason-badge warning">{item.decision.outcome}</span>
										<p class="reason-desc">{item.decision.explanation}</p>
									{:else}
										<span class="reason-badge info">Eskalasi Kebijakan</span>
										<p class="reason-desc">Klaim memerlukan verifikasi manual reviewer.</p>
									{/if}
									<button class="btn-inspect" onclick={() => openInspectModal(item.claim.id)}>
										🔍 Cek Bukti Struk & Log AI
									</button>
								</td>
								<td>
									<span class="status-pill warning">Review Open</span>
								</td>
								<td>
									<div class="action-btn-group">
										<button
											class="btn-approve"
											onclick={() => initiateDecision(item.claim.id, 'approve')}
										>
											Setujui
										</button>
										<button
											class="btn-reject"
											onclick={() => initiateDecision(item.claim.id, 'reject')}
										>
											Tolak
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>

<!-- Modal Pop-up Bukti Nota & Log Backend Asli (FR-12) -->
{#if activeDetail || loadingDetail}
	<div class="modal-backdrop" onclick={() => (activeDetail = null)} role="presentation">
		<div class="modal-dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
			<div class="modal-header">
				<div>
					<span class="modal-eyebrow">Audit Trail & Extraction Detail (FR-12)</span>
					<h3>
						Klaim #{activeDetail?.claim.id.slice(0, 8)} - {activeDetail?.claim.employee_id}
					</h3>
				</div>
				<button class="btn-close" onclick={() => (activeDetail = null)}>✕</button>
			</div>

			<div class="modal-body">
				{#if loadingDetail}
					<div class="modal-loading">Memuat data nota dari server...</div>
				{:else if activeDetail}
					<!-- Struk & Hasil Ekstraksi Vision Asli -->
					<div class="receipt-container">
						<div class="receipt-paper">
							<div class="receipt-header">
								<h4>{activeDetail.extractions[0]?.vendor.value ?? 'Vendor Tidak Terbaca'}</h4>
								<p>
									Tanggal Nota: {formatDate(String(activeDetail.extractions[0]?.receipt_date.value ?? ''))}
								</p>
								<div class="receipt-dash">--------------------------------</div>
							</div>

							<div class="receipt-items">
								{#if activeDetail.extractions[0]?.line_items?.length}
									{#each activeDetail.extractions[0].line_items as itm}
										<div class="receipt-row">
											<span>{itm.description}</span>
											<span>{formatCurrency(itm.total)}</span>
										</div>
									{/each}
								{:else}
									<p class="muted">Tidak ada rincian item baris tersimpan.</p>
								{/if}
							</div>

							<div class="receipt-dash">--------------------------------</div>
							<div class="receipt-total">
								<strong>TOTAL:</strong>
								<strong>
									{formatCurrency(toNumber(activeDetail.extractions[0]?.total.value as number | string | null) ?? activeDetail.claim.declared_amount)}
								</strong>
							</div>

							<div class="ocr-badge">
								✓ Total Confidence: {formatConfidence(activeDetail.extractions[0]?.total.confidence)}
							</div>
						</div>
					</div>

					<!-- Riwayat Tahapan Logika AI Asli dari Backend -->
					<div class="audit-flow">
						<h4>Riwayat Percobaan & Evaluasi (Backend State)</h4>
						<div class="timeline">
							{#each activeDetail.attempts as att}
								<div class="timeline-step">
									<div class="step-indicator {att.error_code ? 'FAIL' : 'PASS'}">
										{att.error_code ? '!' : '✓'}
									</div>
									<div class="step-details">
										<strong>Percobaan #{att.attempt}: {att.preprocessing.join(', ') || 'Ekstraksi Standar'}</strong>
										<p>{att.message || 'Ekstraksi OCR berhasil diproses tanpa error.'}</p>
										<span class="timestamp">{formatDateTime(att.created_at)}</span>
									</div>
								</div>
							{/each}

							{#if activeDetail.decisions?.length}
								{#each activeDetail.decisions as dec}
									<div class="timeline-step">
										<div class="step-indicator dec">⚖️</div>
										<div class="step-details">
											<strong>Keputusan Agen: {dec.outcome.toUpperCase()}</strong>
											<p>{dec.explanation}</p>
											<span class="timestamp">{formatDateTime(dec.created_at)}</span>
										</div>
									</div>
								{/each}
							{/if}
						</div>

						<div class="modal-footer-actions">
							<button
								class="btn-approve full"
								onclick={() => {
									if (activeDetail) initiateDecision(activeDetail.claim.id, 'approve');
								}}
							>
								✓ Setujui Klaim Ini
							</button>
							<button
								class="btn-reject full"
								onclick={() => {
									if (activeDetail) initiateDecision(activeDetail.claim.id, 'reject');
								}}
							>
								✕ Tolak Klaim
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Dialog Konfirmasi Keputusan Reviewer (Syarat FR-10) -->
{#if confirmAction.isOpen}
	<div class="modal-backdrop" onclick={() => (confirmAction.isOpen = false)} role="presentation">
		<div
			class="modal-dialog small"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
		>
			<div class="modal-header">
				<h3>Konfirmasi Keputusan Reviewer (FR-10)</h3>
				<button class="btn-close" onclick={() => (confirmAction.isOpen = false)}>✕</button>
			</div>
			<div class="confirm-body">
				<p>
					Anda akan <strong>{confirmAction.action === 'approve' ? 'MENYETUJUI' : 'MENOLAK'}</strong> klaim
					<code>{confirmAction.claimId.slice(0, 8)}...</code> sebagai reviewer
					<code>{CURRENT_REVIEWER_ID}</code>.
				</p>

				<label for="review-reason">
					<strong>Alasan Keputusan Reviewer (Wajib):</strong>
				</label>
				<textarea
					id="review-reason"
					bind:value={confirmAction.reason}
					placeholder="Tuliskan catatan pertimbangan reviewer..."
					rows="3"
				></textarea>

				<div class="confirm-actions">
					<button
						class="btn-cancel"
						onclick={() => (confirmAction.isOpen = false)}
						disabled={confirmAction.submitting}
					>
						Batal
					</button>
					<button
						class={confirmAction.action === 'approve' ? 'btn-approve' : 'btn-reject'}
						onclick={submitDecision}
						disabled={confirmAction.submitting}
					>
						{confirmAction.submitting ? 'Mengirim...' : 'Kirim Keputusan ke Backend'}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	:global(body) {
		margin: 0;
		background: #f1f4f9;
		font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
		color: #1e293b;
	}

	.review-wrapper {
		max-width: 1280px;
		margin: 0 auto;
		padding: 2rem 2.5rem;
		box-sizing: border-box;
	}

	.top-nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.brand-logo {
		font-size: 1.35rem;
		font-weight: 800;
		color: #0f172a;
		text-decoration: none;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		letter-spacing: -0.03em;
	}

	.logo-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: #7c3aed;
		box-shadow: 0 0 10px #7c3aed;
	}

	.page-title {
		color: #94a3b8;
		font-size: 0.95rem;
		font-weight: 600;
	}

	.top-controls {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		flex-wrap: wrap;
	}

	.btn-dashboard-link {
		background: #ffffff;
		color: #475569;
		border: 1px solid #e2e8f0;
		padding: 0.6rem 1.1rem;
		border-radius: 999px;
		font-weight: 700;
		font-size: 0.85rem;
		text-decoration: none;
		transition: all 0.2s;
	}

	.btn-refresh {
		background: #7c3aed;
		color: white;
		border: none;
		border-radius: 999px;
		padding: 0.6rem 1.25rem;
		font-weight: 700;
		font-size: 0.85rem;
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
	}

	.stat-cards-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.4rem;
		margin-bottom: 2rem;
	}

	.gradient-card {
		color: white;
		padding: 1.6rem;
		border-radius: 20px;
		position: relative;
		overflow: hidden;
		box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.12);
	}

	.gradient-card.orange {
		background: linear-gradient(135deg, #ea580c, #f59e0b);
	}
	.gradient-card.purple {
		background: linear-gradient(135deg, #7c3aed, #a855f7);
	}
	.gradient-card.blue {
		background: linear-gradient(135deg, #2563eb, #38bdf8);
	}

	.card-top {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}
	.card-icon {
		font-size: 1.1rem;
	}
	.card-title {
		font-size: 0.82rem;
		font-weight: 600;
		text-transform: uppercase;
		opacity: 0.9;
	}
	.card-value {
		font-size: 2.3rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		margin-bottom: 0.35rem;
	}
	.card-value.small {
		font-size: 1.6rem;
	}
	.card-sub {
		font-size: 0.82rem;
		opacity: 0.85;
	}
	.card-wave {
		position: absolute;
		right: -20px;
		bottom: -20px;
		width: 100px;
		height: 100px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.12);
		pointer-events: none;
	}

	.card-panel {
		background: #ffffff;
		border-radius: 20px;
		padding: 1.8rem;
		box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
		border: 1px solid #f1f5f9;
	}

	.toolbar {
		margin-bottom: 1.5rem;
	}
	.search-pill {
		background: #f8fafc;
		border-radius: 999px;
		padding: 0.55rem 1.1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid #e2e8f0;
		max-width: 420px;
	}
	.search-pill input {
		border: none;
		outline: none;
		background: transparent;
		font-family: inherit;
		font-size: 0.85rem;
		width: 100%;
	}

	.state-box {
		padding: 3rem;
		text-align: center;
		color: #64748b;
	}
	.state-box.empty .empty-icon {
		font-size: 3rem;
		margin: 0;
	}
	.state-box.error {
		color: #ef4444;
	}
	.btn-retry {
		margin-top: 1rem;
		padding: 0.5rem 1rem;
		background: #7c3aed;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
	}

	.table-responsive {
		overflow-x: auto;
	}
	.modern-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
	}
	.modern-table th {
		padding: 0.9rem 1rem;
		color: #94a3b8;
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid #f1f5f9;
	}
	.modern-table td {
		padding: 1.2rem 1rem;
		font-size: 0.88rem;
		border-bottom: 1px solid #f8fafc;
		vertical-align: top;
	}

	.id-tag {
		background: #f1f5f9;
		color: #475569;
		font-weight: 700;
		font-size: 0.75rem;
		padding: 0.2rem 0.45rem;
		border-radius: 6px;
		font-family: monospace;
	}
	.date-col {
		color: #64748b;
		white-space: nowrap;
	}
	.amount {
		font-weight: 800;
		color: #0f172a;
		white-space: nowrap;
	}

	.reason-cell {
		max-width: 320px;
	}
	.reason-badge {
		display: inline-block;
		font-size: 0.72rem;
		font-weight: 700;
		padding: 0.15rem 0.5rem;
		border-radius: 6px;
		margin-bottom: 0.3rem;
	}
	.reason-badge.warning {
		background: #fff7ed;
		color: #c2410c;
	}
	.reason-badge.danger {
		background: #fef2f2;
		color: #b91c1c;
	}
	.reason-badge.info {
		background: #f0fdf4;
		color: #15803d;
	}
	.reason-desc {
		margin: 0 0 0.5rem;
		font-size: 0.8rem;
		color: #64748b;
		line-height: 1.35;
	}

	.btn-inspect {
		background: #f8fafc;
		border: 1px dashed #cbd5e1;
		color: #64748b;
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.25rem 0.6rem;
		border-radius: 6px;
		cursor: pointer;
	}
	.status-pill {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
	}
	.status-pill.warning {
		background: #fff7ed;
		color: #c2410c;
	}

	.action-btn-group {
		display: flex;
		gap: 0.4rem;
	}
	.btn-approve {
		background: #10b981;
		color: white;
		border: none;
		border-radius: 8px;
		padding: 0.45rem 0.85rem;
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
	}
	.btn-reject {
		background: white;
		color: #ef4444;
		border: 1px solid #fecaca;
		border-radius: 8px;
		padding: 0.45rem 0.85rem;
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.toast-notification {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		background: #0f172a;
		color: #ffffff;
		padding: 0.85rem 1.4rem;
		border-radius: 12px;
		font-weight: 600;
		font-size: 0.88rem;
		box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
		z-index: 1000;
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(15, 23, 42, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 999;
		backdrop-filter: blur(4px);
	}
	.modal-dialog {
		background: white;
		width: 90%;
		max-width: 860px;
		border-radius: 20px;
		overflow: hidden;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}
	.modal-dialog.small {
		max-width: 480px;
	}
	.modal-header {
		padding: 1.4rem 1.8rem;
		border-bottom: 1px solid #f1f5f9;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.modal-eyebrow {
		font-size: 0.78rem;
		font-weight: 700;
		color: #7c3aed;
		text-transform: uppercase;
	}
	.btn-close {
		background: #f1f5f9;
		border: none;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		cursor: pointer;
	}
	.modal-body {
		padding: 1.8rem;
		display: grid;
		grid-template-columns: 1fr 1.3fr;
		gap: 1.6rem;
		overflow-y: auto;
	}
	.modal-loading {
		padding: 3rem;
		text-align: center;
		grid-column: 1 / -1;
	}

	.receipt-container {
		background: #f8fafc;
		padding: 1rem;
		border-radius: 14px;
	}
	.receipt-paper {
		background: white;
		padding: 1.2rem;
		border-radius: 8px;
		font-family: monospace;
		font-size: 0.85rem;
	}
	.receipt-header h4 {
		margin: 0;
		text-align: center;
	}
	.receipt-header p {
		margin: 0;
		text-align: center;
		color: #94a3b8;
		font-size: 0.8rem;
	}
	.receipt-dash {
		text-align: center;
		color: #cbd5e1;
		margin: 0.5rem 0;
	}
	.receipt-row {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.35rem;
	}
	.receipt-total {
		display: flex;
		justify-content: space-between;
		font-size: 0.95rem;
	}
	.ocr-badge {
		margin-top: 1rem;
		background: #f5f3ff;
		color: #7c3aed;
		padding: 0.4rem;
		border-radius: 6px;
		text-align: center;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.audit-flow h4 {
		margin: 0 0 1rem;
	}
	.timeline {
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}
	.timeline-step {
		display: flex;
		gap: 0.8rem;
		align-items: flex-start;
	}
	.step-indicator {
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
	.step-indicator.PASS {
		background: #dcfce7;
		color: #15803d;
	}
	.step-indicator.FAIL {
		background: #fee2e2;
		color: #b91c1c;
	}
	.step-indicator.dec {
		background: #f5f3ff;
	}
	.step-details strong {
		font-size: 0.85rem;
	}
	.step-details p {
		margin: 0.2rem 0;
		font-size: 0.8rem;
		color: #64748b;
	}
	.timestamp {
		font-size: 0.72rem;
		color: #94a3b8;
	}

	.modal-footer-actions {
		margin-top: 1.5rem;
		display: flex;
		gap: 0.6rem;
		padding-top: 1rem;
		border-top: 1px solid #f1f5f9;
	}
	.btn-approve.full,
	.btn-reject.full {
		flex: 1;
		padding: 0.65rem;
	}

	.confirm-body {
		padding: 1.5rem;
	}
	.confirm-body p {
		margin: 0 0 1rem;
		font-size: 0.9rem;
		color: #475569;
	}
	.confirm-body code {
		background: #f1f5f9;
		padding: 0.15rem 0.4rem;
		border-radius: 4px;
	}
	.confirm-body label {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.85rem;
	}
	.confirm-body textarea {
		width: 100%;
		box-sizing: border-box;
		border: 1px solid #cbd5e1;
		border-radius: 8px;
		padding: 0.6rem;
		font-family: inherit;
		font-size: 0.85rem;
		outline: none;
		margin-bottom: 1.2rem;
	}
	.confirm-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.6rem;
	}
	.btn-cancel {
		background: #f1f5f9;
		border: none;
		border-radius: 8px;
		padding: 0.5rem 1rem;
		cursor: pointer;
		font-weight: 600;
	}
</style>