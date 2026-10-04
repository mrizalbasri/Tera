<script>
	// Data antrean klaim interaktif
	let claims = $state([
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
			aiReason: 'Nota valid (skor 94%), namun melebihi batas auto-approve (Rp500.000).',
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
				{ step: 'Deteksi Anomali & Duplikat', status: 'PASS', desc: 'Bukan klaim ganda, pola historis wajar.' },
				{ step: 'Keputusan Otonom (FR-08/10)', status: 'FLAGGED', desc: 'Dieskalasi ke admin karena total melebihi batas otonom.' }
			]
		},
		{
			id: 'CLM-1045',
			name: 'Andi Wijaya',
			role: 'Sales Lapangan Bandung',
			category: 'BBM Pertamina',
			date: '01 Okt 2026',
			amount: 180000,
			vendor: 'SPBU Pertamina 34-40112',
			reasonBadge: 'Anomali Limit',
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
				{ step: 'Deteksi Anomali & Duplikat', status: 'WARN', desc: 'Karyawan mengajukan klaim BBM 2x dalam jarak 18 jam.' },
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
			reasonBadge: 'Low Confidence (72%)',
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
				{ step: 'Deteksi Anomali & Duplikat', status: 'PASS', desc: 'Tidak ada indikasi nota ganda.' },
				{ step: 'Keputusan Otonom (FR-08/10)', status: 'FLAGGED', desc: 'Dieskalasi untuk konfirmasi mata manusia sebelum disetujui.' }
			]
		}
	]);

	let autoApprovedCount = $state(289);
	let searchQuery = $state('');
	let selectedCategory = $state('ALL');
	let activeModalClaim = $state(null);
	let toastMessage = $state('');

	let pendingClaims = $derived(claims.filter(c => c.status === 'PENDING'));
	let pendingCount = $derived(pendingClaims.length);
	let filteredClaims = $derived(
		claims.filter(c => {
			const matchSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
			                    c.id.toLowerCase().includes(searchQuery.toLowerCase());
			const matchCategory = selectedCategory === 'ALL' || c.category.includes(selectedCategory);
			return matchSearch && matchCategory;
		})
	);

	function showToast(msg) {
		toastMessage = msg;
		setTimeout(() => { toastMessage = ''; }, 3500);
	}

	function approveClaim(id) {
		const claim = claims.find(c => c.id === id);
		if (claim) {
			claim.status = 'APPROVED';
			autoApprovedCount += 1;
			showToast(`✅ Berhasil! Klaim ${claim.id} atas nama ${claim.name} telah DISETUJUI.`);
			if (activeModalClaim?.id === id) activeModalClaim = null;
		}
	}

	function rejectClaim(id) {
		const claim = claims.find(c => c.id === id);
		if (claim) {
			const reason = prompt('Masukkan alasan penolakan klaim:', 'Melanggar batas nominal kebijakan');
			if (reason !== null) {
				claim.status = 'REJECTED';
				showToast(`❌ Klaim ${claim.id} telah DITOLAK.`);
				if (activeModalClaim?.id === id) activeModalClaim = null;
			}
		}
	}

	function formatRupiah(num) {
		return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(num);
	}

	function exportToCSV() {
		const headers = ['ID Klaim', 'Nama Salesman', 'Kategori', 'Tanggal', 'Vendor', 'Nominal', 'Status', 'Alasan'];
		const rows = claims.map(c => [c.id, `"${c.name}"`, `"${c.category}"`, c.date, `"${c.vendor}"`, c.amount, c.status, `"${c.aiReason}"`]);
		const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
		const encodedUri = encodeURI(csvContent);
		const link = document.createElement('a');
		link.setAttribute('href', encodedUri);
		link.setAttribute('download', `review-antrean-klaim-${new Date().toISOString().slice(0, 10)}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		showToast('📥 Data antrean berhasil diekspor ke CSV!');
	}
</script>

<svelte:head>
	<title>Expense Agent - Claim Escalation & Review</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
</svelte:head>

{#if toastMessage}
	<div class="toast-notification">
		{toastMessage}
	</div>
{/if}

<div class="review-wrapper">
	<!-- Top Nav -->
	<header class="top-nav">
		<div class="brand">
			<a href="/" class="brand-logo">
				<span class="logo-dot"></span>
				ExpenseAgent
			</a>
			<span class="page-title">/ Human Review Portal</span>
		</div>

		<div class="top-controls">
			<a href="/dashboard" class="btn-dashboard-link">
				📊 Buka Analytics Dashboard
			</a>
			<button class="btn-action" onclick={exportToCSV}>
				Export CSV
			</button>
		</div>
	</header>

	<!-- 3 Colorful Gradient Cards -->
	<section class="stat-cards-grid">
		<div class="gradient-card orange">
			<div class="card-top">
				<span class="card-icon">⚠️</span>
				<span class="card-title">Perlu Review Manual</span>
			</div>
			<div class="card-value">{pendingCount}</div>
			<div class="card-sub">{pendingCount > 0 ? 'Klaim menunggu verifikasi admin' : 'Semua antrean selesai! 🎉'}</div>
			<div class="card-wave"></div>
		</div>

		<div class="gradient-card purple">
			<div class="card-top">
				<span class="card-icon">⚡</span>
				<span class="card-title">Auto-Approved AI</span>
			</div>
			<div class="card-value">{autoApprovedCount}</div>
			<div class="card-sub">Diproses otonom tanpa sentuhan manual</div>
			<div class="card-wave"></div>
		</div>

		<div class="gradient-card blue">
			<div class="card-top">
				<span class="card-icon">⏱️</span>
				<span class="card-title">Waktu Kerja Dihemat</span>
			</div>
			<div class="card-value">{(autoApprovedCount * 5 / 60).toFixed(0)} Jam</div>
			<div class="card-sub">Berdasarkan rata-rata 5 menit per nota</div>
			<div class="card-wave"></div>
		</div>
	</section>

	<!-- Main Card Panel: Table & Filters -->
	<section class="card-panel">
		<!-- Toolbar / Search & Filter -->
		<div class="toolbar">
			<div class="search-pill">
				<span class="icon">🔍</span>
				<input type="text" placeholder="Search by ID or salesman name..." bind:value={searchQuery} />
			</div>

			<div class="filter-group">
				<span class="filter-label">Kategori:</span>
				<select bind:value={selectedCategory} class="filter-select">
					<option value="ALL">Semua Kategori</option>
					<option value="Hotel">Hotel / Penginapan</option>
					<option value="BBM">BBM / SPBU</option>
					<option value="Makan">Makan Dinas</option>
				</select>
			</div>
		</div>

		<!-- Table -->
		<div class="table-responsive">
			<table class="modern-table">
				<thead>
					<tr>
						<th>ID & Salesman</th>
						<th>Kategori & Merchant</th>
						<th>Tanggal Nota</th>
						<th>Nominal</th>
						<th>Alasan AI Eskalasi</th>
						<th>Status</th>
						<th>Aksi Admin</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredClaims as claim}
						<tr class:resolved={claim.status !== 'PENDING'}>
							<td>
								<div class="user-block">
									<span class="id-tag">#{claim.id}</span>
									<strong>{claim.name}</strong>
									<span class="role-text">{claim.role}</span>
								</div>
							</td>
							<td>
								<div class="merchant-block">
									<span class="cat-pill">{claim.category}</span>
									<span class="vendor-text">{claim.vendor}</span>
								</div>
							</td>
							<td class="date-col">{claim.date}</td>
							<td class="amount">{formatRupiah(claim.amount)}</td>
							<td class="reason-cell">
								<span class="reason-badge {claim.reasonType}">{claim.reasonBadge}</span>
								<p class="reason-desc">{claim.aiReason}</p>
								<button class="btn-inspect" onclick={() => activeModalClaim = claim}>
									🔍 Cek Bukti Struk & Jejak AI
								</button>
							</td>
							<td>
								{#if claim.status === 'PENDING'}
									<span class="status-pill warning">⏳ Review</span>
								{:else if claim.status === 'APPROVED'}
									<span class="status-pill success">✅ Approved</span>
								{:else}
									<span class="status-pill danger">❌ Rejected</span>
								{/if}
							</td>
							<td>
								{#if claim.status === 'PENDING'}
									<div class="action-btn-group">
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
		</div>
	</section>
</div>

<!-- Modal Pop-up Bukti Nota & Log AI (FR-12) -->
{#if activeModalClaim}
	<div class="modal-backdrop" onclick={() => activeModalClaim = null} role="presentation">
		<div class="modal-dialog" onclick={e => e.stopPropagation()} role="dialog" aria-modal="true">
			<div class="modal-header">
				<div>
					<span class="modal-eyebrow">Bukti Struk & Audit Trail</span>
					<h3>Detail Klaim #{activeModalClaim.id} - {activeModalClaim.name}</h3>
				</div>
				<button class="btn-close" onclick={() => activeModalClaim = null}>✕</button>
			</div>

			<div class="modal-body">
				<!-- Struk Fisik -->
				<div class="receipt-container">
					<div class="receipt-paper">
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
						<div class="receipt-total">
							<strong>TOTAL:</strong>
							<strong>{formatRupiah(activeModalClaim.amount)}</strong>
						</div>
						<div class="ocr-badge">
							✓ Vision OCR Confidence: {activeModalClaim.confidence}%
						</div>
					</div>
				</div>

				<!-- Jejak AI -->
				<div class="audit-flow">
					<h4>Alur Logika AI (FR-12)</h4>
					<div class="timeline">
						{#each activeModalClaim.aiAuditTrail as log, idx}
							<div class="timeline-step">
								<div class="step-indicator {log.status}">
									{log.status === 'PASS' ? '✓' : '!'}
								</div>
								<div class="step-details">
									<strong>Tahap {idx + 1}: {log.step}</strong>
									<p>{log.desc}</p>
								</div>
							</div>
						{/each}
					</div>

					<div class="modal-footer-actions">
						{#if activeModalClaim.status === 'PENDING'}
							<button class="btn-approve full" onclick={() => approveClaim(activeModalClaim.id)}>
								✓ Setujui Klaim Ini
							</button>
							<button class="btn-reject full" onclick={() => rejectClaim(activeModalClaim.id)}>
								✕ Tolak Klaim
							</button>
						{:else}
							<p class="status-summary">Status Klaim: <strong>{activeModalClaim.status}</strong></p>
						{/if}
					</div>
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

	/* Top Nav */
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

	.btn-dashboard-link:hover {
		background: #f8fafc;
		border-color: #cbd5e1;
	}

	.btn-action {
		background: #7c3aed;
		color: white;
		border: none;
		border-radius: 999px;
		padding: 0.6rem 1.25rem;
		font-weight: 700;
		font-size: 0.85rem;
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
		transition: all 0.2s;
	}

	.btn-action:hover {
		background: #6d28d9;
		transform: translateY(-1px);
	}

	/* 3 Gradient Stat Cards */
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
		transition: transform 0.2s ease;
	}

	.gradient-card:hover {
		transform: translateY(-3px);
	}

	.gradient-card.orange { background: linear-gradient(135deg, #ea580c, #f59e0b); }
	.gradient-card.purple { background: linear-gradient(135deg, #7c3aed, #a855f7); }
	.gradient-card.blue { background: linear-gradient(135deg, #2563eb, #38bdf8); }

	.card-top {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.card-icon { font-size: 1.1rem; }

	.card-title {
		font-size: 0.82rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		opacity: 0.9;
	}

	.card-value {
		font-size: 2.3rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		line-height: 1.1;
		margin-bottom: 0.35rem;
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

	/* Card Panel */
	.card-panel {
		background: #ffffff;
		border-radius: 20px;
		padding: 1.8rem;
		box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
		border: 1px solid #f1f5f9;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.search-pill {
		background: #f8fafc;
		border-radius: 999px;
		padding: 0.55rem 1.1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid #e2e8f0;
		flex: 1;
		max-width: 380px;
	}

	.search-pill input {
		border: none;
		outline: none;
		background: transparent;
		font-family: inherit;
		font-size: 0.85rem;
		width: 100%;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.filter-label {
		font-size: 0.82rem;
		font-weight: 700;
		color: #64748b;
	}

	.filter-select {
		padding: 0.5rem 0.9rem;
		border: 1px solid #e2e8f0;
		border-radius: 999px;
		background: #f8fafc;
		font-size: 0.85rem;
		font-family: inherit;
		outline: none;
		font-weight: 600;
		color: #334155;
	}

	/* Table */
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

	tr.resolved {
		background: #fafcff;
		opacity: 0.7;
	}

	.user-block strong {
		display: block;
		font-size: 0.92rem;
		color: #0f172a;
		margin-top: 0.2rem;
	}

	.id-tag {
		background: #f1f5f9;
		color: #475569;
		font-weight: 700;
		font-size: 0.75rem;
		padding: 0.2rem 0.45rem;
		border-radius: 6px;
	}

	.role-text {
		font-size: 0.78rem;
		color: #94a3b8;
	}

	.merchant-block {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.cat-pill {
		display: inline-block;
		width: fit-content;
		background: #f5f3ff;
		color: #7c3aed;
		font-size: 0.78rem;
		font-weight: 700;
		padding: 0.2rem 0.6rem;
		border-radius: 999px;
	}

	.vendor-text {
		font-size: 0.82rem;
		color: #64748b;
	}

	.date-col {
		color: #64748b;
		font-weight: 500;
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
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.2rem 0.55rem;
		border-radius: 6px;
		margin-bottom: 0.35rem;
	}

	.reason-badge.warning { background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; }
	.reason-badge.danger { background: #fef2f2; color: #b91c1c; border: 1px solid #fee2e2; }
	.reason-badge.info { background: #f0fdf4; color: #15803d; border: 1px solid #dcfce7; }

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
		transition: all 0.15s;
	}

	.btn-inspect:hover {
		background: #f1f5f9;
		color: #0f172a;
		border-color: #94a3b8;
	}

	.status-pill {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
	}

	.status-pill.warning { background: #fff7ed; color: #c2410c; }
	.status-pill.success { background: #dcfce7; color: #15803d; }
	.status-pill.danger { background: #fef2f2; color: #b91c1c; }

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
		transition: background 0.15s;
	}

	.btn-approve:hover { background: #059669; }

	.btn-reject {
		background: white;
		color: #ef4444;
		border: 1px solid #fecaca;
		border-radius: 8px;
		padding: 0.45rem 0.85rem;
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn-reject:hover { background: #fef2f2; }

	.text-done {
		color: #94a3b8;
		font-size: 0.82rem;
		font-weight: 600;
	}

	/* Toast Notification */
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
		box-shadow: 0 10px 25px -5px rgba(0,0,0,0.25);
		z-index: 1000;
	}

	/* Modal Dialog */
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
		box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
		max-height: 90vh;
		display: flex;
		flex-direction: column;
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
		letter-spacing: 0.05em;
	}

	.modal-header h3 {
		margin: 0.2rem 0 0;
		font-size: 1.3rem;
		color: #0f172a;
	}

	.btn-close {
		background: #f1f5f9;
		border: none;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		font-size: 1.1rem;
		cursor: pointer;
		color: #64748b;
	}

	.modal-body {
		padding: 1.8rem;
		display: grid;
		grid-template-columns: 1fr 1.3fr;
		gap: 1.6rem;
		overflow-y: auto;
	}

	/* Receipt Mockup */
	.receipt-container {
		background: #f8fafc;
		padding: 1rem;
		border-radius: 14px;
	}

	.receipt-paper {
		background: white;
		padding: 1.2rem;
		border-radius: 8px;
		box-shadow: 0 4px 10px rgba(0,0,0,0.03);
		font-family: monospace;
		font-size: 0.85rem;
		color: #334155;
	}

	.receipt-header h4 {
		margin: 0 0 0.3rem;
		font-size: 0.95rem;
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

	.ocr-badge {
		margin-top: 1.2rem;
		background: #f5f3ff;
		color: #7c3aed;
		padding: 0.45rem;
		border-radius: 6px;
		text-align: center;
		font-size: 0.75rem;
		font-weight: 700;
	}

	/* Audit Flow */
	.audit-flow h4 {
		margin: 0 0 1rem;
		color: #0f172a;
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
		font-weight: bold;
	.step-indicator.PASS { background: #dcfce7; color: #15803d; }
	.step-indicator.WARN { background: #fef3c7; color: #b45309; }

	.step-details strong {
		font-size: 0.85rem;
		color: #1e293b;
	}

	.step-details p {
		margin: 0.2rem 0 0;
		font-size: 0.8rem;
		color: #64748b;
		line-height: 1.35;
	}

	.modal-footer-actions {
		margin-top: 1.5rem;
		display: flex;
		gap: 0.6rem;
		padding-top: 1.2rem;
		border-top: 1px solid #f1f5f9;
	}

	.btn-approve.full, .btn-reject.full {
		flex: 1;
		padding: 0.65rem;
		font-size: 0.85rem;
	}

	.status-summary {
		font-size: 0.9rem;
		color: #64748b;
		margin: 0;
	}
</style>
