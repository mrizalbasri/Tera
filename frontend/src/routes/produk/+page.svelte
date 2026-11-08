<script lang="ts">
	import TeraBrandRibbon from '$lib/components/TeraBrandRibbon.svelte';
	import { reveal } from '$lib/actions/reveal';

	// Nav state (exact match with landing page)
	let mobileMenu = $state(false);
	let productMenu = $state(false);
	let productButton = $state<HTMLButtonElement>();
	let menuButton = $state<HTMLButtonElement>();
	let headerElement = $state<HTMLElement>();
	let scrolled = $state(false);

	let hoverTimer: ReturnType<typeof setTimeout> | undefined;
	let lastMouseEnterTime = 0;
	function openProductMenu() {
		if (hoverTimer) clearTimeout(hoverTimer);
		lastMouseEnterTime = Date.now();
		productMenu = true;
	}
	function scheduleCloseProductMenu() {
		if (hoverTimer) clearTimeout(hoverTimer);
		hoverTimer = setTimeout(() => {
			productMenu = false;
		}, 200);
	}
	function toggleProductMenu() {
		if (hoverTimer) clearTimeout(hoverTimer);
		if (productMenu && Date.now() - lastMouseEnterTime < 400) {
			return;
		}
		productMenu = !productMenu;
	}
	function closeMenus() {
		if (hoverTimer) clearTimeout(hoverTimer);
		mobileMenu = false;
		productMenu = false;
	}
</script>

<svelte:head>
	<title>Fitur & Alur Kerja · Tera</title>
	<meta name="description" content="Pelajari bagaimana Tera membaca nota, memeriksa ketentuan pengeluaran kerja, meninjau klaim, dan merapikan laporan keuangan tim." />
</svelte:head>

<svelte:window 
	onscroll={() => { const next = window.scrollY > 16; if (next !== scrolled) scrolled = next; }}
	onpointerdown={(event) => { if (event.target instanceof Node && !headerElement?.contains(event.target)) closeMenus(); }}
	onkeydown={(event) => {
		if (event.key === 'Escape') {
			if (productMenu) { productMenu = false; productButton?.focus(); }
			else if (mobileMenu) { mobileMenu = false; menuButton?.focus(); }
		}
	}}
/>

<div class="landing">
	<!-- Navbar (100% Identical with Homepage) -->
	<div class="navbar-shell" class:scrolled>
		<header bind:this={headerElement} class="landing-header" onfocusout={(event) => { if (event.relatedTarget instanceof Node && !headerElement?.contains(event.relatedTarget)) productMenu = false; }}>
			<a class="wordmark" href="/" aria-label="Tera, beranda">
				<img src="/logo.webp" alt="" width="36" height="36" />
				<span>Tera</span>
			</a>
			<nav class:expanded={mobileMenu} id="landing-nav" aria-label="Navigasi produk">
				<div class="nav-links">
					<button 
						bind:this={productButton} 
						type="button" 
						class="product-trigger" 
						class:selected={productMenu} 
						aria-expanded={productMenu} 
						aria-controls="product-panel" 
						onmouseenter={openProductMenu}
						onmouseleave={scheduleCloseProductMenu}
						onclick={toggleProductMenu}>
						Produk 
						<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
							<path d="m4 6 4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					</button>
					<div class="product-panel" class:shown={productMenu} id="product-panel" role="region" aria-label="Menu produk" inert={!productMenu} onmouseenter={openProductMenu} onmouseleave={scheduleCloseProductMenu}>
						<div class="product-panel-content">
							<a class="product-spotlight" href="/produk" onclick={closeMenus}>
								<span class="menu-eyebrow">KENALI TERA</span>
								<strong>Dari nota<br />ke keputusan.</strong>
								<span class="spotlight-description">Lihat bagaimana Tera memeriksa pengeluaran kerja.</span>
								<img src="/brand/tera-receipt-curved.png" alt="" width="1280" height="1280" />
								<span class="spotlight-link">Jelajahi fitur lengkap <span aria-hidden="true">↗</span></span>
							</a>
							<div class="product-shortcuts">
								<a href="/produk#pengajuan" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">↥</span>
									<span><strong>Ajukan klaim</strong><small>Unggah nota dan mulai pemeriksaan.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/produk#riwayat" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">≡</span>
									<span><strong>Riwayat pengajuan</strong><small>Ikuti status dan jejak setiap klaim.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/produk#review" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">✓</span>
									<span><strong>Review klaim</strong><small>Tinjau bukti dan tentukan tindak lanjut.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/produk#laporan" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">↗</span>
									<span><strong>Laporan pengeluaran</strong><small>Lihat ringkasan dan ekspor data klaim.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
							</div>
							<div class="product-panel-footer">
								<span>Satu alur untuk karyawan dan finance.</span>
								<a href="/#untuk-tim" onclick={closeMenus}>Tera untuk tim <span aria-hidden="true">→</span></a>
							</div>
						</div>
					</div>
					<a href="/#fitur" onclick={closeMenus}>Fitur</a>
					<a href="/#cara-kerja" onclick={closeMenus}>Cara kerja</a>
					<a href="/#untuk-tim" onclick={closeMenus}>Untuk tim</a>
					<a href="/#faq" onclick={closeMenus}>FAQ</a>
				</div>
			</nav>
			<div class="nav-actions">
				<a class="button nav-cta" href="/pengajuan">Buka aplikasi <span aria-hidden="true">↗</span></a>
				<button 
					bind:this={menuButton} 
					class="menu-toggle secondary" 
					class:opened={mobileMenu} 
					type="button" 
					aria-label={mobileMenu ? 'Tutup navigasi' : 'Buka navigasi'} 
					aria-expanded={mobileMenu} 
					aria-controls="landing-nav" 
					onclick={() => { mobileMenu = !mobileMenu; productMenu = false; }}>
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
						<path class="hamburger-top" d="M4 6h16" />
						<path class="hamburger-middle" d="M4 12h16" />
						<path class="hamburger-bottom" d="M4 18h16" />
					</svg>
				</button>
			</div>
		</header>
	</div>

	<main id="main-content" tabindex="-1">
		<!-- Hero Section -->
		<div class="hero-stage">
			<TeraBrandRibbon />
			<section class="hero-copy-centered">
				<span class="eyebrow-tag">KEMAMPUAN TERA</span>
				<h1>Alur pengeluaran kerja,<br /><span>dari awal sampai selesai.</span></h1>
				<p>
					Mulai dari mengunggah nota, memeriksa kesesuaian kebijakan, meninjau klaim bersama buktinya, hingga menyiapkan laporan pengeluaran tim.
				</p>
			</section>
		</div>

		<!-- 1. AJUKAN KLAIM (#pengajuan) -->
		<section use:reveal class="feature-block scroll-reveal" id="pengajuan">
			<div class="feature-content">
				<div class="feature-text">
					<span class="feature-number">01</span>
					<span class="feature-category">PENGAJUAN KLAIM</span>
					<h2>Kirim nota, biarkan detailnya dirapikan.</h2>
					<p>
						Unggah foto nota fisik atau berkas PDF pengeluaran kerja. Tera membaca data penting dari nota, mencocokkannya dengan ketentuan pengeluaran, dan menampilkan hasil pemeriksaannya.
					</p>
					<ul class="feature-keypoints">
						<li><strong>Pembacaan data penting:</strong> Nama tempat belanja, tanggal transaksi, nominal total, dan rincian pembelian langsung terangkum.</li>
						<li><strong>Pemeriksaan ketentuan:</strong> Menilai apakah nominal dan kategori pengeluaran sesuai dengan aturan yang berlaku di tim.</li>
						<li><strong>Bisa diklarifikasi:</strong> Jika nota buram atau informasi belum lengkap, kamu bisa melengkapinya tanpa harus membuat klaim baru dari awal.</li>
					</ul>
					<a class="button cta-link" href="/pengajuan">Ajukan klaim baru <span aria-hidden="true">↗</span></a>
				</div>
				<div class="feature-preview-card">
					<div class="card-caption">CONTOH PEMBACAAN NOTA</div>
					<div class="receipt-card-mockup">
						<div class="receipt-header-row">
							<div>
								<strong class="receipt-vendor">Restoran Padang Sederhana</strong>
								<span class="receipt-sub">14 Oktober 2026 · 13:15 WIB</span>
							</div>
							<span class="status-chip success">Terbaca</span>
						</div>
						<div class="receipt-item-table">
							<div class="item-line"><span>Paket Makan Siang Tim (4 Orang)</span><strong>Rp 340.000</strong></div>
							<div class="item-line"><span>Minuman &amp; Aneka Jus</span><strong>Rp 80.000</strong></div>
							<div class="item-line total-line"><span>Total Terbaca</span><strong class="total-amount">Rp 420.000</strong></div>
						</div>
						<div class="policy-eval-box">
							<div class="policy-status-pill">
								<span class="eval-dot"></span>
								<span>Sesuai Kebijakan (Maks. Rp 500.000 per pertemuan)</span>
							</div>
							<p>Klaim memenuhi syarat dan siap diproses ke langkah berikutnya.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- 2. RIWAYAT PENGAJUAN (#riwayat) -->
		<section use:reveal class="feature-block scroll-reveal" id="riwayat">
			<div class="feature-content reverse">
				<div class="feature-text">
					<span class="feature-number">02</span>
					<span class="feature-category">RIWAYAT KLAIM</span>
					<h2>Pantau status dan jejak setiap pengajuan.</h2>
					<p>
						Setiap proses pemeriksaan tercatat dengan jelas. Karyawan bisa memantau perkembangan klaim kapan saja dan mengetahui alasan di balik setiap keputusan.
					</p>
					<ul class="feature-keypoints">
						<li><strong>Status yang jelas:</strong> Mengetahui apakah klaim sedang diperiksa, membutuhkan klarifikasi, atau sudah disetujui.</li>
						<li><strong>Alasan keputusan terbuka:</strong> Setiap hasil pemeriksaan disertai keterangan aturan dan pertimbangan yang jelas.</li>
						<li><strong>Bukti tersimpan rapi:</strong> Foto nota dan detail transaksi tersimpan di satu tempat agar mudah ditinjau kembali.</li>
					</ul>
					<a class="button cta-link" href="/riwayat">Buka riwayat klaim <span aria-hidden="true">↗</span></a>
				</div>
				<div class="feature-preview-card">
					<div class="card-caption">TAHAPAN PEMERIKSAAN KLAIM</div>
					<div class="timeline-visual">
						<div class="timeline-row passed">
							<span class="step-badge">1</span>
							<div class="step-info">
								<strong>Nota diterima</strong>
								<small>Bukti nota diunggah dan disimpan ke dalam klaim.</small>
							</div>
						</div>
						<div class="timeline-row passed">
							<span class="step-badge">2</span>
							<div class="step-info">
								<strong>Data dibaca</strong>
								<small>Vendor, tanggal, dan nominal dirangkum secara terstruktur.</small>
							</div>
						</div>
						<div class="timeline-row passed">
							<span class="step-badge">3</span>
							<div class="step-info">
								<strong>Kebijakan dicocokkan</strong>
								<small>Batas nominal dan kategori pengeluaran diperiksa.</small>
							</div>
						</div>
						<div class="timeline-row passed">
							<span class="step-badge">4</span>
							<div class="step-info">
								<strong>Risiko &amp; duplikasi ditinjau</strong>
								<small>Memeriksa apakah nota serupa pernah diajukan sebelumnya.</small>
							</div>
						</div>
						<div class="timeline-row active">
							<span class="step-badge">5</span>
							<div class="step-info">
								<strong>Keputusan &amp; tindak lanjut</strong>
								<small>Hasil pemeriksaan diperbarui bersama catatan untuk karyawan.</small>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- 3. REVIEW KLAIM (#review) -->
		<section use:reveal class="feature-block scroll-reveal" id="review">
			<div class="feature-content">
				<div class="feature-text">
					<span class="feature-number">03</span>
					<span class="feature-category">REVIEW FINANCE</span>
					<h2>Tinjau klaim bersama buktinya.</h2>
					<p>
						Pengeluaran rutin yang sesuai aturan dapat diproses cepat. Tim finance cukup fokus meninjau klaim yang melebihi batas atau membutuhkan persetujuan khusus.
					</p>
					<ul class="feature-keypoints">
						<li><strong>Tanda pengingat:</strong> Memperjelas klaim yang melebihi anggaran atau memiliki detail yang perlu dipastikan.</li>
						<li><strong>Pemeriksaan duplikat:</strong> Membantu melihat jika ada nota atau nominal serupa yang diajukan berulang.</li>
						<li><strong>Catatan reviewer:</strong> Keputusan setuju atau tolak dapat dilengkapi pesan penjelasan yang ikut tercatat.</li>
					</ul>
					<a class="button cta-link" href="/reviews">Buka antrean review <span aria-hidden="true">↗</span></a>
				</div>
				<div class="feature-preview-card">
					<div class="card-caption">CONTOH ANTREAN REVIEW</div>
					<div class="reviewer-card-mockup">
						<div class="claim-topbar">
							<div>
								<span class="claim-tag">Klaim #CLM-2026-089</span>
								<h4>Perlengkapan Monitor Kerja</h4>
							</div>
							<div class="anomaly-pill high">
								<span>Perlu tinjauan finance</span>
							</div>
						</div>
						<div class="review-details-grid">
							<div class="detail-box">
								<small>Pengaju</small>
								<span>Ahmad Fauzi (Produk)</span>
							</div>
							<div class="detail-box">
								<small>Total Klaim</small>
								<strong class="highlight-val">Rp 2.750.000</strong>
							</div>
						</div>
						<div class="signals-summary">
							<div class="sig-pill warning">
								<span>⚠️ Melebihi plafon mandiri (Maks. Rp 1.000.000 tanpa PO)</span>
							</div>
							<div class="sig-pill clean">
								<span>✓ Tidak ditemukan duplikasi dengan nota lain</span>
							</div>
						</div>
						<div class="review-action-hint">
							<span>Tindakan:</span>
							<strong>Menunggu Keputusan Reviewer</strong>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- 4. LAPORAN PENGELUARAN (#laporan) -->
		<section use:reveal class="feature-block scroll-reveal" id="laporan">
			<div class="feature-content reverse">
				<div class="feature-text">
					<span class="feature-number">04</span>
					<span class="feature-category">LAPORAN PENGELUARAN</span>
					<h2>Ringkasan pengeluaran dan ekspor data untuk pembukuan.</h2>
					<p>
						Pantau total pengeluaran tim secara menyeluruh tanpa harus menghitung nota satu per satu. Data klaim dapat disaring dan diekspor ke file CSV untuk kebutuhan rekap dan pembukuan.
					</p>
					<ul class="feature-keypoints">
						<li><strong>Ringkasan per periode:</strong> Pantau total klaim yang diajukan dan disetujui dalam rentang waktu tertentu.</li>
						<li><strong>Distribusi kategori:</strong> Lihat porsi pengeluaran untuk makan tim, transportasi dinas, hingga perlengkapan kerja.</li>
						<li><strong>Ekspor CSV rapi:</strong> Unduh seluruh data transaksi lengkap untuk diolah di spreadsheet atau software akuntansi.</li>
					</ul>
					<a class="button cta-link" href="/reports">Buka laporan pengeluaran <span aria-hidden="true">↗</span></a>
				</div>
				<div class="feature-preview-card">
					<div class="card-caption">CONTOH RINGKASAN PENGELUARAN</div>
					<div class="analytics-mockup">
						<div class="kpi-banner">
							<div class="kpi-item">
								<small>Total Pengeluaran Bulan Ini</small>
								<strong>Rp 38.650.000</strong>
							</div>
							<div class="kpi-item">
								<small>Total Klaim Selesai</small>
								<strong class="highlight-teal">32 Klaim</strong>
							</div>
						</div>
						<div class="distribution-preview">
							<small class="dist-label">Distribusi Kategori Pengeluaran</small>
							<div class="bar-item">
								<div class="bar-labels"><span>Makanan &amp; Minuman</span><span>45%</span></div>
								<div class="progress-bg"><div class="progress-fill" style="width: 45%;"></div></div>
							</div>
							<div class="bar-item">
								<div class="bar-labels"><span>Transportasi Dinas</span><span>30%</span></div>
								<div class="progress-bg"><div class="progress-fill" style="width: 30%;"></div></div>
							</div>
							<div class="bar-item">
								<div class="bar-labels"><span>Perlengkapan Kerja</span><span>25%</span></div>
								<div class="progress-bg"><div class="progress-fill" style="width: 25%;"></div></div>
							</div>
						</div>
						<div class="export-chip-row">
							<span>Format Ekspor: <strong>File CSV (IDR, UTF-8)</strong></span>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Bottom Call-to-Action -->
		<section use:reveal class="closing-stage scroll-reveal">
			<TeraBrandRibbon dark />
			<div class="closing-box">
				<h2>Mulai rapikan pengeluaran kerja.</h2>
				<p>Coba ajukan nota pertamamu atau masuk ke ruang kerja untuk melihat alur pemeriksaannya.</p>
				<div class="closing-btn-row">
					<a class="button main-button" href="/pengajuan">Mulai pengajuan klaim <span aria-hidden="true">→</span></a>
					<a class="button secondary-button" href="/login">Masuk ke akun</a>
				</div>
			</div>
		</section>
	</main>

	<!-- Footer (100% Identical with Homepage) -->
	<footer class="landing-footer">
		<div class="footer-shell">
			<div class="footer-grid">
				<div class="footer-brand">
					<a class="wordmark" href="/" aria-label="Tera, beranda">
						<img src="/logo.webp" width="32" height="32" alt="" />
						<span>Tera</span>
					</a>
					<p class="footer-summary">
						AI Expense Agent untuk membaca nota, mencocokkan kebijakan, dan menata klaim pengeluaran kerja dalam satu alur yang jelas.
					</p>
					<div class="footer-callout">
						<span class="callout-copy">Siap mencoba dengan notamu?</span>
						<a class="footer-pill" href="/pengajuan">Buka aplikasi <span aria-hidden="true">→</span></a>
					</div>
				</div>
				<nav class="footer-nav" aria-label="Tautan footer">
					<div class="footer-col">
						<p class="footer-heading">Aplikasi</p>
						<a href="/pengajuan"><span>Pengajuan baru</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/riwayat"><span>Riwayat klaim</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/reviews"><span>Antrean review</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/reports"><span>Laporan &amp; CSV</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
					</div>
					<div class="footer-col">
						<p class="footer-heading">Telusuri</p>
						<a href="/produk"><span>Eksplorasi produk</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="/#fitur"><span>Cakupan fitur</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="/#cara-kerja"><span>Cara kerja</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="/#untuk-tim"><span>Untuk tim</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="/#faq"><span>Pertanyaan umum</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
					</div>
					<div class="footer-col">
						<p class="footer-heading">Ruang kerja</p>
						<a href="/dashboard"><span>Ringkasan klaim</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/admin/policies"><span>Kebijakan klaim</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/admin/checkpoints"><span>Observabilitas Graph</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
						<a href="/login"><span>Masuk akun</span><span class="footer-link-arrow" aria-hidden="true">↗</span></a>
					</div>
				</nav>
			</div>
			<div class="footer-wordmark-stage" aria-hidden="true">
				<span class="footer-giant-mark"><span>T</span><span>e</span><span>r</span><span>a</span></span>
			</div>
			<div class="footer-bottom">
				<p>Tera · Pengeluaran kerja, lebih tertata.</p>
				<div class="footer-meta-links">
					<span class="footer-pillars">Nota · Kebijakan · Risiko · Keputusan</span>
					<a class="footer-backtop" href="#main-content"><span>Kembali ke atas</span><span class="backtop-icon" aria-hidden="true">↑</span></a>
				</div>
			</div>
		</div>
	</footer>
</div>

<style>
	/* Shared Modern-Minimal Tera Styles matching +page.svelte */
	.landing {
		--nav-offset: 110px;
		display: flow-root;
		color: var(--color-ink);
		background-color: #FAFCFB;
	}
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
		transition: background-color 220ms var(--ease-out), box-shadow 220ms var(--ease-out), border-color 220ms var(--ease-out);
	}
	.navbar-shell.scrolled {
		background: rgb(255 255 255 / .88);
		backdrop-filter: blur(14px);
		border-color: var(--color-border-strong);
		box-shadow: 0 10px 30px rgb(0 45 40 / .11);
	}
	.landing-header {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-6);
		min-height: 76px;
		width: 100%;
		padding: 12px 18px;
	}
	.wordmark {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-ink);
		text-decoration: none;
		flex-shrink: 0;
	}
	.wordmark span {
		font: 800 28px var(--font-display);
		letter-spacing: -1.5px;
	}
	.wordmark img {
		object-fit: contain;
	}
	.landing-header nav, .nav-links {
		display: flex;
		align-items: center;
		gap: var(--space-7, 28px);
	}
	.landing-header nav a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		padding: var(--space-3) 0;
		color: var(--color-ink);
		font-size: 14px;
		font-weight: 500;
		text-decoration: none;
		border-radius: 0;
		white-space: nowrap;
	}
	.landing-header nav a:hover {
		color: var(--color-primary);
		background: transparent;
	}
	.product-trigger {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		gap: 6px;
		min-height: 44px;
		padding: 8px 10px;
		border: 0;
		background: transparent;
		color: var(--color-ink);
		font-size: 14px;
		font-weight: 500;
		border-radius: 8px;
		cursor: pointer;
	}
	.product-trigger:hover, .product-trigger.selected {
		background: var(--color-light);
		color: var(--color-primary-dark);
	}
	.product-trigger svg {
		transition: transform 220ms ease;
	}
	.product-trigger.selected svg {
		transform: rotate(180deg);
	}
	.product-panel {
		position: absolute;
		top: calc(100% + 12px);
		left: 50%;
		width: min(760px, calc(100vw - 64px));
		transform: translate(-50%, -8px);
		opacity: 0;
		visibility: hidden;
		transition: opacity 180ms ease, transform 220ms ease, visibility 220ms;
	}
	.product-panel.shown {
		opacity: 1;
		visibility: visible;
		transform: translate(-50%, 0);
	}
	.product-panel::before {
		content: '';
		position: absolute;
		top: -20px;
		left: 0;
		right: 0;
		height: 20px;
	}
	.product-panel-content {
		display: grid;
		grid-template-columns: .85fr 1.15fr;
		padding: 8px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 16px;
		box-shadow: 0 20px 48px rgb(0 45 40 / .14);
	}
	.landing-header nav .product-spotlight {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		min-height: 300px;
		overflow: hidden;
		padding: 24px;
		background: var(--color-light);
		border-radius: 10px;
		white-space: normal;
	}
	.landing-header nav .product-spotlight:hover {
		background: #d8eee6;
	}
	.menu-eyebrow {
		font-size: 10px;
		letter-spacing: .12em;
		font-weight: 600;
		color: var(--color-primary);
	}
	.product-spotlight > strong {
		margin-top: 16px;
		font-size: 29px;
		letter-spacing: -.05em;
		line-height: 1.15;
		position: relative;
		z-index: 1;
	}
	.spotlight-description {
		max-width: 180px;
		font-size: 12px;
		line-height: 1.7;
		margin-top: 12px;
		position: relative;
		z-index: 1;
	}
	.product-spotlight img {
		position: absolute;
		width: 180px;
		height: auto;
		right: -40px;
		bottom: -48px;
		transform: rotate(-12deg);
		opacity: .6;
	}
	.spotlight-link {
		display: flex;
		gap: 16px;
		margin-top: auto;
		padding-top: 40px;
		font-size: 12px;
		font-weight: 600;
		position: relative;
		z-index: 1;
	}
	.product-shortcuts {
		display: grid;
		padding: 6px 8px;
	}
	.landing-header nav .product-shortcuts a {
		padding: 12px;
		gap: 12px;
		border-radius: 8px;
		white-space: normal;
	}
	.landing-header nav .product-shortcuts a:hover {
		background: var(--color-light);
	}
	.shortcut-symbol {
		display: grid;
		place-items: center;
		width: 36px;
		height: 36px;
		flex: 0 0 36px;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		color: var(--color-primary);
		font-size: 20px;
	}
	.product-shortcuts strong {
		display: block;
		font-size: 13px;
		font-weight: 600;
	}
	.product-shortcuts small {
		display: block;
		margin-top: 5px;
		font-size: 11px;
		line-height: 1.5;
		color: var(--color-text-muted);
	}
	.shortcut-arrow {
		margin-left: auto;
		color: var(--color-primary);
	}
	.landing-header nav .product-shortcuts a > span:nth-child(2) {
		display: block;
		flex: 1;
		min-width: 0;
	}
	.product-panel-footer {
		grid-column: 1 / -1;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin: 8px 8px 0;
		padding: 8px;
		border-top: 1px solid var(--color-border);
		font-size: 11px;
		color: var(--color-text-muted);
	}
	.nav-actions {
		display: flex;
		gap: var(--space-2);
	}
	.nav-cta {
		font-size: var(--text-sm);
		border-radius: var(--radius-pill);
		background: var(--color-ink);
		border-color: var(--color-ink);
		gap: var(--space-3);
		color: white;
		text-decoration: none;
		padding: 10px 18px;
		font-weight: 600;
		display: inline-flex;
		align-items: center;
	}
	.menu-toggle {
		display: none;
		width: 44px;
		height: 44px;
		padding: 0;
		align-items: center;
		justify-content: center;
		color: var(--color-ink);
		border-color: var(--color-border);
		background: transparent;
		cursor: pointer;
	}
	.menu-toggle svg path {
		stroke: currentColor;
		stroke-width: 1.7;
		stroke-linecap: round;
		transform-origin: 12px 12px;
		transition: transform 220ms ease, opacity 150ms ease;
	}
	.opened .hamburger-top {
		transform: translateY(6px) rotate(45deg);
		transform-origin: 12px 6px;
	}
	.opened .hamburger-middle {
		opacity: 0;
	}
	.opened .hamburger-bottom {
		transform: translateY(-6px) rotate(-45deg);
		transform-origin: 12px 18px;
	}

	/* Hero Page Stage */
	.hero-stage {
		position: relative;
		overflow: hidden;
		padding: 80px 24px 60px;
		text-align: center;
	}
	.hero-copy-centered {
		width: min(860px, calc(100% - 48px));
		margin: 0 auto;
	}
	.eyebrow-tag {
		display: inline-block;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: .12em;
		color: var(--color-primary);
		background: var(--color-light);
		padding: 6px 14px;
		border-radius: 999px;
		margin-bottom: 20px;
	}
	.hero-copy-centered h1 {
		font-size: clamp(36px, 5vw, 56px);
		font-weight: 800;
		letter-spacing: -.04em;
		line-height: 1.1;
		color: var(--color-ink);
		margin-bottom: 18px;
	}
	.hero-copy-centered h1 span {
		color: var(--color-primary);
	}
	.hero-copy-centered p {
		font-size: clamp(16px, 2vw, 19px);
		line-height: 1.6;
		color: var(--color-text-muted);
		max-width: 640px;
		margin: 0 auto;
	}

	/* Feature Blocks */
	.feature-block {
		width: min(1040px, calc(100% - 48px));
		margin: 100px auto;
		scroll-margin-top: 130px;
	}
	.feature-content {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 60px;
		align-items: center;
	}
	.feature-content.reverse {
		grid-template-columns: 1fr 1fr;
		direction: rtl;
	}
	.feature-content.reverse > * {
		direction: ltr;
	}
	.feature-number {
		display: block;
		font: 800 36px var(--font-display);
		color: var(--color-primary);
		letter-spacing: -0.04em;
		line-height: 1;
		margin-bottom: 6px;
	}
	.feature-category {
		display: block;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: .1em;
		color: var(--color-text-muted);
		margin-bottom: 14px;
	}
	.feature-text h2 {
		font-size: clamp(26px, 3.2vw, 34px);
		font-weight: 800;
		line-height: 1.25;
		letter-spacing: -.03em;
		margin-bottom: 16px;
		color: var(--color-ink);
	}
	.feature-text p {
		font-size: 15px;
		line-height: 1.7;
		color: var(--color-text-muted);
		margin-bottom: 24px;
	}
	.feature-keypoints {
		list-style: none;
		padding: 0;
		margin: 0 0 32px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.feature-keypoints li {
		font-size: 14px;
		line-height: 1.6;
		color: var(--color-ink);
		padding-left: 20px;
		position: relative;
	}
	.feature-keypoints li::before {
		content: '✓';
		position: absolute;
		left: 0;
		top: 1px;
		font-weight: 800;
		color: var(--color-primary);
	}
	.feature-keypoints strong {
		color: var(--color-ink);
	}
	.cta-link {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		background: var(--color-primary);
		color: white;
		padding: 10px 22px;
		border-radius: var(--radius-pill, 999px);
		font-weight: 600;
		font-size: 14px;
		text-decoration: none;
		transition: background 180ms ease;
	}
	.cta-link:hover {
		background: var(--color-primary-dark);
	}

	/* Clean Visual Mockups */
	.feature-preview-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 20px;
		padding: 24px;
		box-shadow: 0 16px 40px rgb(0 45 40 / .08);
	}
	.card-caption {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: .08em;
		color: var(--color-primary);
		margin-bottom: 16px;
	}

	/* 1. Receipt Card */
	.receipt-card-mockup {
		background: #FAFCFB;
		border: 1px solid var(--color-border);
		border-radius: 12px;
		padding: 20px;
	}
	.receipt-header-row {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		border-bottom: 1px dashed var(--color-border-strong);
		padding-bottom: 12px;
		margin-bottom: 14px;
	}
	.receipt-vendor {
		display: block;
		font-size: 15px;
		font-weight: 800;
	}
	.receipt-sub {
		display: block;
		font-size: 12px;
		color: var(--color-text-muted);
		margin-top: 2px;
	}
	.status-chip {
		font-size: 11px;
		font-weight: 700;
		padding: 4px 10px;
		border-radius: 999px;
	}
	.status-chip.success {
		background: #DCFCE7;
		color: #166534;
	}
	.receipt-item-table {
		display: flex;
		flex-direction: column;
		gap: 8px;
		font-size: 13px;
	}
	.item-line {
		display: flex;
		justify-content: space-between;
		color: var(--color-ink);
	}
	.total-line {
		border-top: 1px solid var(--color-border);
		padding-top: 10px;
		margin-top: 4px;
		font-weight: 800;
	}
	.total-amount {
		color: var(--color-primary);
		font-size: 15px;
	}
	.policy-eval-box {
		margin-top: 16px;
		background: var(--color-light);
		border-radius: 8px;
		padding: 12px;
		font-size: 12px;
	}
	.policy-status-pill {
		display: flex;
		align-items: center;
		gap: 6px;
		font-weight: 700;
		color: var(--color-primary-dark);
		margin-bottom: 4px;
	}
	.eval-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-primary);
	}
	.policy-eval-box p {
		margin: 0;
		color: var(--color-text-muted);
	}

	/* 2. Timeline Visual */
	.timeline-visual {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.timeline-row {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 10px 14px;
		background: #FAFCFB;
		border: 1px solid var(--color-border);
		border-radius: 10px;
	}
	.timeline-row.active {
		border-color: var(--color-primary);
		background: var(--color-light);
	}
	.step-badge {
		display: grid;
		place-items: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--color-border);
		font-size: 12px;
		font-weight: 800;
		color: var(--color-ink);
		flex-shrink: 0;
	}
	.timeline-row.passed .step-badge {
		background: var(--color-mint);
		color: var(--color-primary-dark);
	}
	.timeline-row.active .step-badge {
		background: var(--color-primary);
		color: white;
	}
	.step-info strong {
		display: block;
		font-size: 13px;
		color: var(--color-ink);
	}
	.step-info small {
		display: block;
		font-size: 11px;
		color: var(--color-text-muted);
	}

	/* 3. Reviewer Card */
	.reviewer-card-mockup {
		background: #FAFCFB;
		border: 1px solid var(--color-border);
		border-radius: 12px;
		padding: 20px;
	}
	.claim-topbar {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		border-bottom: 1px solid var(--color-border);
		padding-bottom: 12px;
		margin-bottom: 14px;
	}
	.claim-tag {
		font-size: 11px;
		font-weight: 700;
		color: var(--color-primary);
	}
	.claim-topbar h4 {
		margin: 4px 0 0;
		font-size: 15px;
		font-weight: 800;
	}
	.anomaly-pill {
		font-size: 11px;
		padding: 4px 10px;
		border-radius: 999px;
	}
	.anomaly-pill.high {
		background: #FEE2E2;
		color: #991B1B;
	}
	.review-details-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
		margin-bottom: 14px;
	}
	.detail-box {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 10px 12px;
	}
	.detail-box small {
		display: block;
		font-size: 10px;
		color: var(--color-text-muted);
		text-transform: uppercase;
	}
	.detail-box span, .detail-box strong {
		font-size: 13px;
		display: block;
		margin-top: 2px;
	}
	.highlight-val {
		color: var(--color-primary-dark);
		font-weight: 800;
	}
	.signals-summary {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 14px;
	}
	.sig-pill {
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 12px;
	}
	.sig-pill.warning {
		background: #FEF3C7;
		color: #92400E;
		border: 1px solid #FDE68A;
	}
	.sig-pill.clean {
		background: #ECFDF5;
		color: #065F46;
		border: 1px solid #A7F3D0;
	}
	.review-action-hint {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		padding-top: 10px;
		border-top: 1px dashed var(--color-border);
		color: var(--color-text-muted);
	}
	.review-action-hint strong {
		color: var(--color-ink);
	}

	/* 4. Analytics Mockup */
	.analytics-mockup {
		background: #FAFCFB;
		border: 1px solid var(--color-border);
		border-radius: 12px;
		padding: 20px;
	}
	.kpi-banner {
		display: grid;
		grid-template-columns: 1.2fr 1fr;
		gap: 12px;
		margin-bottom: 18px;
	}
	.kpi-item {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 12px;
	}
	.kpi-item small {
		display: block;
		font-size: 11px;
		color: var(--color-text-muted);
		margin-bottom: 4px;
	}
	.kpi-item strong {
		font-size: 18px;
		font-weight: 800;
		color: var(--color-ink);
	}
	.highlight-teal {
		color: var(--color-primary) !important;
	}
	.distribution-preview {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 14px;
		margin-bottom: 14px;
	}
	.dist-label {
		display: block;
		font-size: 11px;
		font-weight: 700;
		color: var(--color-text-muted);
		margin-bottom: 10px;
		text-transform: uppercase;
		letter-spacing: .05em;
	}
	.bar-item {
		margin-bottom: 8px;
	}
	.bar-labels {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		margin-bottom: 3px;
	}
	.progress-bg {
		height: 6px;
		background: var(--color-light);
		border-radius: 4px;
		overflow: hidden;
	}
	.progress-fill {
		height: 100%;
		background: var(--color-primary);
		border-radius: 4px;
	}
	.export-chip-row {
		font-size: 11px;
		color: var(--color-text-muted);
		text-align: right;
	}
	.export-chip-row strong {
		color: var(--color-primary);
	}

	/* Closing Stage */
	.closing-stage {
		position: relative;
		overflow: hidden;
		width: min(1040px, calc(100% - 48px));
		margin: 100px auto 80px;
		background: var(--color-ink);
		color: white;
		padding: 70px 32px;
		border-radius: 24px;
		text-align: center;
		box-shadow: 0 20px 48px rgb(0 45 40 / .16);
	}
	.closing-box h2 {
		font-size: clamp(28px, 4vw, 42px);
		font-weight: 800;
		letter-spacing: -0.03em;
		margin-bottom: 12px;
	}
	.closing-box p {
		font-size: 16px;
		color: var(--color-mint);
		max-width: 540px;
		margin: 0 auto 32px;
		line-height: 1.6;
	}
	.closing-btn-row {
		display: flex;
		justify-content: center;
		gap: 14px;
		flex-wrap: wrap;
	}
	.main-button {
		background: var(--color-mint);
		color: var(--color-primary-dark);
		padding: 12px 26px;
		border-radius: 999px;
		font-weight: 700;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.main-button:hover {
		background: white;
	}
	.secondary-button {
		background: transparent;
		color: white;
		border: 1px solid rgba(255, 255, 255, .4);
		padding: 12px 26px;
		border-radius: 999px;
		font-weight: 600;
		text-decoration: none;
	}
	.secondary-button:hover {
		border-color: white;
		background: rgba(255, 255, 255, .08);
	}

	/* Footer Styles */
	.landing-footer {
		width: min(1120px, calc(100% - 64px));
		margin-inline: auto;
		padding: 40px 0 32px;
		border-top: 1px solid var(--color-border);
	}
	.footer-shell {
		width: 100%;
	}
	.footer-grid {
		display: grid;
		grid-template-columns: 1.2fr 2fr;
		gap: 48px;
		padding-bottom: 40px;
	}
	.footer-brand {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	.footer-summary {
		font-size: 13px;
		line-height: 1.6;
		color: var(--color-text-muted);
		max-width: 320px;
	}
	.footer-callout {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 8px;
	}
	.callout-copy {
		font-size: 12px;
		font-weight: 600;
		color: var(--color-ink);
	}
	.footer-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--color-light);
		color: var(--color-primary-dark);
		padding: 8px 16px;
		border-radius: 999px;
		font-size: 12px;
		font-weight: 700;
		text-decoration: none;
		width: fit-content;
	}
	.footer-nav {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 24px;
	}
	.footer-heading {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: .08em;
		text-transform: uppercase;
		color: var(--color-primary);
		margin-bottom: 16px;
	}
	.footer-col a {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 0;
		font-size: 13px;
		color: var(--color-ink);
		text-decoration: none;
	}
	.footer-col a:hover {
		color: var(--color-primary);
	}
	.footer-link-arrow {
		font-size: 12px;
		color: var(--color-primary);
	}
	.footer-wordmark-stage {
		border-top: 1px solid var(--color-border);
		padding: 24px 0;
		overflow: hidden;
	}
	.footer-giant-mark {
		display: flex;
		justify-content: space-between;
		font: 800 84px var(--font-display);
		color: var(--color-light);
		line-height: .9;
		letter-spacing: -.06em;
		user-select: none;
	}
	.footer-bottom {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-top: 16px;
		font-size: 12px;
		color: var(--color-text-muted);
		flex-wrap: wrap;
		gap: 16px;
	}
	.footer-meta-links {
		display: flex;
		align-items: center;
		gap: 20px;
	}
	.footer-pillars {
		color: var(--color-primary);
		font-weight: 600;
	}
	.footer-backtop {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--color-ink);
		text-decoration: none;
		font-weight: 600;
	}

	/* Responsive */
	@media (max-width: 960px) {
		.landing { --nav-offset: 106px; }
		.landing-header { min-height: 72px; flex-wrap: wrap; gap: var(--space-3); position: relative; z-index: 10; }
		.landing-header nav { position: absolute; top: calc(100% - 4px); left: 0; display: grid; grid-template-rows: 0fr; align-items: stretch; width: 100%; padding: 0 var(--space-5); gap: 0; background: var(--color-surface); border-radius: var(--radius-md); box-shadow: 0 14px 28px rgb(0 45 40 / .1); visibility: hidden; transition: grid-template-rows 240ms ease, visibility 240ms; }
		.landing-header nav.expanded { grid-template-rows: 1fr; visibility: visible; }
		.nav-links { min-height: 0; width: 100%; overflow: hidden; display: flex; flex-direction: column; align-items: stretch; gap: 0; }
		.landing-header nav a { justify-content: flex-start; padding-block: var(--space-3); border-top: 1px solid var(--color-border); }
		.product-trigger { width: 100%; flex: 0 0 auto; border-top: 1px solid var(--color-border); border-radius: 0; padding: 12px 0; }
		.product-panel { position: static; width: 100%; max-height: 0; transform: none; overflow: hidden; flex: 0 0 auto; }
		.product-panel.shown { max-height: 540px; transform: none; }
		.product-panel-content { display: block; border: 0; box-shadow: none; padding: 0 0 12px; }
		.landing-header nav .product-spotlight, .product-panel-footer { display: none; }
		.product-shortcuts { padding: 0; border-left: 2px solid var(--color-mint); }
		.landing-header nav .product-shortcuts a { border-top: 0; padding: 12px; }
		.landing-header nav { max-height: calc(100dvh - 112px); overflow-y: auto; }
		.menu-toggle { display: inline-flex; }
		.feature-content, .feature-content.reverse {
			grid-template-columns: 1fr;
			gap: 36px;
			direction: ltr;
		}
		.footer-grid {
			grid-template-columns: 1fr;
			gap: 32px;
		}
		.footer-giant-mark {
			font-size: 48px;
		}
	}
</style>
