<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	let id = $derived(page.params.id);

	// Mock data for the detail page based on the ID
	let claimData = $state<any>(null);
	let loading = $state(true);

	onMount(() => {
		// Simulate fetching data
		setTimeout(() => {
			claimData = {
				id: `CLM-${id}`,
				date: '28 Sep 2026',
				vendor: 'SPBU Pertamina Margonda',
				amount: 'Rp 120.000',
				category: 'BBM',
				status: 'approved',
				fileName: 'nota_bensin.jpg',
				imageUrl: 'https://placehold.co/400x600/e0f2ee/1a6b5c?text=Nota+BBM',
				agentSteps: [
					{ label: 'Membaca nota (OCR)', detail: 'Ekstrak: Vendor (SPBU Pertamina Margonda), Tanggal (28 Sep 2026), Total (Rp 120.000), Item (Pertamax 8.5L).', status: 'done', icon: '🔍' },
					{ label: 'Validasi data', detail: 'Format nota valid. Total sesuai dengan perkalian harga item.', status: 'done', icon: '✔️' },
					{ label: 'Cek kebijakan', detail: 'Kategori BBM harian maks Rp150.000. Klaim valid (Rp120.000 ≤ Rp150.000).', status: 'done', icon: '📋' },
					{ label: 'Deteksi duplikat', detail: 'Tidak ditemukan klaim serupa di bulan ini.', status: 'done', icon: '🔄' },
					{ label: 'Keputusan akhir', detail: 'Klaim memenuhi syarat auto-approve.', status: 'done', icon: '⚖️' }
				]
			};
			
			// Override for rejected example if ID matches our mock rejected claim
			if (id === '20006') {
				claimData = {
					...claimData,
					vendor: 'Parkir Mall Depok',
					amount: 'Rp 22.000',
					category: 'Tol/Parkir',
					status: 'rejected',
					imageUrl: 'https://placehold.co/400x600/fef2f2/dc2626?text=Karcis+Parkir',
					agentSteps: [
						{ label: 'Membaca nota (OCR)', detail: 'Ekstrak: Vendor (Parkir Mall Depok), Tanggal (20 Sep 2026), Total (Rp 22.000).', status: 'done', icon: '🔍' },
						{ label: 'Validasi data', detail: 'Format tiket valid.', status: 'done', icon: '✔️' },
						{ label: 'Cek kebijakan', detail: 'Kategori Tol/Parkir valid.', status: 'done', icon: '📋' },
						{ label: 'Deteksi duplikat', detail: 'Ditemukan klaim identik (CLM-19044) diajukan pada 21 Sep 2026.', status: 'rejected', icon: '🔄' },
						{ label: 'Keputusan akhir', detail: 'Klaim ditolak karena terdeteksi sebagai duplikat (Fraud Prevention).', status: 'done', icon: '⚖️' }
					]
				};
			}

			loading = false;
		}, 600);
	});
</script>

<svelte:head>
	<title>Detail Klaim CLM-{id} | Tera Expense Agent</title>
</svelte:head>

<section class="detail-page">
	<div class="page-header">
		<div class="back-link">
			<a href="/riwayat">
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<line x1="19" y1="12" x2="5" y2="12"/>
					<polyline points="12 19 5 12 12 5"/>
				</svg>
				Kembali ke Riwayat
			</a>
		</div>
		<div>
			<h1>Detail Klaim CLM-{id}</h1>
		</div>
	</div>

	{#if loading}
		<div class="loading-state">
			<span class="spin">⟳</span> Memuat detail...
		</div>
	{:else if claimData}
		<div class="detail-grid">
			<!-- Kiri: Foto Nota -->
			<div class="receipt-panel glass-panel">
				<h3>Foto Nota</h3>
				<div class="receipt-image">
					<img src={claimData.imageUrl} alt="Foto Nota {claimData.id}" />
				</div>
				<div class="file-info">
					<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
					{claimData.fileName}
				</div>
			</div>

			<!-- Kanan: Info & Log Agent -->
			<div class="info-panel">
				<!-- Ringkasan Info -->
				<div class="glass-panel summary-info">
					<div class="info-row">
						<span class="info-label">Status</span>
						<span class="status-pill {claimData.status}">
							{#if claimData.status === 'approved'}✓ Disetujui
							{:else if claimData.status === 'rejected'}✕ Ditolak
							{:else}⏳ Menunggu{/if}
						</span>
					</div>
					<div class="info-row">
						<span class="info-label">Tanggal</span>
						<span class="info-val">{claimData.date}</span>
					</div>
					<div class="info-row">
						<span class="info-label">Kategori</span>
						<span class="cat-tag {claimData.category === 'BBM' ? 'bbm' : claimData.category === 'Makan' ? 'makan' : 'tol'}">{claimData.category}</span>
					</div>
					<div class="info-row">
						<span class="info-label">Vendor</span>
						<span class="info-val">{claimData.vendor}</span>
					</div>
					<div class="info-row total-row">
						<span class="info-label">Total</span>
						<span class="info-val amount">{claimData.amount}</span>
					</div>
				</div>

				<!-- Log Agent -->
				<div class="glass-panel agent-log">
					<div class="log-header">
						<div class="agent-avatar-mini">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<rect x="3" y="11" width="18" height="10" rx="2"/>
								<circle cx="12" cy="5" r="2"/>
								<path d="M12 7v4"/>
								<circle cx="8.5" cy="15" r="1.5"/>
								<circle cx="15.5" cy="15" r="1.5"/>
							</svg>
						</div>
						<h3>Log Keputusan AI Agent</h3>
					</div>
					
					<div class="steps-list">
						{#each claimData.agentSteps as step}
							<div class="step-item {step.status}">
								<div class="step-icon-wrap">
									{#if step.status === 'done'}
										<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
									{:else if step.status === 'rejected'}
										<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
									{:else}
										<span class="step-emoji">{step.icon}</span>
									{/if}
								</div>
								<div class="step-text">
									<span class="step-label">{step.label}</span>
									<span class="step-detail">{step.detail}</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}
</section>

<style>
	.detail-page {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		max-width: 960px;
	}

	.page-header {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.back-link a {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-primary);
		text-decoration: none;
		transition: opacity var(--transition);
	}
	.back-link a:hover { opacity: 0.7; }

	h1 {
		font-size: 1.5rem;
		font-weight: 800;
		margin: 0;
		color: var(--color-text);
	}

	.loading-state {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 2rem;
		color: var(--color-text-muted);
		font-weight: 500;
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

	.detail-grid {
		display: grid;
		grid-template-columns: 1fr 1.3fr;
		gap: 1.25rem;
		align-items: start;
	}

	.glass-panel {
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: 0 2px 16px rgba(26, 107, 92, 0.07);
		padding: 1.5rem;
	}

	.glass-panel h3 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		color: var(--color-text);
	}

	/* Kiri: Foto Nota */
	.receipt-panel {
		display: flex;
		flex-direction: column;
	}

	.receipt-image {
		width: 100%;
		border-radius: var(--radius-sm);
		overflow: hidden;
		border: 1px solid var(--color-border);
		background: rgba(26, 107, 92, 0.03);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.75rem;
	}

	.receipt-image img {
		width: 100%;
		height: auto;
		display: block;
	}

	.file-info {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	/* Kanan: Info */
	.info-panel {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.summary-info {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 0.75rem;
		border-bottom: 1px dashed rgba(26, 107, 92, 0.15);
	}
	.info-row:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.info-label {
		font-size: 0.8rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}

	.info-val {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.total-row {
		padding-top: 0.25rem;
	}
	.amount {
		font-size: 1.1rem;
		color: var(--color-primary);
		font-weight: 800;
	}

	/* Agent Log */
	.log-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1.25rem;
	}
	.log-header h3 { margin: 0; }

	.agent-avatar-mini {
		width: 28px;
		height: 28px;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.3);
	}

	.steps-list {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.step-item {
		display: flex;
		align-items: flex-start;
		gap: 0.85rem;
		padding: 0.6rem 0;
		position: relative;
	}

	/* Vertical connector line */
	.step-item:not(:last-child)::after {
		content: '';
		position: absolute;
		left: 13px;
		top: 36px;
		width: 2px;
		height: calc(100% - 10px);
		background: var(--color-primary);
		opacity: 0.2;
	}
	
	.step-item.rejected:not(:last-child)::after {
		background: #dc2626;
	}

	.step-icon-wrap {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.8rem;
		flex-shrink: 0;
		background: var(--color-primary);
		color: white;
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.2);
		position: relative;
		z-index: 1;
	}

	.step-item.rejected .step-icon-wrap {
		background: #dc2626;
		box-shadow: 0 2px 8px rgba(220, 38, 38, 0.2);
	}

	.step-text {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding-top: 0.2rem;
	}

	.step-label {
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--color-text);
	}
	
	.step-item.rejected .step-label {
		color: #b91c1c;
	}

	.step-detail {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		line-height: 1.5;
	}

	/* Badges & Tags */
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

	.status-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.7rem;
		border-radius: 20px;
		font-size: 0.75rem;
		font-weight: 600;
	}
	.status-pill.approved { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
	.status-pill.pending { background: rgba(245, 158, 11, 0.12); color: #b45309; }
	.status-pill.rejected { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

	@media (max-width: 768px) {
		.detail-grid { grid-template-columns: 1fr; }
	}
</style>
