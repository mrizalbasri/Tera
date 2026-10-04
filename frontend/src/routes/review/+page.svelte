<script lang="ts">
	type OcrItem = { desc: string; price: number };
	type AuditEntry = { step: string; status: string; desc: string };
	type ReviewClaim = {
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
		aiAuditTrail: AuditEntry[];
	};

	// Data antrean klaim (berdasarkan BRD)
	let claims = $state<ReviewClaim[]>([
		{
			id: 'CLM-1042',
			name: 'Budi Santoso',
			role: 'Sales Lapangan Surabaya',
			category: 'Hotel / Penginapan',
			date: '28 Sep 2026',
			amount: 650000,
			vendor: 'Hotel Ibis Budget Surabaya',
			reasonBadge: 'Nominal > Rp 500.000',
			reasonType: 'warning',
			aiReason: 'Nota valid (skor 94%), namun melebihi ambang batas auto-approve (Rp500.000).',
			status: 'PENDING',
			confidence: 94,
			ocrItems: [
				{ desc: 'Room Standard 1 Malam', price: 590909 },
				{ desc: 'PB1 / Pajak Daerah 10%', price: 59091 }
			],
			aiAuditTrail: [
				{ step: 'Kualitas Gambar', status: 'PASS', desc: 'Resolusi 1920x1080, tidak buram, teks terbaca jelas.' },
				{ step: 'Ekstraksi OCR (FR-02)', status: 'PASS', desc: 'Berhasil membaca vendor, tanggal, rincian item, dan total.' },
				{ step: 'Pengecekan Kebijakan (RAG)', status: 'PASS', desc: 'Batas hotel Rp600.000/malam. Tanggal klaim dalam 14 hari.' },
				{ step: 'Deteksi Anomali & Duplikat (ML)', status: 'PASS', desc: 'Bukan klaim ganda, pola historis wajar.' },
				{ step: 'Keputusan Otonom (FR-08/10)', status: 'FLAGGED', desc: 'Dieskalasi ke admin manusia karena total (Rp650rb) > batas otonom (Rp500rb).' }
			]
		},
		{
			id: 'CLM-1045',
			name: 'Andi Wijaya',
			role: 'Sales Lapangan Bandung',
			category: 'BBM / SPBU',
			date: '01 Okt 2026',
			amount: 180000,
			vendor: 'SPBU Pertamina 34-40112',
			reasonBadge: 'Terdeteksi Anomali',
			reasonType: 'danger',
			aiReason: 'Nominal BBM melebihi batas kebijakan harian maksimal Rp150.000/hari kerja.',
			status: 'PENDING',
			confidence: 89,
			ocrItems: [
				{ desc: 'Pertamax 13.95 Liter @ Rp12.900', price: 180000 }
			],
			aiAuditTrail: [
				{ step: 'Kualitas Gambar', status: 'PASS', desc: 'Foto struk SPBU terbaca.' },
				{ step: 'Ekstraksi OCR (FR-02)', status: 'PASS', desc: 'Nominal Rp180.000 terverifikasi.' },
				{ step: 'Pengecekan Kebijakan (RAG)', status: 'WARN', desc: 'Batas maksimal BBM per hari adalah Rp150.000. Selisih: Rp30.000.' },
				{ step: 'Deteksi Anomali & Duplikat (ML)', status: 'WARN', desc: 'Karyawan mengajukan klaim BBM 2x dalam jarak 18 jam.' },
				{ step: 'Keputusan Otonom (FR-08/10)', status: 'FLAGGED', desc: 'Dieskalasi ke manusia karena melanggar aturan limit anggaran.' }
			]
		},
		{
			id: 'CLM-1049',
			name: 'Siti Rahma',
			role: 'Sales Lapangan Semarang',
			category: 'Makan Dinas',
			date: '02 Okt 2026',
			amount: 85000,
			vendor: 'RM Padang Sederhana',
			reasonBadge: 'Kepercayaan Rendah (72%)',
			reasonType: 'info',
			aiReason: 'Foto sedikit buram, rincian item minuman/pajak perlu verifikasi mata admin.',
			status: 'PENDING',
			confidence: 72,
			ocrItems: [
				{ desc: 'Nasi Rendang Komplit x1', price: 42000 },
				{ desc: 'Ayam Gulai x1 (tidak jelas)', price: 28000 },
				{ desc: 'Es Jeruk x1', price: 15000 }
			],
			aiAuditTrail: [
				{ step: 'Kualitas Gambar', status: 'WARN', desc: 'Kamera goyang, bagian tengah nota agak buram.' },
				{ step: 'Ekstraksi OCR (FR-02)', status: 'WARN', desc: 'Skor keyakinan 72% (di bawah batas minimal 80%).' },
				{ step: 'Pengecekan Kebijakan (RAG)', status: 'PASS', desc: 'Maks Rp75.000/orang. Nota untuk 1 orang (melebihi Rp10.000).' },
				{ step: 'Deteksi Anomali & Duplikat (ML)', status: 'PASS', desc: 'Tidak ada indikasi nota ganda.' },
				{ step: 'Keputusan Otonom (FR-08/10)', status: 'FLAGGED', desc: 'Dieskalasi untuk konfirmasi mata manusia sebelum disetujui.' }
			]
		}
	]);

	let autoApprovedCount = $state(24);
	let searchQuery = $state('');
	let selectedCategory = $state('ALL');
	let activeModalClaim = $state<ReviewClaim | null>(null);
	let toastMessage = $state('');

	// Hitung angka statistik secara live
	let pendingClaims = $derived(claims.filter(c => c.status === 'PENDING'));
	let pendingCount = $derived(pendingClaims.length);
	let filteredClaims = $derived(
		claims.filter(c => {
			const matchSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
			                    c.id.toLowerCase().includes(searchQuery.toLowerCase());
			const matchCategory = selectedCategory === 'ALL' || c.category === selectedCategory;
			return matchSearch && matchCategory;
		})
	);

	function showToast(msg: string) {
		toastMessage = msg;
		setTimeout(() => {
			toastMessage = '';
		}, 3500);
	}

	function approveClaim(id: string) {
		const claim = claims.find(c => c.id === id);
		if (claim) {
			claim.status = 'APPROVED';
			autoApprovedCount += 1;
			showToast(`✅ Berhasil! Klaim ${claim.id} atas nama ${claim.name} telah DISETUJUI.`);
			if (activeModalClaim?.id === id) activeModalClaim = null;
		}
	}

	function rejectClaim(id: string) {
		const claim = claims.find(c => c.id === id);
		if (claim) {
			const reason = prompt('Masukkan alasan penolakan klaim (opsional):', 'Tidak sesuai kebijakan perusahaan');
			if (reason !== null) {
				claim.status = 'REJECTED';
				showToast(`❌ Klaim ${claim.id} telah DITOLAK. Alasan dicatat.`);
				if (activeModalClaim?.id === id) activeModalClaim = null;
			}
		}
	}

	function formatRupiah(num: number) {
		return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(num);
	}

	function exportToCSV() {
		const headers = ['ID Klaim', 'Nama Karyawan', 'Kategori', 'Tanggal', 'Vendor', 'Nominal (IDR)', 'Status', 'Alasan AI'];
		const rows = claims.map(c => [
			c.id,
			`"${c.name}"`,
			`"${c.category}"`,
			c.date,
			`"${c.vendor}"`,
			c.amount,
			c.status,
			`"${c.aiReason}"`
		]);

		const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
		const encodedUri = encodeURI(csvContent);
		const link = document.createElement('a');
		link.setAttribute('href', encodedUri);
		link.setAttribute('download', `laporan-klaim-expense-agent-${new Date().toISOString().slice(0, 10)}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		showToast('📥 Laporan CSV berhasil diunduh ke komputermu!');
	}
</script>

<svelte:head>
	<title>Review & Eskalasi Klaim | Expense Agent</title>
</svelte:head>

{#if toastMessage}
	<div class="toast-notification">
		{toastMessage}
	</div>
{/if}

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
			<span class="stat-hint">{pendingCount > 0 ? 'Menunggu keputusan admin' : 'Semua antrean selesai! 🎉'}</span>
		</div>
		<div class="stat-card">
			<span class="stat-label">Auto-Approved Hari Ini</span>
			<span class="stat-value">{autoApprovedCount}</span>
			<span class="stat-hint">{Math.round((autoApprovedCount / (autoApprovedCount + claims.length)) * 100)}% tanpa intervensi manual</span>
		</div>
		<div class="stat-card">
			<span class="stat-label">Estimasi Waktu Dihemat</span>
			<span class="stat-value">{(autoApprovedCount * 5 / 60).toFixed(1)} Jam</span>
			<span class="stat-hint">Target efisiensi: 5 menit per klaim</span>
		</div>
	</section>

	<!-- Filter & Search Bar -->
	<div class="toolbar">
		<div class="search-box">
			🔍 <input type="text" placeholder="Cari ID klaim atau nama salesman..." bind:value={searchQuery} />
		</div>
		<div class="filter-group">
			<span>Kategori:</span>
			<select bind:value={selectedCategory}>
				<option value="ALL">Semua Kategori</option>
				<option value="Hotel / Penginapan">Hotel / Penginapan</option>
				<option value="BBM / SPBU">BBM / SPBU</option>
				<option value="Makan Dinas">Makan Dinas</option>
			</select>
		</div>
	</div>

	<!-- Tabel Antrean Review -->
	<section class="table-container">
		<div class="table-header">
			<h2>Daftar Antrean Klaim (Eskalasi)</h2>
			<span class="badge-count">{pendingCount} Klaim Perlu Tindakan</span>
		</div>

		{#if filteredClaims.length === 0}
			<div class="empty-state">
				<p>Tidak ada klaim yang cocok dengan pencarian.</p>
			</div>
		{:else}
			<table class="review-table">
				<thead>
					<tr>
						<th>ID & Karyawan</th>
						<th>Kategori & Vendor</th>
						<th>Tanggal Nota</th>
						<th>Nominal</th>
						<th>Alasan Eskalasi AI</th>
						<th>Status</th>
						<th>Aksi</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredClaims as claim}
						<tr class:resolved={claim.status !== 'PENDING'}>
							<td>
								<strong>#{claim.id}</strong>
								<div class="user-sub">{claim.name}</div>
								<div class="role-sub">{claim.role}</div>
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
								<button class="btn-inspect" onclick={() => activeModalClaim = claim}>
									🔍 Lihat Bukti & Log AI
								</button>
							</td>
							<td>
								{#if claim.status === 'PENDING'}
									<span class="status-pill pending">⏳ Menunggu</span>
								{:else if claim.status === 'APPROVED'}
									<span class="status-pill approved">✅ Disetujui</span>
								{:else}
									<span class="status-pill rejected">❌ Ditolak</span>
								{/if}
							</td>
							<td>
								{#if claim.status === 'PENDING'}
									<div class="action-buttons">
										<button class="btn-approve" onclick={() => approveClaim(claim.id)}>Setujui</button>
										<button class="btn-reject" onclick={() => rejectClaim(claim.id)}>Tolak</button>
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

<!-- Modal Pop-up Bukti Nota & Audit Trail AI (FR-12) -->
{#if activeModalClaim}
	<div class="modal-backdrop" onclick={() => activeModalClaim = null} role="presentation">
		<div class="modal-dialog" onclick={e => e.stopPropagation()} role="dialog" aria-modal="true">
			<div class="modal-header">
				<div>
					<span class="eyebrow">Audit Trail & Bukti Nota</span>
					<h3>Detail Klaim #{activeModalClaim.id} - {activeModalClaim.name}</h3>
				</div>
				<button class="btn-close" onclick={() => activeModalClaim = null}>✕</button>
			</div>

			<div class="modal-body">
				<!-- Kolom Kiri: Simulasi Struk Fisik -->
				<div class="receipt-mockup">
					<div class="receipt-paper">
						<div class="receipt-header">
							<h4>{activeModalClaim.vendor}</h4>
							<p>Tanggal: {activeModalClaim.date}</p>
							<p class="receipt-dash">--------------------------------</p>
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
						<div class="receipt-total">
							<strong>TOTAL:</strong>
							<strong>{formatRupiah(activeModalClaim.amount)}</strong>
						</div>
						<div class="ocr-watermark">
							<span>✓ Terverifikasi Vision OCR ({activeModalClaim.confidence}%)</span>
						</div>
					</div>
				</div>

				<!-- Kolom Kanan: Langkah Kerja AI (Audit Trail FR-12) -->
				<div class="audit-log">
					<h4>Jejak Logika Agent (FR-12)</h4>
					<div class="timeline">
						{#each activeModalClaim.aiAuditTrail as log, idx}
							<div class="timeline-item">
								<div class="timeline-badge {log.status}">
									{log.status === 'PASS' ? '✓' : log.status === 'WARN' ? '!' : '⚠'}
								</div>
								<div class="timeline-content">
									<strong>Langkah {idx + 1}: {log.step}</strong>
									<p>{log.desc}</p>
								</div>
							</div>
						{/each}
					</div>

					<div class="modal-actions-bar">
						{#if activeModalClaim.status === 'PENDING'}
							{@const claimId = activeModalClaim.id}
							<button class="btn-approve full" onclick={() => approveClaim(claimId)}>
								✓ Setujui Klaim Ini
							</button>
							<button class="btn-reject full" onclick={() => rejectClaim(claimId)}>
								✕ Tolak Klaim
							</button>
						{:else}
							<p class="status-summary">Klaim ini sudah berstatus: <strong>{activeModalClaim.status}</strong></p>
						{/if}
					</div>
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

	.filter-group {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		color: #4b584c;
		font-weight: 600;
	}

	.filter-group select {
		padding: 0.5rem 0.8rem;
		border: 1px solid #dce4da;
		border-radius: 8px;
		background: white;
		font-size: 0.9rem;
		outline: none;
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

	.role-sub {
		font-size: 0.78rem;
		color: #7b887c;
	}

	.vendor-sub {
		font-size: 0.8rem;
		color: #637064;
		margin-top: 0.25rem;
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
	.badge.info { background: #e0f2fe; color: #075985; }

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

	.status-pill {
		display: inline-block;
		font-size: 0.8rem;
		font-weight: 600;
		padding: 0.25rem 0.6rem;
		border-radius: 999px;
	}
	.status-pill.pending { background: #fef9c3; color: #854d0e; }
	.status-pill.approved { background: #dcfce7; color: #166534; }
	.status-pill.rejected { background: #fee2e2; color: #991b1b; }

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

	/* Toast */
	.toast-notification {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		background: #172018;
		color: #ffffff;
		padding: 0.85rem 1.4rem;
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.9rem;
		box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2);
		z-index: 1000;
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
	.timeline-badge.FLAGGED { background: #fee2e2; color: #991b1b; }

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
</style>