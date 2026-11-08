<script lang="ts">
	import TeraBrandRibbon from '$lib/components/TeraBrandRibbon.svelte';
	import { reveal } from '$lib/actions/reveal';

	// Navigation & state
	let mobileMenu = $state(false);
	let scrolled = $state(false);
	let activeTab = $state<'pengajuan' | 'riwayat' | 'review' | 'laporan'>('pengajuan');

	// --- 1. SIMULATOR PENGAJUAN (OCR AI) ---
	interface SampleReceipt {
		id: string;
		name: string;
		vendor: string;
		date: string;
		amount: number;
		category: string;
		tax: number;
		confidence: number;
		policyRule: string;
		status: 'approved' | 'escalated';
		statusLabel: string;
		explanation: string;
		items: Array<{ name: string; qty: number; price: number }>;
	}

	const samples: SampleReceipt[] = [
		{
			id: 'sample-1',
			name: 'Nota Makan Siang Tim',
			vendor: 'Restoran Padang Sederhana',
			date: '14 Okt 2026',
			amount: 420000,
			category: 'Makanan & Minuman',
			tax: 42000,
			confidence: 99.2,
			policyRule: 'Maks. Rp 500.000 per pertemuan tim',
			status: 'approved',
			statusLabel: 'Disetujui Otomatis',
			explanation: 'Nominal sesuai plafon jam kerja dan nota resmi terbaca lengkap tanpa indikasi duplikat.',
			items: [
				{ name: 'Paket Ayam Pop x4', qty: 4, price: 160000 },
				{ name: 'Rendang Daging x4', qty: 4, price: 180000 },
				{ name: 'Jus Alpukat & Es Jeruk', qty: 4, price: 80000 }
			]
		},
		{
			id: 'sample-2',
			name: 'Taksi Perjalanan Dinas',
			vendor: 'Bluebird Taxi Jakarta',
			date: '15 Okt 2026',
			amount: 145000,
			category: 'Transportasi',
			tax: 0,
			confidence: 98.7,
			policyRule: 'Transportasi lokal operasional kerja',
			status: 'approved',
			statusLabel: 'Disetujui Otomatis',
			explanation: 'Perjalanan terverifikasi pada rute kantor - bandara dalam jam penugasan kerja.',
			items: [
				{ name: 'Argo Taksi Bandara - SCBD', qty: 1, price: 130000 },
				{ name: 'Tarif Tol Lingkar Luar', qty: 1, price: 15000 }
			]
		},
		{
			id: 'sample-3',
			name: 'Beli Aksesoris Monitor',
			vendor: 'Sentra Komputer Glodok',
			date: '16 Okt 2026',
			amount: 2750000,
			category: 'Perlengkapan Kerja',
			tax: 275000,
			confidence: 97.4,
			policyRule: 'Plafon belanja mandiri maks. Rp 1.000.000',
			status: 'escalated',
			statusLabel: 'Diteruskan ke Reviewer Finance',
			explanation: 'Total pengeluaran melampaui batas belanja tanpa Purchase Order (PO). Perlu persetujuan tim Finance.',
			items: [
				{ name: 'Monitor Arm Heavy Duty Dual', qty: 1, price: 1450000 },
				{ name: 'Docking Station USB-C Pro', qty: 1, price: 1300000 }
			]
		}
	];

	let selectedReceipt = $state<SampleReceipt>(samples[0]);
	let isScanning = $state(false);

	function chooseSample(sample: SampleReceipt) {
		selectedReceipt = sample;
		isScanning = true;
		setTimeout(() => {
			isScanning = false;
		}, 400);
	}

	function formatRupiah(num: number): string {
		return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(num);
	}

	// --- 2. AUDIT TIMELINE (RIWAYAT) ---
	const timelineSteps = [
		{
			time: '14:20:01',
			title: 'Nota Diterima & Hash Dihitung',
			desc: 'File nota `nota_makan_siang.png` diunggah karyawan. SHA-256 dibuat untuk mencegah pengajuan ulang nota yang sama.',
			badge: 'Verifikasi Awal'
		},
		{
			time: '14:20:04',
			title: 'AI OCR & Ekstraksi Bidang',
			desc: 'Model Vision mengekstrak vendor, tanggal, daftar item, pajak, dan grand total dengan skor keyakinan 99.2%.',
			badge: 'Ekstraksi 99%'
		},
		{
			time: '14:20:06',
			title: 'Pemeriksaan Kebijakan Otomatis',
			desc: 'Pengeluaran dicocokkan dengan Kebijakan Versi 2026.2: plafon makan malam kerja terpenuhi.',
			badge: 'Kebijakan Sesuai'
		},
		{
			time: '14:20:08',
			title: 'Evaluasi Risiko & Sinyal Duplikat',
			desc: 'Pengecekan riwayat 90 hari: tidak ditemukan kesamaan atribut dengan nota karyawan lain (skor anomali 0.08 / Rendah).',
			badge: 'Bebas Duplikat'
		},
		{
			time: '14:20:10',
			title: 'Keputusan Final Ditetapkan',
			desc: 'Klaim disetujui otomatis tanpa perlu eskalasi manual. Notifikasi dikirimkan ke karyawan dan rekaman dicatat ke audit log.',
			badge: 'Disetujui'
		}
	];
	let activeTimelineIdx = $state(2);

	// --- 3. REVIEW WORKBENCH (FINANCE) ---
	let simulatedDecision = $state<'idle' | 'approved' | 'rejected'>('idle');
	let decisionNote = $state('');

	function handleSimulatedDecision(action: 'approved' | 'rejected') {
		simulatedDecision = action;
		decisionNote = action === 'approved' 
			? 'Klaim disetujui oleh Reviewer Finance. Catatan: Penggantian aksesoris telah dikonfirmasi ke manajer divisi.'
			: 'Klaim ditolak oleh Reviewer Finance. Alasan: Pengeluaran harus diajukan melalui sistem Procurement perusahaan.';
	}

	function resetDecision() {
		simulatedDecision = 'idle';
		decisionNote = '';
	}

	// --- 4. EXPORT & ANALITIK (LAPORAN) ---
	let reportPeriod = $state<'month' | 'quarter'>('month');

	function downloadSampleCSV() {
		const headers = 'ID Klaim,Tanggal,Karyawan,Divisi,Vendor,Kategori,Nominal (IDR),Status,Metode Verifikasi\n';
		const rows = [
			'CLM-2026-001,2026-10-14,Budi Santoso,Engineering,Restoran Padang Sederhana,Makanan & Minuman,420000,approved,Otomatis AI',
			'CLM-2026-002,2026-10-15,Siti Rahma,Sales,Bluebird Taxi Jakarta,Transportasi,145000,approved,Otomatis AI',
			'CLM-2026-003,2026-10-16,Ahmad Fauzi,Product,Sentra Komputer Glodok,Perlengkapan Kerja,2750000,escalated,Review Manual',
			'CLM-2026-004,2026-10-17,Dewi Lestari,Marketing,Kopi Kenangan Kantor,Makanan & Minuman,78000,approved,Otomatis AI',
			'CLM-2026-005,2026-10-18,Rian Pratama,Finance,Hotel Santika Surabaya,Akomodasi,850000,approved,Otomatis AI'
		].join('\n');

		const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.setAttribute('download', `tera-rekap-pengeluaran-sample-${reportPeriod}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}
</script>

<svelte:head>
	<title>Eksplorasi Produk · Tera AI Expense Agent</title>
	<meta name="description" content="Pelajari dan uji coba alur kerja AI Expense Agent Tera: dari pembacaan nota OCR cerdas, pelacakan riwayat transparan, review finance berbukti, hingga pelaporan otomatis." />
</svelte:head>

<svelte:window onscroll={() => { const next = window.scrollY > 16; if (next !== scrolled) scrolled = next; }} />

<div class="product-page">
	<!-- Navbar Sticky -->
	<div class="navbar-shell" class:scrolled>
		<header class="landing-header">
			<a class="wordmark" href="/" aria-label="Kembali ke beranda Tera">
				<img src="/logo.webp" alt="" width="36" height="36" />
				<span>Tera</span>
			</a>
			<nav class:expanded={mobileMenu} id="landing-nav" aria-label="Navigasi produk">
				<div class="nav-links">
					<a href="/produk" class="active-nav">Produk</a>
					<a href="/#fitur">Fitur</a>
					<a href="/#cara-kerja">Cara kerja</a>
					<a href="/#untuk-tim">Untuk tim</a>
					<a href="/#faq">FAQ</a>
				</div>
			</nav>
			<div class="nav-actions">
				<a class="button nav-cta" href="/pengajuan">Buka aplikasi <span aria-hidden="true">↗</span></a>
				<button 
					class="menu-toggle secondary" 
					class:opened={mobileMenu} 
					type="button" 
					aria-label={mobileMenu ? 'Tutup navigasi' : 'Buka navigasi'}
					onclick={() => (mobileMenu = !mobileMenu)}>
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
						<path d={mobileMenu ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
					</svg>
				</button>
			</div>
		</header>
	</div>

	<main id="main-content">
		<!-- Hero Section -->
		<section class="product-hero">
			<TeraBrandRibbon />
			<div class="hero-container">
				<div class="badge-pill">Eksplorasi Produk &amp; Fitur Interaktif</div>
				<h1>Satu sistem cerdas.<br /><span>Empat pilar pengeluaran kerja.</span></h1>
				<p>
					Tera bukan sekadar aplikasi pencatat nota. Tera adalah <em>AI Expense Agent</em> yang memvalidasi kebijakan perusahaan, mendeteksi indikasi anomali, dan menyederhanakan rekonsiliasi keuangan.
				</p>

				<!-- Subnav / Tab Anchor Switcher -->
				<div class="feature-pills" role="tablist" aria-label="Pilih fitur untuk dijelajahi">
					<a href="#pengajuan" class:chosen={activeTab === 'pengajuan'} onclick={() => (activeTab = 'pengajuan')}>
						<span class="pill-icon">↥</span>
						<span>Ajukan klaim</span>
					</a>
					<a href="#riwayat" class:chosen={activeTab === 'riwayat'} onclick={() => (activeTab = 'riwayat')}>
						<span class="pill-icon">≡</span>
						<span>Riwayat pengajuan</span>
					</a>
					<a href="#review" class:chosen={activeTab === 'review'} onclick={() => (activeTab = 'review')}>
						<span class="pill-icon">✓</span>
						<span>Review klaim</span>
					</a>
					<a href="#laporan" class:chosen={activeTab === 'laporan'} onclick={() => (activeTab = 'laporan')}>
						<span class="pill-icon">↗</span>
						<span>Laporan pengeluaran</span>
					</a>
				</div>
			</div>
		</section>

		<!-- 1. AJUKAN KLAIM SHOWCASE -->
		<section use:reveal id="pengajuan" class="feature-section scroll-reveal" aria-labelledby="pengajuan-title">
			<div class="section-badge">MODUL KARYAWAN · PENGAJUAN CERDAS</div>
			<div class="feature-grid">
				<div class="feature-copy">
					<h2 id="pengajuan-title">Unggah nota, biarkan AI membaca dan mencocokkan kebijakan.</h2>
					<p>
						Karyawan cukup mengambil foto nota lewat ponsel atau mengunggah PDF. Model Vision Tera membaca vendor, tanggal transaksi, item, dan total nominal, lalu mencocokkannya ke kebijakan pengeluaran dalam hitungan detik.
					</p>

					<div class="feature-bullets">
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Ekstraksi Multimodal Presisi</strong>
								<p>Mendukung nota restoran, tiket transportasi, struk bensin, hingga invoice vendor resmi.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Pencegahan Duplikat Sejak Awal</strong>
								<p>Sistem menghitung sidik jari digital (hash) nota untuk mencegah klaim ganda yang tidak disengaja.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Percakapan Klarifikasi Cerdas</strong>
								<p>Jika foto terpotong atau informasi kabur, agen langsung menanyakan klarifikasi pada ruang obrolan yang sama.</p>
							</div>
						</div>
					</div>

					<div class="feature-cta-row">
						<a class="button" href="/pengajuan">Coba di Aplikasi Langsung <span aria-hidden="true">→</span></a>
						<span class="cta-hint">Tersedia mode demo instan tanpa kartu kredit.</span>
					</div>
				</div>

				<!-- Simulator OCR Interaktif -->
				<div class="interactive-card">
					<div class="card-header">
						<span class="card-title">Simulator Pembacaan Nota AI</span>
						<span class="live-pill">Live Preview</span>
					</div>

					<div class="sample-picker-bar">
						<span class="picker-label">Pilih contoh nota:</span>
						<div class="sample-chips">
							{#each samples as sample}
								<button 
									type="button" 
									class="chip-button" 
									class:active={selectedReceipt.id === sample.id}
									onclick={() => chooseSample(sample)}>
									{sample.name}
								</button>
							{/each}
						</div>
					</div>

					<!-- Receipt Mockup Stage -->
					<div class="receipt-stage" class:scanning={isScanning}>
						<div class="receipt-paper">
							<div class="receipt-topline">
								<span class="receipt-logo">TERA · RECEIPT</span>
								<span class="receipt-hash">#REC-{selectedReceipt.id.toUpperCase()}</span>
							</div>

							<div class="receipt-vendor-block">
								<strong class="receipt-vendor">{selectedReceipt.vendor}</strong>
								<span class="receipt-date">{selectedReceipt.date}</span>
							</div>

							<div class="receipt-divider"></div>

							<div class="receipt-items-list">
								{#each selectedReceipt.items as item}
									<div class="receipt-item-row">
										<span>{item.name}</span>
										<span>{formatRupiah(item.price)}</span>
									</div>
								{/each}
							</div>

							<div class="receipt-divider"></div>

							<div class="receipt-total-row">
								<span>TOTAL PENGELUARAN</span>
								<strong class="receipt-total-val">{formatRupiah(selectedReceipt.amount)}</strong>
							</div>

							<!-- Floating Confidence Tag -->
							<div class="confidence-tag">
								<span>Akurasi Pembacaan:</span>
								<strong>{selectedReceipt.confidence}%</strong>
							</div>
						</div>

						<!-- OCR Result Inspector -->
						<div class="ocr-inspector">
							<div class="inspector-badge" class:badge-approved={selectedReceipt.status === 'approved'} class:badge-escalated={selectedReceipt.status === 'escalated'}>
								<span class="dot"></span>
								{selectedReceipt.statusLabel}
							</div>

							<div class="inspector-field">
								<small>Aturan Kebijakan Terkait</small>
								<span>{selectedReceipt.policyRule}</span>
							</div>

							<div class="inspector-field">
								<small>Kategori Terdeteksi</small>
								<span>{selectedReceipt.category}</span>
							</div>

							<div class="inspector-explanation">
								<small>Analisis AI Agent:</small>
								<p>{selectedReceipt.explanation}</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- 2. RIWAYAT PENGELUARAN SHOWCASE -->
		<section use:reveal id="riwayat" class="feature-section scroll-reveal" aria-labelledby="riwayat-title">
			<div class="section-badge">MODUL KARYAWAN · JEJAK &amp; KLARIFIKASI</div>
			<div class="feature-grid reverse">
				<!-- Interactive Timeline Card -->
				<div class="interactive-card">
					<div class="card-header">
						<span class="card-title">Jejak Transparansi Pemeriksaan (Audit Trail)</span>
						<span class="live-pill">Langkah Interaktif</span>
					</div>

					<div class="timeline-container">
						<div class="timeline-stepper">
							{#each timelineSteps as step, i}
								<button 
									type="button" 
									class="stepper-item" 
									class:selected={activeTimelineIdx === i}
									onclick={() => (activeTimelineIdx = i)}>
									<span class="stepper-dot">{i + 1}</span>
									<span class="stepper-meta">
										<small>{step.time}</small>
										<strong>{step.title}</strong>
									</span>
								</button>
							{/each}
						</div>

						<div class="timeline-detail-panel">
							<span class="panel-step-label">Detail Langkah {activeTimelineIdx + 1} dari 5</span>
							<h4>{timelineSteps[activeTimelineIdx].title}</h4>
							<span class="tag-pill">{timelineSteps[activeTimelineIdx].badge}</span>
							<p class="panel-desc">{timelineSteps[activeTimelineIdx].desc}</p>
							<div class="panel-security-note">
								<span>🔒</span>
								<small>Setiap rekaman dilengkapi jejak peristiwa yang tidak dapat diubah (immutable log).</small>
							</div>
						</div>
					</div>
				</div>

				<div class="feature-copy">
					<h2 id="riwayat-title">Pantau status pengajuan sampai jelas, tanpa perlu bertanya manual.</h2>
					<p>
						Hilangkan kebiasaan bertanya *"Klaim saya sudah sampai mana?"*. Tera mencatat setiap proses mulai dari pembacaan nota, pengecekan aturan, hingga keputusan final dalam satu lini masa yang terbuka.
					</p>

					<div class="feature-bullets">
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Status Real-Time &amp; Terang Benderang</strong>
								<p>Karyawan tahu persis apakah klaimnya disetujui otomatis, butuh klarifikasi, atau sedang ditinjau Finance.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Alasan Keputusan Tertulis</strong>
								<p>Jika ada klaim yang disesuaikan atau ditolak, alasan kebijakan ditampilkan secara gamblang dan objektif.</p>
							</div>
						</div>
					</div>

					<div class="feature-cta-row">
						<a class="button" href="/riwayat">Lihat Contoh Riwayat <span aria-hidden="true">→</span></a>
					</div>
				</div>
			</div>
		</section>

		<!-- 3. REVIEW KLAIM SHOWCASE -->
		<section use:reveal id="review" class="feature-section scroll-reveal" aria-labelledby="review-title">
			<div class="section-badge">MODUL FINANCE · REVIEW &amp; DETEKSI ANOMALI</div>
			<div class="feature-grid">
				<div class="feature-copy">
					<h2 id="review-title">Fokus hanya pada klaim yang membutuhkan pertimbangan manusia.</h2>
					<p>
						Pengeluaran wajar yang sesuai kebijakan disetujui secara otomatis. Tim finance hanya perlu membuka antrean review untuk memeriksa klaim dengan nilai tinggi, sinyal duplikat, atau indikasi anomali.
					</p>

					<div class="feature-bullets">
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Skor Anomali Pembelajaran Mesin</strong>
								<p>Algoritma Isolation Forest membandingkan pola pengeluaran dengan historis untuk menandai ketidakwajaran.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Deteksi Duplikasi Canggih</strong>
								<p>Mencocokkan nota identik maupun pengajuan berulang dengan tanggal dan nominal yang mirip.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Keputusan Berbasis Alasan Terstandar</strong>
								<p>Setiap persetujuan atau penolakan dicatat dengan kode alasan baku untuk memudahkan audit kepatuhan.</p>
							</div>
						</div>
					</div>

					<div class="feature-cta-row">
						<a class="button" href="/reviews">Buka Antrean Review <span aria-hidden="true">→</span></a>
					</div>
				</div>

				<!-- Simulator Reviewer Finance Interaktif -->
				<div class="interactive-card">
					<div class="card-header">
						<span class="card-title">Panel Reviewer Tim Finance</span>
						<span class="live-pill">Simulasi Tindak Lanjut</span>
					</div>

					<div class="review-workbench-demo">
						<div class="review-meta-header">
							<div>
								<span class="claim-id-tag">Klaim #CLM-2026-089</span>
								<h3>Pembelian Monitor &amp; Docking USB-C</h3>
								<small>Diajukan oleh: Ahmad Fauzi (Product) · Rp 2.750.000</small>
							</div>
							<div class="risk-meter">
								<span class="risk-label">Skor Anomali</span>
								<strong class="risk-value high">0.84 / Tinggi</strong>
							</div>
						</div>

						<div class="signals-box">
							<div class="signal-item warning">
								<span class="sig-icon">⚠</span>
								<div>
									<strong>Plafon Belanja Mandiri Terlampaui</strong>
									<p>Batas maksimal mandiri Rp 1.000.000. Pengeluaran ini Rp 2.750.000 dan memerlukan persetujuan.</p>
								</div>
							</div>
							<div class="signal-item safe">
								<span class="sig-icon">✓</span>
								<div>
									<strong>Pemeriksaan Duplikat Bersih</strong>
									<p>Tidak ditemukan nota identik pada arsip seluruh departemen dalam 180 hari terakhir.</p>
								</div>
							</div>
						</div>

						{#if simulatedDecision === 'idle'}
							<div class="review-actions-stage">
								<p class="action-prompt">Simulasikan keputusan tim finance untuk klaim ini:</p>
								<div class="action-buttons">
									<button type="button" class="btn-approve" onclick={() => handleSimulatedDecision('approved')}>
										✓ Setujui dengan Catatan
									</button>
									<button type="button" class="btn-reject" onclick={() => handleSimulatedDecision('rejected')}>
										✕ Tolak Klaim
									</button>
								</div>
							</div>
						{:else}
							<div class="decision-result-box" class:approved={simulatedDecision === 'approved'} class:rejected={simulatedDecision === 'rejected'}>
								<div class="result-header">
									<strong>{simulatedDecision === 'approved' ? '✓ Klaim Berhasil Disetujui' : '✕ Klaim Ditolak'}</strong>
									<button type="button" class="btn-reset" onclick={resetDecision}>Coba Lagi</button>
								</div>
								<p class="result-note">{decisionNote}</p>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</section>

		<!-- 4. LAPORAN & CSV SHOWCASE -->
		<section use:reveal id="laporan" class="feature-section scroll-reveal" aria-labelledby="laporan-title">
			<div class="section-badge">MODUL FINANCE · ANALITIK &amp; REKONSILIASI</div>
			<div class="feature-grid reverse">
				<!-- Interactive Analytics & Export Demo -->
				<div class="interactive-card">
					<div class="card-header">
						<span class="card-title">Ringkasan Analitik Pengeluaran</span>
						<div class="period-toggle">
							<button type="button" class:active={reportPeriod === 'month'} onclick={() => (reportPeriod = 'month')}>Bulan Ini</button>
							<button type="button" class:active={reportPeriod === 'quarter'} onclick={() => (reportPeriod = 'quarter')}>Kuartal 3</button>
						</div>
					</div>

					<div class="analytics-dashboard-demo">
						<div class="kpi-row">
							<div class="kpi-card">
								<small>Total Pengeluaran</small>
								<strong>{reportPeriod === 'month' ? 'Rp 38.650.000' : 'Rp 114.200.000'}</strong>
								<span class="kpi-sub">82 nota terproses</span>
							</div>
							<div class="kpi-card highlight">
								<small>Rasio Otomatisasi AI</small>
								<strong>88.5%</strong>
								<span class="kpi-sub">Tanpa sentuhan manual</span>
							</div>
							<div class="kpi-card">
								<small>Rata-rata Keputusan</small>
								<strong>1.4 Menit</strong>
								<span class="kpi-sub">Hemat 94% waktu</span>
							</div>
						</div>

						<div class="category-breakdown">
							<div class="breakdown-header">
								<span>Distribusi Pengeluaran</span>
								<small>Berdasarkan Kategori Kebijakan</small>
							</div>
							<div class="breakdown-bars">
								<div class="bar-row">
									<span>Makanan &amp; Minuman</span>
									<div class="bar-track"><div class="bar-fill" style="width: 45%;"></div></div>
									<small>45%</small>
								</div>
								<div class="bar-row">
									<span>Transportasi Dinas</span>
									<div class="bar-track"><div class="bar-fill" style="width: 30%;"></div></div>
									<small>30%</small>
								</div>
								<div class="bar-row">
									<span>Perlengkapan Kerja</span>
									<div class="bar-track"><div class="bar-fill" style="width: 15%;"></div></div>
									<small>15%</small>
								</div>
								<div class="bar-row">
									<span>Akomodasi &amp; Lainnya</span>
									<div class="bar-track"><div class="bar-fill" style="width: 10%;"></div></div>
									<small>10%</small>
								</div>
							</div>
						</div>

						<div class="export-banner">
							<div class="export-copy">
								<strong>Ekspor Data Rekonsiliasi</strong>
								<small>Format CSV terstandar siap diimpor ke sistem akuntansi Anda.</small>
							</div>
							<button type="button" class="btn-download" onclick={downloadSampleCSV}>
								<span aria-hidden="true">📥</span> Unduh Simulasi CSV
							</button>
						</div>
					</div>
				</div>

				<div class="feature-copy">
					<h2 id="laporan-title">Tutup buku akhir bulan lebih cepat tanpa tumpukan kertas.</h2>
					<p>
						Tera merapikan seluruh data transaksi ke dalam agregasi yang bersih dan transparan. Semua klaim yang disetujui, ditolak, maupun sedang menunggu verifikasi dapat dipantau trennya serta diekspor dalam satu kali klik.
					</p>

					<div class="feature-bullets">
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Visibilitas Arus Kas Real-Time</strong>
								<p>Ketahui pengeluaran per divisi dan kategori secara langsung tanpa menunggu laporan akhir bulan.</p>
							</div>
						</div>
						<div class="bullet-item">
							<span class="bullet-check">✓</span>
							<div>
								<strong>Ekspor CSV Terstruktur</strong>
								<p>Mencakup ID klaim, nama vendor, kode alasan keputusan, ID transaksi, dan timestamp verifikasi.</p>
							</div>
						</div>
					</div>

					<div class="feature-cta-row">
						<a class="button" href="/reports">Buka Modul Laporan <span aria-hidden="true">→</span></a>
					</div>
				</div>
			</div>
		</section>

		<!-- Bottom Closing Banner -->
		<section use:reveal class="closing-banner scroll-reveal">
			<div class="closing-content">
				<h2>Mulai otomatisasi pengeluaran kerja tim Anda hari ini.</h2>
				<p>Unggah nota pertamamu dan saksikan bagaimana Tera menyelesaikan pemeriksaan dalam hitungan detik.</p>
				<div class="closing-actions">
					<a class="button primary-cta" href="/pengajuan">Mulai Pengajuan <span aria-hidden="true">→</span></a>
					<a class="button secondary-cta" href="/login">Masuk ke Akun</a>
				</div>
			</div>
		</section>
	</main>

	<!-- Footer -->
	<footer class="landing-footer">
		<div class="footer-shell">
			<div class="footer-bottom">
				<p>Tera · AI Expense Agent untuk Tim Modern.</p>
				<div class="footer-meta-links">
					<a href="/">Beranda</a>
					<a href="/produk">Produk</a>
					<a href="/login">Masuk Akun</a>
				</div>
			</div>
		</div>
	</footer>
</div>

<style>
	/* Tera Design Tokens & Styling */
	.product-page {
		--color-bg: #FAFCFB;
		--color-surface: #FFFFFF;
		--color-ink: #002D28;
		--color-primary: #0F766E;
		--color-primary-dark: #004D40;
		--color-accent: #14B8A6;
		--color-mint: #A7F3D0;
		--color-light: #E6F4F1;
		--color-border: #D1E5E1;
		--color-border-strong: #A3C9C1;
		--color-text-muted: #4B635F;

		background-color: var(--color-bg);
		color: var(--color-ink);
		font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
		min-height: 100vh;
	}

	/* Navbar */
	.navbar-shell {
		position: sticky;
		top: 16px;
		z-index: 50;
		width: min(1040px, calc(100% - 48px));
		margin: 16px auto;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 20px;
		box-shadow: 0 4px 20px rgb(0 45 40 / .07);
		transition: background-color 220ms ease, box-shadow 220ms ease;
	}
	.navbar-shell.scrolled {
		background: rgb(255 255 255 / .92);
		backdrop-filter: blur(14px);
		border-color: var(--color-border-strong);
		box-shadow: 0 10px 30px rgb(0 45 40 / .11);
	}
	.landing-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 20px;
	}
	.wordmark {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		color: var(--color-ink);
		text-decoration: none;
		font-size: 24px;
		font-weight: 800;
		letter-spacing: -1px;
	}
	.nav-links {
		display: flex;
		align-items: center;
		gap: 28px;
	}
	.nav-links a {
		color: var(--color-ink);
		text-decoration: none;
		font-size: 14px;
		font-weight: 500;
		padding: 8px 0;
		transition: color 180ms ease;
	}
	.nav-links a:hover, .nav-links a.active-nav {
		color: var(--color-primary);
		font-weight: 600;
	}
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.nav-cta {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--color-ink);
		color: white;
		padding: 8px 18px;
		border-radius: 999px;
		text-decoration: none;
		font-size: 13px;
		font-weight: 600;
		transition: transform 180ms ease, background 180ms ease;
	}
	.nav-cta:hover {
		background: var(--color-primary);
		transform: translateY(-1px);
	}
	.menu-toggle {
		display: none;
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 6px;
		color: var(--color-ink);
		cursor: pointer;
	}

	/* Hero Section */
	.product-hero {
		position: relative;
		overflow: hidden;
		padding: 60px 24px 40px;
		text-align: center;
	}
	.hero-container {
		max-width: 860px;
		margin: 0 auto;
	}
	.badge-pill {
		display: inline-block;
		background: var(--color-light);
		color: var(--color-primary-dark);
		border: 1px solid var(--color-mint);
		padding: 6px 14px;
		border-radius: 999px;
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		margin-bottom: 20px;
	}
	.product-hero h1 {
		font-size: clamp(34px, 5vw, 56px);
		font-weight: 800;
		letter-spacing: -0.04em;
		line-height: 1.1;
		color: var(--color-ink);
		margin-bottom: 20px;
	}
	.product-hero h1 span {
		color: var(--color-primary);
	}
	.product-hero p {
		font-size: clamp(16px, 2vw, 19px);
		line-height: 1.6;
		color: var(--color-text-muted);
		max-width: 680px;
		margin: 0 auto 36px;
	}

	/* Subnav Pills */
	.feature-pills {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: 8px;
		padding: 6px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 999px;
		box-shadow: 0 4px 16px rgb(0 45 40 / .06);
	}
	.feature-pills a {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 8px 16px;
		border-radius: 999px;
		text-decoration: none;
		font-size: 13px;
		font-weight: 600;
		color: var(--color-ink);
		transition: all 180ms ease;
	}
	.feature-pills a:hover, .feature-pills a.chosen {
		background: var(--color-light);
		color: var(--color-primary-dark);
	}
	.pill-icon {
		font-size: 14px;
		color: var(--color-primary);
	}

	/* Feature Sections */
	.feature-section {
		width: min(1140px, calc(100% - 48px));
		margin: 80px auto;
		scroll-margin-top: 100px;
	}
	.section-badge {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.1em;
		color: var(--color-primary);
		margin-bottom: 16px;
	}
	.feature-grid {
		display: grid;
		grid-template-columns: 1fr 1.15fr;
		gap: 48px;
		align-items: center;
	}
	.feature-grid.reverse {
		grid-template-columns: 1.15fr 1fr;
	}

	.feature-copy h2 {
		font-size: clamp(26px, 3vw, 36px);
		font-weight: 800;
		line-height: 1.2;
		letter-spacing: -0.03em;
		margin-bottom: 18px;
	}
	.feature-copy p {
		font-size: 15px;
		line-height: 1.7;
		color: var(--color-text-muted);
		margin-bottom: 24px;
	}
	.feature-bullets {
		display: flex;
		flex-direction: column;
		gap: 16px;
		margin-bottom: 32px;
	}
	.bullet-item {
		display: flex;
		gap: 12px;
		align-items: flex-start;
	}
	.bullet-check {
		display: grid;
		place-items: center;
		width: 22px;
		height: 22px;
		background: var(--color-mint);
		color: var(--color-primary-dark);
		border-radius: 50%;
		font-size: 12px;
		font-weight: bold;
		flex-shrink: 0;
		margin-top: 2px;
	}
	.bullet-item strong {
		display: block;
		font-size: 14px;
		font-weight: 700;
		color: var(--color-ink);
	}
	.bullet-item p {
		font-size: 13px;
		margin: 4px 0 0;
		line-height: 1.5;
	}
	.feature-cta-row {
		display: flex;
		align-items: center;
		gap: 16px;
		flex-wrap: wrap;
	}
	.feature-cta-row .button {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		background: var(--color-primary);
		color: white;
		padding: 10px 20px;
		border-radius: 8px;
		text-decoration: none;
		font-size: 14px;
		font-weight: 600;
		transition: background 180ms ease;
	}
	.feature-cta-row .button:hover {
		background: var(--color-primary-dark);
	}
	.cta-hint {
		font-size: 12px;
		color: var(--color-text-muted);
	}

	/* Interactive Card */
	.interactive-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 16px;
		box-shadow: 0 16px 36px rgb(0 45 40 / .07);
		overflow: hidden;
	}
	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 14px 20px;
		border-bottom: 1px solid var(--color-border);
		background: #F6FBF9;
	}
	.card-title {
		font-size: 13px;
		font-weight: 700;
		color: var(--color-ink);
	}
	.live-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		font-weight: 600;
		color: var(--color-primary);
		background: var(--color-light);
		padding: 3px 8px;
		border-radius: 999px;
	}
	.live-pill::before {
		content: '';
		width: 6px;
		height: 6px;
		background: var(--color-accent);
		border-radius: 50%;
	}

	/* 1. OCR Stage */
	.sample-picker-bar {
		padding: 12px 18px;
		border-bottom: 1px solid var(--color-border);
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
		background: white;
	}
	.picker-label {
		font-size: 12px;
		font-weight: 600;
		color: var(--color-text-muted);
	}
	.sample-chips {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chip-button {
		background: var(--color-light);
		border: 1px solid transparent;
		color: var(--color-ink);
		font-size: 12px;
		font-weight: 600;
		padding: 4px 10px;
		border-radius: 6px;
		cursor: pointer;
		transition: all 150ms ease;
	}
	.chip-button:hover, .chip-button.active {
		background: var(--color-primary);
		color: white;
	}
	.receipt-stage {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		padding: 20px;
		background: #FAFCFB;
	}
	.receipt-paper {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 16px;
		box-shadow: 0 4px 12px rgb(0 0 0 / .04);
		font-family: monospace;
		font-size: 12px;
		position: relative;
	}
	.receipt-topline {
		display: flex;
		justify-content: space-between;
		font-size: 10px;
		color: var(--color-text-muted);
		margin-bottom: 8px;
	}
	.receipt-vendor-block {
		margin-bottom: 12px;
	}
	.receipt-vendor {
		display: block;
		font-size: 14px;
		font-weight: 800;
		color: var(--color-ink);
	}
	.receipt-date {
		font-size: 11px;
		color: var(--color-text-muted);
	}
	.receipt-divider {
		border-top: 1px dashed var(--color-border-strong);
		margin: 10px 0;
	}
	.receipt-items-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.receipt-item-row {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
	}
	.receipt-total-row {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		margin-top: 8px;
	}
	.receipt-total-val {
		font-size: 14px;
		color: var(--color-primary-dark);
	}
	.confidence-tag {
		margin-top: 12px;
		padding-top: 8px;
		border-top: 1px solid var(--color-border);
		display: flex;
		justify-content: space-between;
		font-size: 10px;
		color: var(--color-text-muted);
	}
	.confidence-tag strong {
		color: var(--color-primary);
	}

	/* OCR Inspector */
	.ocr-inspector {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.inspector-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 700;
		width: fit-content;
	}
	.badge-approved {
		background: #DCFCE7;
		color: #166534;
	}
	.badge-escalated {
		background: #FEF3C7;
		color: #92400E;
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
	}
	.inspector-field {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 10px 12px;
	}
	.inspector-field small {
		display: block;
		font-size: 10px;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 2px;
	}
	.inspector-field span {
		font-size: 13px;
		font-weight: 600;
		color: var(--color-ink);
	}
	.inspector-explanation {
		background: var(--color-light);
		border-left: 3px solid var(--color-primary);
		padding: 10px 12px;
		border-radius: 0 8px 8px 0;
	}
	.inspector-explanation small {
		display: block;
		font-size: 11px;
		font-weight: 700;
		color: var(--color-primary-dark);
		margin-bottom: 4px;
	}
	.inspector-explanation p {
		font-size: 12px;
		line-height: 1.5;
		margin: 0;
		color: var(--color-ink);
	}

	/* 2. Timeline Stepper */
	.timeline-container {
		display: grid;
		grid-template-columns: 1fr 1.1fr;
		padding: 18px;
		gap: 16px;
	}
	.timeline-stepper {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.stepper-item {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		padding: 10px 12px;
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		text-align: left;
		cursor: pointer;
		transition: all 180ms ease;
	}
	.stepper-item:hover, .stepper-item.selected {
		border-color: var(--color-primary);
		background: var(--color-light);
	}
	.stepper-dot {
		display: grid;
		place-items: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--color-border);
		font-size: 11px;
		font-weight: bold;
		color: var(--color-ink);
		flex-shrink: 0;
	}
	.stepper-item.selected .stepper-dot {
		background: var(--color-primary);
		color: white;
	}
	.stepper-meta small {
		display: block;
		font-size: 10px;
		color: var(--color-text-muted);
	}
	.stepper-meta strong {
		font-size: 12px;
		color: var(--color-ink);
	}
	.timeline-detail-panel {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 10px;
		padding: 18px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.panel-step-label {
		font-size: 11px;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.timeline-detail-panel h4 {
		font-size: 16px;
		font-weight: 700;
		margin: 0;
		color: var(--color-ink);
	}
	.tag-pill {
		display: inline-block;
		width: fit-content;
		background: var(--color-light);
		color: var(--color-primary-dark);
		padding: 4px 10px;
		border-radius: 999px;
		font-size: 11px;
		font-weight: 700;
	}
	.panel-desc {
		font-size: 13px;
		line-height: 1.6;
		color: var(--color-text-muted);
		margin: 0;
	}
	.panel-security-note {
		margin-top: auto;
		padding-top: 12px;
		border-top: 1px dashed var(--color-border);
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.panel-security-note small {
		font-size: 11px;
		color: var(--color-text-muted);
	}

	/* 3. Review Workbench Demo */
	.review-workbench-demo {
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.review-meta-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		border-bottom: 1px solid var(--color-border);
		padding-bottom: 14px;
	}
	.claim-id-tag {
		font-size: 11px;
		font-weight: 700;
		color: var(--color-primary);
		letter-spacing: 0.05em;
	}
	.review-meta-header h3 {
		font-size: 16px;
		font-weight: 800;
		margin: 4px 0 2px;
	}
	.review-meta-header small {
		color: var(--color-text-muted);
		font-size: 12px;
	}
	.risk-meter {
		text-align: right;
	}
	.risk-label {
		display: block;
		font-size: 11px;
		color: var(--color-text-muted);
	}
	.risk-value.high {
		color: #DC2626;
		font-size: 14px;
	}
	.signals-box {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.signal-item {
		display: flex;
		gap: 10px;
		padding: 10px 12px;
		border-radius: 8px;
		font-size: 12px;
	}
	.signal-item.warning {
		background: #FFFBEB;
		border: 1px solid #FCD34D;
		color: #92400E;
	}
	.signal-item.safe {
		background: #F0FDF4;
		border: 1px solid #BBF7D0;
		color: #166534;
	}
	.sig-icon {
		font-size: 16px;
		font-weight: bold;
	}
	.signal-item strong {
		display: block;
		margin-bottom: 2px;
	}
	.signal-item p {
		margin: 0;
		font-size: 11px;
	}
	.review-actions-stage {
		background: #F6FBF9;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 14px;
	}
	.action-prompt {
		font-size: 12px;
		font-weight: 600;
		color: var(--color-text-muted);
		margin: 0 0 10px;
	}
	.action-buttons {
		display: flex;
		gap: 10px;
	}
	.btn-approve, .btn-reject {
		padding: 8px 16px;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 700;
		cursor: pointer;
		border: 0;
		transition: opacity 150ms ease;
	}
	.btn-approve {
		background: var(--color-primary);
		color: white;
	}
	.btn-reject {
		background: #EF4444;
		color: white;
	}
	.btn-approve:hover, .btn-reject:hover {
		opacity: 0.9;
	}
	.decision-result-box {
		padding: 14px;
		border-radius: 8px;
		border: 1px solid;
	}
	.decision-result-box.approved {
		background: #ECFDF5;
		border-color: #A7F3D0;
		color: #065F46;
	}
	.decision-result-box.rejected {
		background: #FEF2F2;
		border-color: #FECACA;
		color: #991B1B;
	}
	.result-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 6px;
	}
	.result-note {
		font-size: 12px;
		line-height: 1.5;
		margin: 0;
	}
	.btn-reset {
		background: transparent;
		border: 1px solid currentColor;
		border-radius: 4px;
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		cursor: pointer;
		color: inherit;
	}

	/* 4. Analytics & CSV */
	.period-toggle {
		display: flex;
		gap: 4px;
	}
	.period-toggle button {
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 3px 8px;
		font-size: 11px;
		font-weight: 600;
		cursor: pointer;
		color: var(--color-text-muted);
	}
	.period-toggle button.active {
		background: var(--color-primary);
		color: white;
		border-color: var(--color-primary);
	}
	.analytics-dashboard-demo {
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.kpi-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 12px;
	}
	.kpi-card {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 12px;
	}
	.kpi-card.highlight {
		border-color: var(--color-primary);
		background: var(--color-light);
	}
	.kpi-card small {
		display: block;
		font-size: 10px;
		color: var(--color-text-muted);
		margin-bottom: 4px;
	}
	.kpi-card strong {
		display: block;
		font-size: 16px;
		font-weight: 800;
		color: var(--color-ink);
	}
	.kpi-sub {
		display: block;
		font-size: 10px;
		color: var(--color-primary);
		margin-top: 4px;
	}
	.category-breakdown {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 14px;
	}
	.breakdown-header {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		margin-bottom: 12px;
		font-weight: 600;
	}
	.breakdown-header small {
		color: var(--color-text-muted);
	}
	.breakdown-bars {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.bar-row {
		display: grid;
		grid-template-columns: 140px 1fr 35px;
		align-items: center;
		gap: 10px;
		font-size: 11px;
	}
	.bar-track {
		height: 8px;
		background: var(--color-light);
		border-radius: 4px;
		overflow: hidden;
	}
	.bar-fill {
		height: 100%;
		background: var(--color-primary);
		border-radius: 4px;
	}
	.export-banner {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		background: #F0FDF9;
		border: 1px solid var(--color-mint);
		border-radius: 8px;
	}
	.export-copy strong {
		display: block;
		font-size: 13px;
		color: var(--color-ink);
	}
	.export-copy small {
		display: block;
		font-size: 11px;
		color: var(--color-text-muted);
	}
	.btn-download {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--color-primary);
		color: white;
		border: 0;
		padding: 8px 14px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 700;
		cursor: pointer;
		transition: background 150ms ease;
	}
	.btn-download:hover {
		background: var(--color-primary-dark);
	}

	/* Closing Banner */
	.closing-banner {
		width: min(1040px, calc(100% - 48px));
		margin: 80px auto;
		background: linear-gradient(135deg, var(--color-primary-dark) 0%, #002D28 100%);
		color: white;
		padding: 60px 32px;
		border-radius: 24px;
		text-align: center;
		box-shadow: 0 20px 48px rgb(0 45 40 / .16);
	}
	.closing-content h2 {
		font-size: clamp(28px, 4vw, 42px);
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 14px;
	}
	.closing-content p {
		font-size: 16px;
		color: var(--color-mint);
		max-width: 580px;
		margin: 0 auto 32px;
		line-height: 1.6;
	}
	.closing-actions {
		display: flex;
		justify-content: center;
		gap: 14px;
		flex-wrap: wrap;
	}
	.primary-cta {
		background: var(--color-mint);
		color: var(--color-primary-dark);
		padding: 12px 24px;
		border-radius: 999px;
		font-weight: 700;
		text-decoration: none;
		transition: transform 180ms ease, background 180ms ease;
	}
	.primary-cta:hover {
		background: white;
		transform: translateY(-2px);
	}
	.secondary-cta {
		background: transparent;
		color: white;
		border: 1px solid rgba(255, 255, 255, 0.4);
		padding: 12px 24px;
		border-radius: 999px;
		font-weight: 600;
		text-decoration: none;
		transition: border-color 180ms ease, background 180ms ease;
	}
	.secondary-cta:hover {
		border-color: white;
		background: rgba(255, 255, 255, 0.08);
	}

	/* Footer */
	.landing-footer {
		border-top: 1px solid var(--color-border);
		padding: 32px 24px;
		background: white;
	}
	.footer-shell {
		width: min(1040px, 100%);
		margin: 0 auto;
	}
	.footer-bottom {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 13px;
		color: var(--color-text-muted);
		flex-wrap: wrap;
		gap: 16px;
	}
	.footer-meta-links {
		display: flex;
		gap: 20px;
	}
	.footer-meta-links a {
		color: var(--color-ink);
		text-decoration: none;
		font-weight: 500;
	}
	.footer-meta-links a:hover {
		color: var(--color-primary);
	}

	/* Responsive */
	@media (max-width: 900px) {
		.feature-grid, .feature-grid.reverse {
			grid-template-columns: 1fr;
			gap: 32px;
		}
		.receipt-stage {
			grid-template-columns: 1fr;
		}
		.timeline-container {
			grid-template-columns: 1fr;
		}
		.nav-links {
			display: none;
		}
		.menu-toggle {
			display: flex;
		}
		.kpi-row {
			grid-template-columns: 1fr;
		}
		.export-banner {
			flex-direction: column;
			gap: 12px;
			align-items: flex-start;
		}
	}
</style>
