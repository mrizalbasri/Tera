<script lang="ts">
	import { decideReview } from '$lib/api/reviews';

	interface OcrItem {
		desc: string;
		price: number;
	}

	interface AuditStep {
		step: string;
		status: string;
		desc: string;
	}

	interface Claim {
		id: string;
		name: string;
		role: string;
		category: string;
		date: string;
		amount: number;
		vendor: string;
		reasonBadge: string;
		reasonType: string;
		aiReason: string;
		status: string;
		confidence: number;
		ocrItems: OcrItem[];
		aiAuditTrail: AuditStep[];
	}

	let claims = $state<Claim[]>([
		{
			id: 'CLM-1042',
			name: 'Budi Santoso',
			role: 'Sales Lapangan Surabaya',
			category: 'Hotel / Stay',
			date: '28 Sep 2026',
			amount: 650000,
			vendor: 'Hotel Ibis Budget Surabaya',
			reasonBadge: 'Nominal > Rp 500k',
			reasonType: 'warning',
			aiReason:
				'Nota valid (skor 94%), namun melebihi batas reimbursement tanpa persetujuan awal manager ($500.000).',
			status: 'PENDING',
			confidence: 94,
			ocrItems: [
				{ desc: 'Room Standard 1 Malam', price: 590909 },
				{ desc: 'PB1 / Pajak Daerah 10%', price: 59091 }
			],
			aiAuditTrail: [
				{ step: 'Kualitas Gambar', status: 'PASS', desc: 'Resolusi tinggi, keterbacaan 98%' },
				{ step: 'Ekstraksi Teks (OCR)', status: 'PASS', desc: 'Tanggal, Vendor, & Total cocok' },
				{ step: 'Cek Duplikasi', status: 'PASS', desc: 'Tidak ada invoice ganda' },
				{
					step: 'Kepatuhan Kebijakan',
					status: 'FLAG',
					desc: 'Aturan #4: Klaim menginap di atas Rp 500k perlu verifikasi manual'
				}
			]
		},
		{
			id: 'CLM-1045',
			name: 'Siti Rahma',
			role: 'Software Engineer',
			category: 'Software / SaaS',
			date: '01 Okt 2026',
			amount: 320000,
			vendor: 'ChatGPT Plus Subscription',
			reasonBadge: 'Kategori SaaS Baru',
			reasonType: 'info',
			aiReason:
				'Langganan AI bulanan untuk keperluan riset coding. Nota dalam mata uang USD ($20).',
			status: 'PENDING',
			confidence: 98,
			ocrItems: [{ desc: 'ChatGPT Plus Monthly Subscription', price: 320000 }],
			aiAuditTrail: [
				{ step: 'Kualitas Gambar', status: 'PASS', desc: 'E-receipt PDF resmi' },
				{ step: 'Konversi Kurs', status: 'PASS', desc: 'USD 20.00 -> IDR 320.000 (Kurs Relevan)' },
				{
					step: 'Kepatuhan Kebijakan',
					status: 'PASS',
					desc: 'SaaS Produktivitas disetujui untuk Tim Dev'
				}
			]
		}
	]);

	let toastMessage = $state<string | null>(null);
	let activeModalClaim = $state<Claim | null>(null);

	function showToast(msg: string) {
		toastMessage = msg;
		setTimeout(() => {
			toastMessage = null;
		}, 3000);
	}

	async function approveClaim(id: string) {
		try {
			await decideReview({
				claimId: id,
				action: 'approve',
				reason: 'Disetujui dari Review Portal'
			});

			const claim = claims.find((c) => c.id === id);

			if (claim) {
				claim.status = 'APPROVED';

				showToast(
					`✅ Berhasil! Klaim ${claim.id} atas nama ${claim.name} telah DISETUJUI.`
				);

				if (activeModalClaim?.id === id) {
					activeModalClaim = null;
				}
			}
		} catch (err) {
			console.error('Gagal menyetujui klaim:', err);
			showToast('❌ Gagal menyetujui klaim. Silakan coba lagi.');
		}
	}

	async function rejectClaim(id: string) {
		try {
			await decideReview({
				claimId: id,
				action: 'reject',
				reason: 'Ditolak dari Review Portal'
			});

			const claim = claims.find((c) => c.id === id);

			if (claim) {
				claim.status = 'REJECTED';

				showToast(`❌ Klaim ${claim.id} telah DITOLAK.`);

				if (activeModalClaim?.id === id) {
					activeModalClaim = null;
				}
			}
		} catch (err) {
			console.error('Gagal menolak klaim:', err);
			showToast('❌ Gagal menolak klaim. Silakan coba lagi.');
		}
	}

	function formatRupiah(num: number) {
		return new Intl.NumberFormat('id-ID', {
			style: 'currency',
			currency: 'IDR',
			maximumFractionDigits: 0
		}).format(num);
	}
</script>

<svelte:head>
	<title>Review Portal - Expense Agent</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
	<link
		href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="page-container">
	{#if toastMessage}
		<div class="toast">{toastMessage}</div>
	{/if}

	<header class="page-header">
		<div>
			<h1>Portal Verifikasi Klaim</h1>
			<p>Tinjau klaim reimbursement yang membutuhkan keputusan verifikator manusia (HITL).</p>
		</div>
	</header>

	<section class="table-card">
		<table class="claims-table">
			<thead>
				<tr>
					<th>ID Klaim</th>
					<th>Karyawan</th>
					<th>Kategori & Vendor</th>
					<th>Tanggal</th>
					<th>Nominal</th>
					<th>Catatan AI / Risiko</th>
					<th>Aksi</th>
				</tr>
			</thead>
			<tbody>
				{#each claims as claim}
					<tr>
						<td><span class="claim-id">{claim.id}</span></td>
						<td>
							<div class="user-name">{claim.name}</div>
							<div class="user-sub">{claim.role}</div>
						</td>
						<td>
							<span class="tag">{claim.category}</span>
							<div class="vendor-sub">{claim.vendor}</div>
						</td>
						<td>{claim.date}</td>
						<td class="amount">{formatRupiah(claim.amount)}</td>
						<td>
							<span class="badge {claim.reasonType}">{claim.reasonBadge}</span>
							<p class="ai-reason">{claim.aiReason}</p>
							<button class="btn-inspect" onclick={() => (activeModalClaim = claim)}>
								🔍 Cek Bukti Struk & Jejak AI
							</button>
						</td>
						<td>
							{#if claim.status === 'PENDING'}
								<div class="action-buttons">
									<button class="btn-approve" onclick={() => approveClaim(claim.id)}>
										Setujui
									</button>
									<button class="btn-reject" onclick={() => rejectClaim(claim.id)}>
										Tolak
									</button>
								</div>
							{:else}
								<span class="status-pill {claim.status.toLowerCase()}">{claim.status}</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	{#if activeModalClaim}
		<div class="modal-backdrop" onclick={() => (activeModalClaim = null)} role="presentation">
			<div class="modal-content" onclick={(e) => e.stopPropagation()} role="presentation">
				<button class="modal-close" onclick={() => (activeModalClaim = null)}>✕</button>

				<div class="modal-header">
					<span class="modal-eyebrow">Bukti Struk & Audit Trail</span>
					<h3>Detail Klaim #{activeModalClaim.id} - {activeModalClaim.name}</h3>
				</div>

				<div class="modal-body">
					<div class="receipt-preview">
						<div class="receipt-header">
							<h4>{activeModalClaim.vendor}</h4>
							<p>Tanggal: {activeModalClaim.date}</p>
							<div class="receipt-dash">--------------------------------</div>
						</div>

						<div class="receipt-items">
							{#each activeModalClaim.ocrItems as item}
								<div class="receipt-row">
									<span>{item.desc}</span>
									<span>{formatRupiah(item.price)}</span>
								</div>
							{/each}
						</div>

						<div class="receipt-dash">--------------------------------</div>

						<div class="receipt-row total">
							<strong>TOTAL:</strong>
							<strong>{formatRupiah(activeModalClaim.amount)}</strong>
						</div>

						<div class="ocr-badge">
							✓ Vision OCR Confidence: {activeModalClaim.confidence}%
						</div>
					</div>

					<div class="audit-trail">
						<h4>Analisis Otomatis AI</h4>

						<div class="timeline">
							{#each activeModalClaim.aiAuditTrail as log, idx}
								<div class="timeline-step">
									<div class="step-icon {log.status.toLowerCase()}">{idx + 1}</div>

									<div class="step-details">
										<strong>
											{log.step} -
											<span class="step-status">{log.status}</span>
										</strong>
										<p>{log.desc}</p>
									</div>
								</div>
							{/each}
						</div>
					</div>
				</div>

				<div class="modal-footer-actions">
					{#if activeModalClaim.status === 'PENDING'}
						<button
							class="btn-approve full"
							onclick={() => activeModalClaim && approveClaim(activeModalClaim.id)}
						>
							✓ Setujui Klaim Ini
						</button>

						<button
							class="btn-reject full"
							onclick={() => activeModalClaim && rejectClaim(activeModalClaim.id)}
						>
							✕ Tolak Klaim
						</button>
					{:else}
						<p class="status-summary">
							Status Klaim: <strong>{activeModalClaim.status}</strong>
						</p>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.page-container {
		font-family: 'Plus Jakarta Sans', sans-serif;
		padding: 2rem;
		background-color: #f8fafc;
		min-height: 100vh;
	}

	.page-header h1 {
		font-size: 1.8rem;
		font-weight: 800;
		color: #0f172a;
		margin: 0;
	}

	.page-header p {
		color: #64748b;
		margin-top: 0.25rem;
	}

	.table-card {
		margin-top: 2rem;
		background: white;
		border-radius: 12px;
		border: 1px solid #e2e8f0;
		overflow: hidden;
	}

	.claims-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
	}

	.claims-table th {
		background: #f1f5f9;
		padding: 1rem;
		font-size: 0.85rem;
		font-weight: 700;
		color: #475569;
		border-bottom: 1px solid #e2e8f0;
	}

	.claims-table td {
		padding: 1rem;
		border-bottom: 1px solid #e2e8f0;
		font-size: 0.9rem;
		vertical-align: top;
	}

	.claim-id {
		font-weight: 700;
		color: #2563eb;
	}

	.user-name {
		font-weight: 600;
		color: #0f172a;
	}

	.user-sub,
	.vendor-sub {
		font-size: 0.8rem;
		color: #64748b;
	}

	.tag {
		background: #e0f2fe;
		color: #0369a1;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.amount {
		font-weight: 700;
		color: #0f172a;
	}

	.badge {
		display: inline-block;
		padding: 0.2rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 700;
		margin-bottom: 0.4rem;
	}

	.badge.warning {
		background: #fef3c7;
		color: #b45309;
	}

	.badge.info {
		background: #e0e7ff;
		color: #4338ca;
	}

	.ai-reason {
		font-size: 0.82rem;
		color: #475569;
		margin: 0 0 0.5rem 0;
	}

	.btn-inspect {
		background: none;
		border: none;
		color: #2563eb;
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		padding: 0;
	}

	.action-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.btn-approve {
		background: #16a34a;
		color: white;
		border: none;
		padding: 0.4rem 0.8rem;
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
	}

	.btn-reject {
		background: #dc2626;
		color: white;
		border: none;
		padding: 0.4rem 0.8rem;
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
	}

	.status-pill {
		padding: 0.3rem 0.6rem;
		border-radius: 20px;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.status-pill.approved {
		background: #dcfce7;
		color: #15803d;
	}

	.status-pill.rejected {
		background: #fee2e2;
		color: #b91c1c;
	}

	.toast {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		background: #0f172a;
		color: white;
		padding: 0.8rem 1.2rem;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 1000;
	}

	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100vw;
		height: 100vh;
		background: rgba(15, 23, 42, 0.5);
		display: flex;
		justify-content: center;
		align-items: center;
		z-index: 999;
	}

	.modal-content {
		background: white;
		border-radius: 12px;
		width: 700px;
		max-width: 90%;
		padding: 1.5rem;
		position: relative;
	}

	.modal-close {
		position: absolute;
		top: 1rem;
		right: 1rem;
		background: none;
		border: none;
		font-size: 1.2rem;
		cursor: pointer;
	}

	.modal-body {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
		margin-top: 1rem;
	}

	.receipt-preview {
		background: #f8fafc;
		border: 1px dashed #cbd5e1;
		padding: 1rem;
		border-radius: 8px;
		font-family: monospace;
	}

	.receipt-row {
		display: flex;
		justify-content: space-between;
		font-size: 0.85rem;
		margin: 0.3rem 0;
	}

	.ocr-badge {
		margin-top: 1rem;
		background: #dcfce7;
		color: #166534;
		font-size: 0.75rem;
		padding: 0.4rem;
		border-radius: 4px;
		text-align: center;
		font-family: 'Plus Jakarta Sans', sans-serif;
		font-weight: 600;
	}

	.timeline-step {
		display: flex;
		gap: 0.8rem;
		margin-bottom: 0.8rem;
	}

	.step-icon {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: #e2e8f0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.step-icon.pass {
		background: #dcfce7;
		color: #15803d;
	}

	.step-icon.flag {
		background: #fef3c7;
		color: #b45309;
	}

	.step-details p {
		margin: 0;
		font-size: 0.8rem;
		color: #64748b;
	}

	.modal-footer-actions {
		margin-top: 1.5rem;
		display: flex;
		gap: 0.6rem;
		padding-top: 1.2rem;
		border-top: 1px solid #f1f5f9;
	}

	.btn-approve.full,
	.btn-reject.full {
		flex: 1;
		padding: 0.65rem;
		font-size: 0.85rem;
	}

	.status-summary {
		font-size: 0.9rem;
		color: #475569;
	}
</style>