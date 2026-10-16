<script lang="ts">
	import { onMount } from 'svelte';
	import Toast from '$lib/components/Toast.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { listClaims, CURRENT_EMPLOYEE_ID } from '$lib/api/claims';
	import { ApiError } from '$lib/api/client';
	import { showToast } from '$lib/stores/toast.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDate } from '$lib/formatters/date';
	import { formatCurrency } from '$lib/formatters/currency';
	import { downloadReport } from '$lib/api/reports';
	import type { Claim } from '$lib/types/claim';

	let claims = $state<Claim[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	async function load() {
		loading = true;
		loadError = null;
		try {
			const response = await listClaims(CURRENT_EMPLOYEE_ID);
			claims = [...response.items].sort(
				(a, b) => new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime()
			);
		} catch (error) {
			loadError = error instanceof ApiError ? error.message : 'Terjadi kesalahan tak terduga.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	const approved = $derived(claims.filter((c) => c.status === 'approved'));
	const rejected = $derived(claims.filter((c) => c.status === 'rejected'));
	const waiting = $derived(
		claims.filter((c) => c.status !== 'approved' && c.status !== 'rejected')
	);
	const approvedTotal = $derived(
		approved.reduce((sum, c) => sum + (Number(c.declared_amount) || 0), 0)
	);

	async function exportToCSV() {
		if (loading || claims.length === 0) {
			showToast('Tidak ada data untuk diekspor.', 'error');
			return;
		}
		try {
			const blob = await downloadReport({ employeeId: CURRENT_EMPLOYEE_ID });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `riwayat-klaim-${new Date().toISOString().slice(0, 10)}.csv`;
			link.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
			showToast('File riwayat klaim berhasil diunduh.', 'success');
		} catch (error) {
			showToast(error instanceof Error ? error.message : 'Export gagal.', 'error');
		}
	}
</script>

<svelte:head>
	<title>Riwayat | Tera Expense Agent</title>
	<meta name="description" content="Lihat riwayat pengajuan klaim nota kamu di Tera." />
</svelte:head>

<section class="riwayat-page">
	<Toast />
	<div class="page-header">
		<div>
			<h1>Riwayat klaim</h1>
			<p>Nota yang sudah diajukan, lengkap dengan status dan tindak lanjutnya.</p>
		</div>
		<div class="header-actions">
			<button class="export-btn" id="btn-export-csv" onclick={exportToCSV}>
				<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
					<polyline points="17 8 12 3 7 8"/>
					<line x1="12" y1="3" x2="12" y2="15"/>
				</svg>
				Unduh CSV
			</button>
		</div>
	</div>

	{#if loading}
		<div class="state-panel" role="status">
			<span class="spin" aria-hidden="true">⟳</span> Memuat riwayat klaim...
		</div>
	{:else if loadError}
		<div class="state-panel error" role="alert">
			<h3>Gagal memuat riwayat</h3>
			<p>{loadError}</p>
			<button type="button" class="primary-btn" onclick={load}>Coba lagi</button>
		</div>
	{:else if claims.length === 0}
		<div class="empty-state">
			<div class="empty-icon">
				<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
					<line x1="9" y1="9" x2="15" y2="15"/>
					<line x1="15" y1="9" x2="9" y2="15"/>
				</svg>
			</div>
			<h3>Belum ada riwayat klaim</h3>
			<p>Nota pertamamu akan memulai riwayat ini. Kirim foto atau PDF nota untuk mengajukan pengeluaran kerja.</p>
			<a href="/pengajuan" class="primary-btn">Ajukan klaim</a>
		</div>
	{:else}
		<div class="summary-grid">
			<div class="summary-card">
				<span class="summary-icon approved" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
				</span>
				<div>
					<strong>{approved.length}</strong>
					<span>Disetujui</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon pending" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
				</span>
				<div>
					<strong>{waiting.length}</strong>
					<span>Sedang proses / klarifikasi</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon rejected" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				</span>
				<div>
					<strong>{rejected.length}</strong>
					<span>Ditolak</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon total-icon" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
				</span>
				<div>
					<strong>{formatCurrency(approvedTotal)}</strong>
					<span>Total disetujui</span>
				</div>
			</div>
		</div>

		<div class="table-card">
			<div class="table-header">
				<span class="table-title">Semua Klaim</span>
				<span class="table-count">{claims.length} klaim</span>
			</div>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>ID Klaim</th>
							<th>Diajukan</th>
							<th>Nominal</th>
							<th>Status</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						{#each claims as claim (claim.id)}
							<tr>
								<td class="claim-id-cell">{shortClaimRef(claim.id)}</td>
								<td>{formatDate(claim.submitted_at)}</td>
								<td>{formatCurrency(claim.declared_amount, claim.currency)}</td>
								<td><StatusBadge status={claim.status} size="sm" /></td>
								<td><a href="/riwayat/{claim.id}" class="detail-link">Lihat klaim</a></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</section>

<style>
	.riwayat-page {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		max-width: 960px;
	}

	.page-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 800;
		margin: 0 0 0.2rem;
		color: var(--color-text);
	}

	.page-header p {
		margin: 0;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}

	.export-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.6rem 1rem;
		background: rgba(255, 255, 255, 0.8);
		backdrop-filter: blur(10px);
		border: 1.5px solid var(--color-border);
		border-radius: var(--radius-sm);
		color: var(--color-primary);
		font: inherit;
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		transition: all var(--transition);
		white-space: nowrap;
	}

	.export-btn:hover {
		background: rgba(26, 107, 92, 0.07);
		border-color: var(--color-primary);
		transform: translateY(-1px);
	}

	.state-panel {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		gap: 0.4rem;
		padding: 4rem 2rem;
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		color: var(--color-text-muted);
		font-weight: 500;
	}

	.state-panel.error {
		border: 1px solid rgba(239, 68, 68, 0.25);
	}

	.state-panel h3 {
		margin: 0;
		color: var(--color-text);
	}

	.state-panel p {
		margin: 0 0 0.75rem;
		max-width: 420px;
		line-height: 1.5;
	}

	.spin {
		display: inline-block;
		animation: spinAnim 0.8s linear infinite;
		font-size: 1.2rem;
		color: var(--color-primary);
	}

	@keyframes spinAnim {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	/* Summary Cards */
	.summary-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0.75rem;
	}

	.summary-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.1rem;
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: 0 2px 12px rgba(26, 107, 92, 0.06);
	}

	.summary-card strong {
		display: block;
		font-size: 1.3rem;
		font-weight: 800;
		color: var(--color-text);
		line-height: 1;
		margin-bottom: 0.1rem;
	}

	.summary-card span:not(.summary-icon) {
		font-size: 0.72rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}

	.summary-icon {
		width: 38px;
		height: 38px;
		border-radius: var(--radius-sm);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.summary-icon.approved { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
	.summary-icon.pending { background: rgba(245, 158, 11, 0.12); color: #d97706; }
	.summary-icon.rejected { background: rgba(239, 68, 68, 0.12); color: #dc2626; }
	.summary-icon.total-icon { background: rgba(26, 107, 92, 0.1); color: var(--color-primary); }

	/* Table Card */
	.table-card {
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: 0 2px 16px rgba(26, 107, 92, 0.07);
		overflow: hidden;
	}

	.table-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid var(--color-border);
	}

	.table-title { font-weight: 700; font-size: 0.9rem; color: var(--color-text); }

	.table-count {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		background: rgba(26, 107, 92, 0.07);
		padding: 0.2rem 0.6rem;
		border-radius: 20px;
		font-weight: 600;
	}

	.table-wrap { overflow-x: auto; }

	table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }

	thead tr { background: rgba(26, 107, 92, 0.04); }

	th {
		padding: 0.75rem 1rem;
		text-align: left;
		font-weight: 600;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	td {
		padding: 0.85rem 1rem;
		color: var(--color-text);
		border-top: 1px solid rgba(26, 107, 92, 0.06);
	}

	tbody tr { transition: background var(--transition); }
	tbody tr:hover { background: rgba(26, 107, 92, 0.03); }

	.claim-id-cell {
		font-family: monospace;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		font-weight: 600;
	}

	/* Detail link */
	.detail-link {
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--color-primary);
		text-decoration: none;
		padding: 0.3rem 0.65rem;
		border-radius: var(--radius-sm);
		transition: all var(--transition);
		white-space: nowrap;
	}

	.detail-link:hover {
		background: rgba(26, 107, 92, 0.08);
	}

	@media (max-width: 680px) {
		.summary-grid { grid-template-columns: repeat(2, 1fr); }
		.page-header { flex-direction: column; }
		th, td { padding: 0.6rem 0.75rem; }
		.table-wrap { overflow-x: auto; }
		.table-wrap table { min-width: 620px; }
		.export-btn { width: 100%; justify-content: center; }
	}

	/* ─── Empty State ─── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 4rem 2rem;
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		border: 1px dashed var(--color-border);
		border-radius: var(--radius-lg);
		margin-top: 1rem;
	}

	.empty-icon {
		width: 72px;
		height: 72px;
		background: rgba(26, 107, 92, 0.08);
		color: var(--color-primary);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1.25rem;
	}

	.empty-state h3 {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0 0 0.5rem;
	}

	.empty-state p {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		max-width: 400px;
		margin: 0 0 1.5rem;
		line-height: 1.5;
	}

	.primary-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		background: var(--color-primary);
		color: white;
		font: inherit;
		font-size: 0.85rem;
		font-weight: 600;
		text-decoration: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition);
	}

	.primary-btn:hover {
		background: var(--color-primary-light);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(26, 107, 92, 0.2);
	}
</style>
