<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { page } from '$app/state';
	import Toast from '$lib/components/Toast.svelte';
	import { modalFocus } from '$lib/actions/modalFocus';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import ClaimAmount from '$lib/components/ClaimAmount.svelte';
	import { listReviews, decideReview } from '$lib/api/reviews';
	import { ApiError } from '$lib/api/client';
	import { showToast } from '$lib/stores/toast.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDateTime } from '$lib/formatters/date';
	import { formatCurrency, formatConfidence } from '$lib/formatters/currency';
	import { describeReasonCodes } from '$lib/formatters/reasonCodes';
	import { downloadReport } from '$lib/api/reports';
	import AnomalyBadge from '$lib/components/AnomalyBadge.svelte';
	import type { ReviewQueueItem, Signal } from '$lib/types/claim';

	let queue = $state<ReviewQueueItem[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let searchQuery = $state('');
	let riskFilter = $state<'all' | 'high' | 'normal' | 'anomaly'>('all');
	let ageFilter = $state<'all' | 'old'>('all');

	// FR-10: keputusan reviewer selalu lewat konfirmasi + alasan eksplisit
	let decisionTarget = $state<ReviewQueueItem | null>(null);
	let decisionAction = $state<'approve' | 'reject'>('approve');
	let decisionReason = $state('');
	let finalAmount = $state('');
	let submittingDecision = $state(false);
	let decisionError = $state<string | null>(null);

	// Bukti signal (duplikat/anomali) yang sedang dilihat reviewer
	let activeSignals = $state<ReviewQueueItem | null>(null);

	function getAnomalySignal(item: ReviewQueueItem): Signal | null {
		return item.signals.find((s) => s.signal_type === 'anomaly') ?? null;
	}

	function isHighAnomaly(item: ReviewQueueItem): boolean {
		const decScore = item.decision?.anomaly_score != null ? Number(item.decision.anomaly_score) : null;
		const sig = getAnomalySignal(item);
		const sigScore = sig?.score != null ? Number(sig.score) : null;
		return (decScore != null && decScore >= 0.7) || (sigScore != null && sigScore >= 0.7) || sig?.severity === 'warning' || sig?.severity === 'blocking';
	}

	let pendingCount = $derived(queue.filter((item) => item.review.status === 'open').length);
	let highRiskCount = $derived(queue.filter((item) => item.signals.some((signal) => signal.severity === 'blocking' || signal.severity === 'warning')).length);
	let mlAnomalyCount = $derived(queue.filter(isHighAnomaly).length);
	let olderCount = $derived(queue.filter((item) => Date.now() - new Date(item.review.created_at).getTime() >= 3 * 86_400_000).length);
	let filteredQueue = $derived(
		queue.filter((item) => {
			const q = searchQuery.trim().toLowerCase();
			const matchesSearch = !q || (
				shortClaimRef(item.claim.id).toLowerCase().includes(q) ||
				item.claim.employee_id.toLowerCase().includes(q)
			);
			const hasHighRisk = item.signals.some((signal) => signal.severity === 'blocking' || signal.severity === 'warning');
			const matchesRisk = riskFilter === 'all' || (
				riskFilter === 'high' ? hasHighRisk :
				riskFilter === 'anomaly' ? isHighAnomaly(item) :
				!hasHighRisk
			);
			const ageDays = Math.floor((Date.now() - new Date(item.review.created_at).getTime()) / 86_400_000);
			const matchesAge = ageFilter === 'all' || ageDays >= 3;
			return matchesSearch && matchesRisk && matchesAge;
		})
	);

	async function load() {
		loading = true;
		loadError = null;
		try {
			const response = await listReviews();
			queue = response.items.filter((item) => item.review.status === 'open').sort((a, b) => a.review.created_at.localeCompare(b.review.created_at));
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
		finalAmount = item.claim.amount?.complete ? String(item.claim.amount.value ?? '') : '';
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
				reason,
				finalAmount
			});
			showToast(
				`Klaim ${shortClaimRef(response.claim.id)} ${
					decisionAction === 'approve' ? 'disetujui' : 'ditolak'
				}. Tercatat atas nama ${response.review.reviewer_reference ?? page.data.admin?.username}.`,
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

	async function exportToCSV() {
		if (loading) {
			showToast('Tunggu sampai antrean selesai dimuat.', 'error');
			return;
		}
		try {
			const blob = await downloadReport();
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `seluruh-klaim-${new Date().toISOString().slice(0, 10)}.csv`;
			link.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
			showToast('Laporan CSV berhasil diunduh.', 'success');
		} catch (error) {
			showToast(error instanceof Error ? error.message : 'Export gagal.', 'error');
		}
	}
</script>

<svelte:head>
	<title>Review klaim · Tera</title>
</svelte:head>

<Toast />

<main>
	<header class="header">
		<div>
			<h1>Antrean review</h1>
			<p class="subtitle">
				Tangani kasus yang diteruskan Tera. Klaim yang selesai otomatis tetap tercatat di Semua klaim. Antrean diurutkan dari review terlama.
			</p>
		</div>
		<div class="header-actions">
			<button class="btn-secondary" onclick={exportToCSV} disabled={loading}>
				<Icon name="chart" size={18} />
				Ekspor seluruh klaim
			</button>
		</div>
	</header>
	<div class="review-context"><strong>Keputusan berdasarkan bukti</strong><span>Periksa nota, hasil pembacaan, dan alasan eskalasi sebelum memutuskan. Persetujuan klaim belum berarti pembayaran.</span><a href="/admin/claims">Telusuri semua klaim</a></div>

	<!-- Ringkasan Cepat -->
	<section class="stats-grid">
		<div class="stat-card urgent">
			<span class="stat-label"><span class="stat-symbol"><Icon name="review" /></span>Perlu review manual</span>
			<span class="stat-value">{loading || loadError ? '...' : pendingCount}</span>
			<span class="stat-hint">{loading ? 'Memuat antrean...' : loadError ? 'Data belum tersedia' : pendingCount > 0 ? 'Menunggu keputusan reviewer' : 'Tidak ada klaim menunggu review'}</span>
		</div>
		<div class="stat-card">
			<span class="stat-label"><span class="stat-symbol warning"><Icon name="alert" /></span>Risiko tinggi</span>
			<span class="stat-value">{loading || loadError ? '...' : highRiskCount}</span>
			<span class="stat-hint">Memiliki temuan peringatan atau pemblokiran</span>
		</div>
		<div class="stat-card" class:urgent={mlAnomalyCount > 0}>
			<span class="stat-label"><span class="stat-symbol warning"><Icon name="alert" /></span>Anomali ML tinggi</span>
			<span class="stat-value">{loading || loadError ? '...' : mlAnomalyCount}</span>
			<span class="stat-hint">{mlAnomalyCount > 0 ? 'Deteksi model Isolation Forest ≥ 70%' : 'Tidak ada klaim anomali tinggi'}</span>
		</div>
		<div class="stat-card">
			<span class="stat-label"><span class="stat-symbol waiting"><Icon name="clock" /></span>Menunggu ≥ 3 hari</span>
			<span class="stat-value">{loading || loadError ? '...' : olderCount}</span>
			<span class="stat-hint">Klaim terbuka yang perlu segera ditinjau</span>
		</div>
	</section>

	<!-- Filter & Search Bar -->
	<div class="toolbar">
		<div class="search-box"><Icon name="search" size={18} />
			<input type="text" aria-label="Cari klaim" placeholder="Cari ID klaim atau karyawan..." bind:value={searchQuery} />
		</div>
		<select aria-label="Filter risiko" bind:value={riskFilter}>
			<option value="all">Semua risiko</option>
			<option value="high">Risiko tinggi</option>
			<option value="anomaly">Anomali ML tinggi (≥ 70%)</option>
			<option value="normal">Risiko normal</option>
		</select>
		<select aria-label="Filter usia klaim" bind:value={ageFilter}>
			<option value="all">Semua usia</option>
			<option value="old">Minimal 3 hari</option>
		</select>
	</div>

	<!-- Tabel Antrean Review -->
	<section class="table-container">
		<div class="table-header">
			<h2>Antrean pemeriksaan</h2>
			<span class="badge-count">{loading || loadError ? 'Data belum tersedia' : `${pendingCount} klaim perlu tindakan`}</span>
		</div>

		{#if loading}
			<div class="queue-state" role="status">
				<span class="spin"><Icon name="refresh" /></span> Memuat antrean review...
			</div>
		{:else if loadError}
			<div class="queue-state error" role="alert">
				<p>{loadError}</p>
				<button type="button" class="btn-approve" onclick={load}>Coba lagi</button>
			</div>
		{:else if filteredQueue.length === 0}
			<div class="empty-state">
				<span class="empty-symbol"><Icon name={queue.length === 0 ? 'check' : 'search'} size={28} /></span>
				<h3>{queue.length === 0 ? 'Antrean sudah beres' : 'Klaim tidak ditemukan'}</h3>
				<p>{queue.length === 0 ? 'Belum ada klaim yang membutuhkan review. Klaim yang diteruskan Tera akan muncul di sini.' : 'Tidak ada klaim yang cocok. Coba ubah pencarian atau filter.'}</p>
			</div>
		{:else}
			<table class="review-table">
				<thead>
					<tr>
						<th>ID & Karyawan</th>
						<th>Diajukan</th>
						<th>Nominal</th>
						<th>Skor Anomali</th>
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
							<td class="amount"><ClaimAmount claim={item.claim} /></td>
							<td>
								{#if item.decision?.anomaly_score != null || getAnomalySignal(item)}
									<AnomalyBadge score={item.decision?.anomaly_score} signal={getAnomalySignal(item)} size="sm" />
								{:else}
									<span class="text-muted" style="font-size: 12px; color: var(--color-text-muted);">-</span>
								{/if}
							</td>
							<td>
								<span class="badge {item.decision?.outcome === 'rejected' ? 'danger' : 'warning'}">{primaryReason(item)}</span>
								<p class="ai-reason">{item.decision?.explanation ?? 'Agent meneruskan klaim ini ke reviewer manusia.'}</p>
								<button class="btn-inspect" onclick={() => (activeSignals = item)}>
									<Icon name="eye" size={18} />Lihat bukti pemeriksaan
								</button>
							</td>
							<td>
								<StatusBadge status={item.claim.status} size="sm" />
								<div class="review-state">
									{item.review.status === 'open' ? 'Menunggu review' : `Review selesai${item.review.reviewer_reference ? ` · ${item.review.reviewer_reference}` : ''}`}
								</div>
							</td>
							<td>
								<a class="btn-inspect" href={`/reviews/${encodeURIComponent(item.claim.id)}`}><Icon name="review" size={18} />Buka detail reviewer</a>
								{#if item.review.status === 'open'}
									<div class="action-buttons">
										<button class="btn-approve" onclick={() => openDecisionModal(item, 'approve')}><Icon name="check" size={18} />Setujui</button>
										<button class="btn-reject" onclick={() => openDecisionModal(item, 'reject')}><Icon name="close" size={18} />Tolak</button>
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
		<div class="modal-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Bukti dan log AI klaim" use:modalFocus={{ onclose: () => (activeSignals = null) }}>
			<div class="modal-header">
				<div>
					<span class="eyebrow">Audit Trail & Bukti Signal</span>
					<h3>Klaim {shortClaimRef(activeSignals.claim.id)} · {activeSignals.claim.employee_id}</h3>
				</div>
				<button class="btn-close" aria-label="Tutup bukti pemeriksaan" onclick={() => (activeSignals = null)}><Icon name="close" /></button>
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
							<div class="receipt-row"><span>Nominal</span><ClaimAmount claim={activeSignals.claim} /></div>
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
					<h4>Keputusan Tera</h4>
					<p class="ai-reason">{activeSignals.decision?.explanation ?? 'Belum ada keputusan backend.'}</p>
					{#if activeSignals.decision}
						<div class="reason-chips">
							{#each describeReasonCodes(activeSignals.decision.reason_codes) as reason (reason.label)}
								<span class="tag">{reason.label}</span>
							{/each}
						</div>
					{/if}

					<h4 style="margin-top: 1.1rem;">Temuan duplikat dan anomali</h4>
					{#if activeSignals.signals.length === 0}
						<p class="ai-reason">Tidak ada signal dari backend untuk klaim ini.</p>
					{:else}
						<div class="timeline">
							{#each activeSignals.signals as signal (signal.id)}
								<div class="timeline-item">
									<div class="timeline-badge {signal.severity === 'blocking' ? 'WARN' : 'PASS'}">
										<Icon name={signal.signal_type === 'duplicate' ? 'receipt' : 'alert'} size={18} />
									</div>
									<div class="timeline-content">
										<strong>{signal.signal_type === 'duplicate' ? 'Duplikat' : 'Anomali'} · {severityLabel(signal.severity)}</strong>
										{#if signal.signal_type === 'anomaly'}
											<div style="margin: 6px 0;">
												<AnomalyBadge score={signal.score} {signal} size="sm" />
											</div>
										{/if}
										<p>{signal.explanation}</p>
										{#if signal.score != null}<p class="signal-meta">Skor model: {formatConfidence(signal.score)}</p>{/if}
										{#if signal.detector_version}
											<p class="signal-meta">Versi detektor: <code>{signal.detector_version}</code></p>
										{/if}
										{#if signal.evidence && typeof signal.evidence === 'object'}
											{@const ev = signal.evidence as Record<string, unknown>}
											{#if ev.features && typeof ev.features === 'object'}
												<details class="evidence-features" style="margin-top: 6px; font-size: 12px;">
													<summary style="cursor: pointer; color: var(--color-primary-dark); font-weight: 600;">Detail fitur ML ({Object.keys(ev.features).length} variabel)</summary>
													<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 6px; padding: 6px; background: var(--color-light); border-radius: 4px; margin-top: 4px;">
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
								<Icon name="check" size={18} />Setujui klaim ini
							</button>
							<button class="btn-reject full" onclick={() => openDecisionModal(activeSignals!, 'reject')}>
								<Icon name="close" size={18} />Tolak klaim
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
		<div class="modal-dialog decision-dialog" role="dialog" aria-modal="true" tabindex="-1" aria-label="Konfirmasi keputusan review" use:modalFocus={{ onclose: closeDecisionModal }}>
			<div class="modal-header">
				<div>
					<span class="eyebrow">Konfirmasi Keputusan</span>
					<h3>{decisionAction === 'approve' ? 'Setujui' : 'Tolak'} klaim {shortClaimRef(decisionTarget.claim.id)}</h3>
				</div>
				<button class="btn-close" aria-label="Tutup konfirmasi keputusan" onclick={closeDecisionModal}><Icon name="close" /></button>
			</div>
			<div class="decision-modal-body">
				<p class="ai-reason">
					Keputusan ini akan dicatat sebagai keputusan resmi atas nama
					<strong>{page.data.admin?.username}</strong> dan tidak dapat diubah dari UI.
				</p>
				<label class="reason-label" for="decision-reason">Alasan keputusan (wajib)</label>
				{#if decisionAction === 'approve'}
					<label for="decision-amount">Nominal final ({decisionTarget.claim.currency}) sesuai bukti</label>
					<input id="decision-amount" inputmode="decimal" bind:value={finalAmount} disabled={submittingDecision} placeholder="Contoh: 75000" />
					<p class="ai-reason">Wajib diisi tanpa pemisah ribuan. Koreksi nominal harus dijelaskan pada alasan keputusan.</p>
				{/if}
				<textarea
					id="decision-reason"
					required
					aria-required="true"
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
						disabled={submittingDecision || !decisionReason.trim() || (decisionAction === 'approve' && !(Number(finalAmount) > 0))}
					>
						{submittingDecision ? 'Mengirim...' : decisionAction === 'approve' ? 'Konfirmasi persetujuan' : 'Konfirmasi penolakan'}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.stat-label { display: flex; align-items: center; gap: var(--space-3); }
	.stat-symbol, .empty-symbol { display: inline-flex; align-items: center; justify-content: center; background: var(--color-light); color: var(--color-primary-dark); padding: var(--space-3); border-radius: var(--radius-md); }
	.stat-symbol.warning { background: var(--color-warning-soft); color: var(--color-warning); }
	.stat-symbol.waiting { background: var(--color-info-soft); color: var(--color-info); }
	.empty-symbol { margin-bottom: var(--space-5); }
	.empty-state h3 { color: var(--color-ink); font-size: var(--text-lg); }
	.empty-state p { max-width: 440px; margin-inline: auto; }
	.search-box:focus-within { outline: 3px solid var(--color-focus); outline-offset: 3px; }
	.search-box input:focus-visible { outline: none; }
	@media (max-width: 768px) { .stat-label { flex-direction: column; align-items: flex-start; } .header-actions, .header-actions button { width: 100%; } }

	.review-context {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
		padding: 0.75rem 1.1rem;
		background: #f7faf6;
		border: 1px solid #dce4da;
		border-radius: 8px;
		font-size: 0.88rem;
		color: #556356;
		margin-bottom: 1.5rem;
	}

	.review-context strong {
		color: #172018;
	}

	.review-context a {
		color: #1e5a22;
		font-weight: 600;
		text-decoration: underline;
		margin-left: auto;
	}

	main {
		max-width: 1440px;
		margin: 0 auto;
		padding: 0;
		box-sizing: border-box;
	}

	.header {
		padding: clamp(20px, 3vw, 32px);
		background: var(--color-light);
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		gap: var(--space-5);
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
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
