<script lang="ts">
	// State to test empty history view
	let isEmpty = $state(false);
	
	// Toast Notification
	let toast = $state<{ message: string, type: 'error' | 'success', visible: boolean }>({ message: '', type: 'success', visible: false });

	function showToast(message: string, type: 'error' | 'success' = 'success') {
		toast = { message, type, visible: true };
		setTimeout(() => { toast.visible = false; }, 3500);
	}

	function exportToCSV() {
		if (isEmpty) {
			showToast('Tidak ada data untuk diekspor.', 'error');
			return;
		}
		// Dummy action
		showToast('File laporan_klaim.csv sedang diunduh...', 'success');
	}
</script>

<svelte:head>
	<title>Riwayat | Tera Expense Agent</title>
	<meta name="description" content="Lihat riwayat pengajuan klaim nota kamu di Tera." />
</svelte:head>

<section class="riwayat-page">
	<!-- Toast Notification -->
	{#if toast.visible}
		<div class="toast {toast.type}">
			{#if toast.type === 'error'}
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
			{:else}
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
			{/if}
			<span>{toast.message}</span>
		</div>
	{/if}
	<div class="page-header">
		<div>
			<h1>Riwayat Pengajuan</h1>
			<p>Semua nota yang sudah kamu upload dan status prosesnya.</p>
		</div>
		<div class="header-actions">
			<button class="export-btn" id="btn-export-csv" onclick={exportToCSV}>
				<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
					<polyline points="17 8 12 3 7 8"/>
					<line x1="12" y1="3" x2="12" y2="15"/>
				</svg>
				Export CSV
			</button>
		</div>
	</div>

	{#if isEmpty}
		<!-- Empty State -->
		<div class="empty-state">
			<div class="empty-icon">
				<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
					<line x1="9" y1="9" x2="15" y2="15"/>
					<line x1="15" y1="9" x2="9" y2="15"/>
				</svg>
			</div>
			<h3>Belum ada riwayat klaim</h3>
			<p>Kamu belum pernah mengajukan klaim reimbursement. Mulai upload nota di halaman Beranda.</p>
			<a href="/" class="primary-btn">Mulai Upload Nota</a>
		</div>
	{:else}
		<!-- Summary cards -->
		<div class="summary-grid">
			<div class="summary-card">
				<span class="summary-icon approved">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
				</span>
				<div>
					<strong>8</strong>
					<span>Disetujui</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon pending">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
				</span>
				<div>
					<strong>2</strong>
					<span>Menunggu</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon rejected">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
				</span>
				<div>
					<strong>1</strong>
					<span>Ditolak</span>
				</div>
			</div>
			<div class="summary-card">
				<span class="summary-icon total-icon">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
				</span>
				<div>
					<strong>Rp 1,4 jt</strong>
					<span>Total disetujui</span>
				</div>
			</div>
		</div>

		<!-- Table -->
		<div class="table-card">
			<div class="table-header">
				<span class="table-title">Semua Klaim</span>
				<span class="table-count">7 klaim</span>
			</div>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>ID Klaim</th>
							<th>Tanggal</th>
							<th>Kategori</th>
							<th>Vendor / Keterangan</th>
							<th>Nominal</th>
							<th>Status</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td class="claim-id-cell">CLM-28001</td>
							<td>28 Sep 2026</td>
							<td><span class="cat-tag bbm">BBM</span></td>
							<td>SPBU Pertamina Margonda</td>
							<td>Rp 120.000</td>
							<td><span class="status-pill approved">✓ Disetujui</span></td>
							<td><a href="/riwayat/28001" class="detail-link" id="link-detail-28001">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-27002</td>
							<td>27 Sep 2026</td>
							<td><span class="cat-tag makan">Makan</span></td>
							<td>RM Padang Sederhana</td>
							<td>Rp 65.000</td>
							<td><span class="status-pill approved">✓ Disetujui</span></td>
							<td><a href="/riwayat/27002" class="detail-link" id="link-detail-27002">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-25003</td>
							<td>25 Sep 2026</td>
							<td><span class="cat-tag tol">Tol/Parkir</span></td>
							<td>Tol Jagorawi</td>
							<td>Rp 22.000</td>
							<td><span class="status-pill approved">✓ Disetujui</span></td>
							<td><a href="/riwayat/25003" class="detail-link" id="link-detail-25003">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-24004</td>
							<td>24 Sep 2026</td>
							<td><span class="cat-tag makan">Makan</span></td>
							<td>Nota untuk 4 orang</td>
							<td>Rp 240.000</td>
							<td><span class="status-pill pending">⏳ Menunggu</span></td>
							<td><a href="/riwayat/24004" class="detail-link" id="link-detail-24004">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-22005</td>
							<td>22 Sep 2026</td>
							<td><span class="cat-tag bbm">BBM</span></td>
							<td>SPBU Shell Ciawi</td>
							<td>Rp 145.000</td>
							<td><span class="status-pill approved">✓ Disetujui</span></td>
							<td><a href="/riwayat/22005" class="detail-link" id="link-detail-22005">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-20006</td>
							<td>20 Sep 2026</td>
							<td><span class="cat-tag tol">Tol/Parkir</span></td>
							<td>Parkir Mall Depok</td>
							<td>Rp 22.000</td>
							<td><span class="status-pill rejected">✕ Duplikat</span></td>
							<td><a href="/riwayat/20006" class="detail-link" id="link-detail-20006">Lihat →</a></td>
						</tr>
						<tr>
							<td class="claim-id-cell">CLM-18007</td>
							<td>18 Sep 2026</td>
							<td><span class="cat-tag makan">Makan</span></td>
							<td>KFC Bogor Raya</td>
							<td>Rp 72.000</td>
							<td><span class="status-pill pending">⏳ Menunggu</span></td>
							<td><a href="/riwayat/18007" class="detail-link" id="link-detail-18007">Lihat →</a></td>
						</tr>
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

	/* Category Tags */
	.cat-tag {
		display: inline-block;
		padding: 0.2rem 0.55rem;
		border-radius: 20px;
		font-size: 0.7rem;
		font-weight: 600;
	}

	.cat-tag.bbm { background: rgba(59, 130, 246, 0.12); color: #1d4ed8; }
	.cat-tag.makan { background: rgba(245, 158, 11, 0.12); color: #b45309; }
	.cat-tag.tol { background: rgba(139, 92, 246, 0.12); color: #6d28d9; }

	/* Status Pills */
	.status-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.7rem;
		border-radius: 20px;
		font-size: 0.72rem;
		font-weight: 600;
		white-space: nowrap;
	}

	.status-pill.approved { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
	.status-pill.pending { background: rgba(245, 158, 11, 0.12); color: #b45309; }
	.status-pill.rejected { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

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
		font-size: 0.85rem;
		font-weight: 600;
		text-decoration: none;
		border-radius: var(--radius-sm);
		transition: all var(--transition);
	}

	.primary-btn:hover {
		background: var(--color-primary-light);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(26, 107, 92, 0.2);
	}

	/* ─── Toast ─── */
	.toast {
		position: fixed;
		top: 1.5rem;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		border-radius: var(--radius-sm);
		font-weight: 600;
		font-size: 0.85rem;
		z-index: 1000;
		box-shadow: 0 4px 16px rgba(0,0,0,0.08);
		animation: toastSlide 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}

	.toast.error { background: #fef2f2; border: 1px solid #f87171; color: #b91c1c; }
	.toast.success { background: #f0fdf4; border: 1px solid #4ade80; color: #15803d; }

	@keyframes toastSlide {
		from { top: -2rem; opacity: 0; }
		to { top: 1.5rem; opacity: 1; }
	}
</style>