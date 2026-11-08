<script lang="ts">
	import TeraReceiptArtwork from '$lib/components/TeraReceiptArtwork.svelte';
	import TeraBrandRibbon from '$lib/components/TeraBrandRibbon.svelte';
	import { reveal } from '$lib/actions/reveal';
	let mobileMenu = $state(false);
	let productMenu = $state(false);
	let productButton = $state<HTMLButtonElement>();
	let headerElement = $state<HTMLElement>();
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
	let menuButton = $state<HTMLButtonElement>();
	let activeStep = $state(0);
	let scrolled = $state(false);
	const workflow = [
		{ title: 'Nota dibaca', description: 'Vendor, tanggal, dan nominal diambil dari nota.', label: 'Hasil pembacaan', detail: 'Informasi penting terkumpul dalam satu klaim.' },
		{ title: 'Kebijakan dicocokkan', description: 'Pengeluaran diperiksa terhadap kebijakan perusahaan.', label: 'Pemeriksaan kebijakan', detail: 'Ketentuan dan batas pengeluaran menjadi dasar penilaian.' },
		{ title: 'Risiko diperiksa', description: 'Duplikat dan indikasi anomali ikut diperiksa.', label: 'Pemeriksaan risiko', detail: 'Temuan disimpan agar bisa ditinjau bersama buktinya.' },
		{ title: 'Tindak lanjut ditentukan', description: 'Klaim diputuskan, diklarifikasi, atau diteruskan ke reviewer.', label: 'Tindak lanjut', detail: 'Tim dapat melihat alasan keputusan dan jejak pemeriksaan.' }
	];
	const selected = $derived(workflow[activeStep]);
	function toggleFaq(event: MouseEvent) {
		const summary = event.currentTarget as HTMLElement;
		const details = summary.parentElement as HTMLDetailsElement;
		event.preventDefault();
		if (details.open) {
			details.classList.add('closing-faq');
			setTimeout(() => {
				details.open = false;
				details.classList.remove('closing-faq');
			}, 240);
		} else {
			details.open = true;
		}
	}
</script>

<svelte:head>
	<title>Tera · AI Expense Agent untuk tim modern</title>
	<meta name="description" content="Tera membantu membaca nota, memeriksa kebijakan, dan menata proses reimbursement. Ajukan klaim dan ikuti setiap langkah pemeriksaannya." />
</svelte:head>

<svelte:window onscroll={() => { const next = window.scrollY > 16; if (next !== scrolled) scrolled = next; }} onpointerdown={(event) => { if (event.target instanceof Node && !headerElement?.contains(event.target)) closeMenus(); }} onkeydown={(event) => { if (event.key === 'Escape') { if (productMenu) { productMenu = false; productButton?.focus(); } else if (mobileMenu) { mobileMenu = false; menuButton?.focus(); } } }} />

<div class="landing">
	<div class="navbar-shell" class:scrolled>
	<header bind:this={headerElement} class="landing-header" onfocusout={(event) => { if (event.relatedTarget instanceof Node && !headerElement?.contains(event.relatedTarget)) productMenu = false; }}>
		<a class="wordmark" href="/" aria-label="Tera, beranda"><img src="/logo.webp" alt="" width="36" height="36" /><span>Tera</span></a>
		<nav class:expanded={mobileMenu} id="landing-nav" aria-label="Navigasi beranda">
			<div class="nav-links">
			<button bind:this={productButton} type="button" class="product-trigger" class:selected={productMenu} aria-expanded={productMenu} aria-controls="product-panel" onmouseenter={openProductMenu} onmouseleave={scheduleCloseProductMenu} onclick={toggleProductMenu}>Produk <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m4 6 4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg></button>
			<div class="product-panel" class:shown={productMenu} id="product-panel" role="region" aria-label="Menu produk" inert={!productMenu} onmouseenter={openProductMenu} onmouseleave={scheduleCloseProductMenu}>
				<div class="product-panel-content">
					<a class="product-spotlight" href="/produk" onclick={closeMenus}><span class="menu-eyebrow">KENALI TERA</span><strong>Dari nota<br />ke keputusan.</strong><span class="spotlight-description">Lihat bagaimana Tera memeriksa pengeluaran kerja.</span><img src="/brand/tera-receipt-curved.png" alt="" width="1280" height="1280" /><span class="spotlight-link">Jelajahi fitur lengkap <span aria-hidden="true">↗</span></span></a>
					<div class="product-shortcuts">
						<a href="/produk#pengajuan" onclick={closeMenus}><span class="shortcut-symbol" aria-hidden="true">↥</span><span><strong>Ajukan klaim</strong><small>Unggah nota dan mulai pemeriksaan.</small></span><span class="shortcut-arrow" aria-hidden="true">↗</span></a>
						<a href="/produk#riwayat" onclick={closeMenus}><span class="shortcut-symbol" aria-hidden="true">≡</span><span><strong>Riwayat pengajuan</strong><small>Ikuti status dan jejak setiap klaim.</small></span><span class="shortcut-arrow" aria-hidden="true">↗</span></a>
						<a href="/produk#review" onclick={closeMenus}><span class="shortcut-symbol" aria-hidden="true">✓</span><span><strong>Review klaim</strong><small>Tinjau bukti dan tentukan tindak lanjut.</small></span><span class="shortcut-arrow" aria-hidden="true">↗</span></a>
						<a href="/produk#laporan" onclick={closeMenus}><span class="shortcut-symbol" aria-hidden="true">↗</span><span><strong>Laporan pengeluaran</strong><small>Lihat ringkasan dan ekspor data klaim.</small></span><span class="shortcut-arrow" aria-hidden="true">↗</span></a>
					</div>
					<div class="product-panel-footer"><span>Satu alur untuk karyawan dan finance.</span><a href="#untuk-tim" onclick={closeMenus}>Tera untuk tim <span aria-hidden="true">→</span></a></div>
				</div>
			</div>
			<a href="#fitur" onclick={closeMenus}>Fitur</a>
			<a href="#cara-kerja" onclick={closeMenus}>Cara kerja</a>
			<a href="#untuk-tim" onclick={closeMenus}>Untuk tim</a>
			<a href="#faq" onclick={closeMenus}>FAQ</a>
			</div>
		</nav>
		<div class="nav-actions">
			<a class="button nav-cta" href="/pengajuan">Buka aplikasi <span aria-hidden="true">↗</span></a>
			<button bind:this={menuButton} class="menu-toggle secondary" class:opened={mobileMenu} type="button" aria-label={mobileMenu ? 'Tutup navigasi' : 'Buka navigasi'} aria-expanded={mobileMenu} aria-controls="landing-nav" onclick={() => { mobileMenu = !mobileMenu; productMenu = false; }}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path class="hamburger-top" d="M4 6h16" /><path class="hamburger-middle" d="M4 12h16" /><path class="hamburger-bottom" d="M4 18h16" /></svg></button>
		</div>
	</header>
	</div>

	<main id="main-content" tabindex="-1">
		<div class="hero-stage" id="produk">
		<TeraBrandRibbon />
		<section class="hero" aria-labelledby="hero-title">
			<div class="hero-copy">
				<h1 id="hero-title">AI Expense<br />Agent untuk<br /><span>Tim Modern.</span></h1>
				<p>Dari nota hingga keputusan klaim. Tera membantu membaca, memeriksa, dan menata pengeluaran kerja dalam satu alur.</p>
				<div class="hero-actions"><a class="button" href="/pengajuan">Ajukan klaim <span aria-hidden="true">→</span></a><a class="hero-secondary" href="#cara-kerja"><span class="play-icon" aria-hidden="true">▶</span>Lihat alurnya</a></div>
				<p class="hero-note">Kirim nota. Ikuti prosesnya. Lanjutkan pekerjaan.</p>
			</div>
			<TeraReceiptArtwork />
		</section>
		</div>

		<div use:reveal class="capability-line scroll-reveal" id="fitur" aria-label="Cakupan Tera"><span>Pembacaan nota</span><span>Validasi kebijakan</span><span>Pemeriksaan duplikat</span><span>Jejak keputusan</span></div>

		<section use:reveal class="workflow-section scroll-reveal" id="cara-kerja" aria-labelledby="workflow-title">
			<div class="section-intro"><h2 id="workflow-title">Bukan sekadar<br />menyimpan nota.</h2><p>Setiap pengajuan punya alur pemeriksaan. Kamu bisa melihat apa yang dibaca, apa yang perlu diperbaiki, dan mengapa sebuah keputusan diambil.</p></div>
			<div class="workflow-layout">
				<div class="workflow-controls" aria-label="Jelajahi alur pemeriksaan">
					{#each workflow as step, i}
						<button type="button" class:chosen={activeStep === i} aria-pressed={activeStep === i} aria-controls="workflow-detail" onclick={() => (activeStep = i)}><span class="step-number" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span><span><strong>{step.title}</strong><span class="step-description">{step.description}</span></span><span class="step-select" aria-hidden="true">{activeStep === i ? '−' : '+'}</span></button>
					{/each}
				</div>
				<div class="workflow-detail" id="workflow-detail" aria-live="polite">
					{#key activeStep}
						<div class="workflow-detail-body">
							<span class="detail-position">Langkah {activeStep + 1} dari {workflow.length}</span><h3>{selected.label}</h3><p>{selected.detail}</p>
							{#if activeStep === 0}
								<dl class="extraction-example"><div><dt>Vendor</dt><dd>Terbaca dari nota</dd></div><div><dt>Tanggal</dt><dd>Tanggal transaksi</dd></div><div><dt>Nominal</dt><dd>Total pengeluaran</dd></div><div><dt>Kategori</dt><dd>Jenis pengeluaran</dd></div></dl>
							{:else if activeStep === 1}
								<ul class="detail-list"><li>Kelengkapan data nota</li><li>Ketentuan kategori pengeluaran</li><li>Batas nominal sesuai kebijakan</li></ul>
							{:else if activeStep === 2}
								<ul class="detail-list"><li>Kecocokan dengan pengajuan sebelumnya</li><li>Indikasi pengeluaran tidak wajar</li><li>Bukti dan alasan setiap temuan</li></ul>
							{:else}
								<ul class="detail-list"><li>Keputusan beserta alasannya</li><li>Klarifikasi ketika informasi kurang</li><li>Review manusia saat perlu ditinjau</li></ul>
							{/if}
						</div>
					{/key}
					<a class="quiet-link" href="/pengajuan">Coba dengan notamu <span aria-hidden="true">↗</span></a>
				</div>
			</div>
		</section>

		<section use:reveal class="team-section scroll-reveal" id="untuk-tim" aria-labelledby="team-title">
			<div class="team-heading"><h2 id="team-title">Tera memeriksa.<br /><span>Tim tetap memegang kendali.</span></h2><p>Satu tempat untuk mengajukan, melengkapi, dan meninjau pengeluaran kerja.</p></div>
			<div class="audience-layout">
				<article class="employee-section"><span class="audience-label">Untuk karyawan</span><h3>Ajukan sekali.<br />Pantau sampai jelas.</h3><p>Unggah foto atau PDF nota, ikuti progres pemeriksaan, dan lengkapi informasi ketika Tera meminta klarifikasi.</p><a class="quiet-link" href="/riwayat">Lihat riwayat klaim <span aria-hidden="true">↗</span></a><div class="employee-note"><span aria-hidden="true">✓</span><p>Nota, hasil pembacaan, dan status pengajuan ada dalam satu klaim.</p></div></article>
				<article class="finance-section"><span class="audience-label">Untuk finance dan reviewer</span><h3>Lihat buktinya.<br />Tentukan tindak lanjutnya.</h3><p>Tinjau klaim yang diteruskan beserta alasan dan sinyal risikonya. Keputusan reviewer ikut tercatat dalam jejak pemeriksaan.</p><a class="quiet-link" href="/reviews">Buka antrean review <span aria-hidden="true">↗</span></a><div class="finance-note"><div><span>Bukti nota</span><strong>Tersimpan bersama klaim</strong></div><div><span>Keputusan</span><strong>Dilengkapi alasan</strong></div><div><span>Pelaporan</span><strong>Dapat diekspor ke CSV</strong></div></div></article>
			</div>
		</section>

		<section use:reveal class="faq-section scroll-reveal" id="faq" aria-labelledby="faq-title">
			<div class="faq-intro"><h2 id="faq-title">Sebelum mengirim<br />nota pertamamu.</h2><p>Beberapa hal tentang pengajuan dan pemeriksaan di Tera.</p><a class="quiet-link" href="/pengajuan">Mulai pengajuan <span aria-hidden="true">↗</span></a></div>
			<div class="faq-list">
				<details><summary onclick={toggleFaq}>Apa yang diperiksa Tera?</summary><div class="faq-answer"><div><p>Tera membaca informasi pada nota, mencocokkan pengeluaran dengan kebijakan perusahaan, serta memeriksa duplikat dan indikasi anomali. Hasilnya tersimpan bersama klaim.</p></div></div></details>
				<details><summary onclick={toggleFaq}>Apakah semua klaim langsung disetujui?</summary><div class="faq-answer"><div><p>Hasil pemeriksaan menentukan tindak lanjutnya. Klaim bisa membutuhkan klarifikasi atau diteruskan ke reviewer. Tim tetap bisa melihat alasan keputusan dan bukti pendukungnya.</p></div></div></details>
				<details><summary onclick={toggleFaq}>Bagaimana saya memantau pengajuan?</summary><div class="faq-answer"><div><p>Buka Riwayat di aplikasi, lalu pilih klaim untuk melihat status, hasil pembacaan, dan jejak pemeriksaannya. Jika dibutuhkan, kamu bisa melengkapi informasi melalui klarifikasi.</p></div></div></details>
				<details><summary onclick={toggleFaq}>Apa yang bisa dilakukan tim finance?</summary><div class="faq-answer"><div><p>Tim finance dapat meninjau antrean review, melihat nota dan temuan pemeriksaan, lalu mencatat keputusan. Ringkasan pengeluaran juga tersedia melalui laporan dan ekspor CSV.</p></div></div></details>
			</div>
		</section>

		<section use:reveal class="closing scroll-reveal" aria-labelledby="closing-title">
			<TeraBrandRibbon dark />
			<div class="closing-copy"><img src="/logo.webp" width="40" height="40" alt="" /><h2 id="closing-title">Ubah nota.<br /><span>Rapikan pengeluaran.</span></h2><p>Tera membantu memeriksa detailnya,<br />agar kamu bisa fokus ke pekerjaan berikutnya.</p><a class="button closing-button" href="/pengajuan">Ajukan klaim pertamamu <span aria-hidden="true">→</span></a></div>
			<TeraReceiptArtwork compact />
		</section>
	</main>
	<footer use:reveal class="landing-footer scroll-reveal">
		<div class="footer-shell">
			<div class="footer-grid">
				<div class="footer-brand">
					<a class="wordmark" href="/" aria-label="Tera, beranda"><img src="/logo.webp" width="32" height="32" alt="" /><span>Tera</span></a>
					<p class="footer-summary">AI Expense Agent untuk membaca nota, mencocokkan kebijakan, dan menata klaim pengeluaran kerja dalam satu alur yang jelas.</p>
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
						<a href="#fitur"><span>Cakupan fitur</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="#cara-kerja"><span>Cara kerja</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="#untuk-tim"><span>Untuk tim</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
						<a href="#faq"><span>Pertanyaan umum</span><span class="footer-link-arrow" aria-hidden="true">→</span></a>
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
					<a class="footer-backtop" href="#produk"><span>Kembali ke atas</span><span class="backtop-icon" aria-hidden="true">↑</span></a>
				</div>
			</div>
		</div>
	</footer>
</div>

<style>
	/* Hallmark · genre: modern-minimal · macrostructure: Marquee Hero · design-system: DESIGN.md · enrichment: receipt workflow · nav: N9 · footer: Ft2 */
	.landing { --nav-offset: 110px; display: flow-root; color: var(--color-ink); }
	.navbar-shell { position: sticky; top: 16px; z-index: 50; width: min(1040px, calc(100% - 48px)); margin: 16px auto; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 20px; box-shadow: 0 4px 20px rgb(0 45 40 / .07); transition: background-color 220ms var(--ease-out), box-shadow 220ms var(--ease-out), border-color 220ms var(--ease-out); }
	.navbar-shell.scrolled { background: rgb(255 255 255 / .88); backdrop-filter: blur(14px); border-color: var(--color-border-strong); box-shadow: 0 10px 30px rgb(0 45 40 / .11); }
	.landing :is(#produk, #fitur, #cara-kerja, #untuk-tim, #faq) { scroll-margin-top: 124px; }
	.landing-header, .hero, .capability-line, .workflow-section, .team-section, .faq-section, .closing, .landing-footer { width: min(1120px, calc(100% - 64px)); margin-inline: auto; }
	.landing-header { position: relative; display: flex; align-items: center; justify-content: space-between; gap: var(--space-6); min-height: 76px; width: 100%; padding: 12px 18px; }
	.wordmark { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--color-ink); text-decoration: none; flex-shrink: 0; }
	.wordmark span { font: 800 28px var(--font-display); letter-spacing: -1.5px; }
	.wordmark img { object-fit: contain; }
	.landing-header nav, .nav-links { display: flex; align-items: center; gap: var(--space-7, 28px); }
	.landing-header nav a { display: inline-flex; align-items: center; min-height: 44px; padding: var(--space-3) 0; color: var(--color-ink); font-size: 14px; font-weight: 500; text-decoration: none; border-radius: 0; white-space: nowrap; }
	.landing-header nav a:hover { color: var(--color-primary); background: transparent; }
	.product-trigger { display: inline-flex; align-items: center; justify-content: space-between; gap: 6px; min-height: 44px; padding: 8px 10px; border: 0; background: transparent; color: var(--color-ink); font-size: 14px; font-weight: 500; border-radius: 8px; }
	.product-trigger:hover, .product-trigger.selected { background: var(--color-light); color: var(--color-primary-dark); }
	.product-trigger svg { transition: transform 220ms ease; }
	.product-trigger.selected svg { transform: rotate(180deg); }
	.product-panel { position: absolute; top: calc(100% + 12px); left: 50%; width: min(760px, calc(100vw - 64px)); transform: translate(-50%, -8px); opacity: 0; visibility: hidden; transition: opacity 180ms ease, transform 220ms ease, visibility 220ms; }
	.product-panel.shown { opacity: 1; visibility: visible; transform: translate(-50%, 0); }
	.product-panel::before { content: ''; position: absolute; top: -20px; left: 0; right: 0; height: 20px; }
	.product-panel-content { display: grid; grid-template-columns: .85fr 1.15fr; padding: 8px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 16px; box-shadow: 0 20px 48px rgb(0 45 40 / .14); }
	.landing-header nav .product-spotlight { position: relative; display: flex; flex-direction: column; align-items: flex-start; min-height: 300px; overflow: hidden; padding: 24px; background: var(--color-light); border-radius: 10px; white-space: normal; }
	.landing-header nav .product-spotlight:hover { background: #d8eee6; }
	.menu-eyebrow { font-size: 10px; letter-spacing: .12em; font-weight: 600; color: var(--color-primary); }
	.product-spotlight > strong { margin-top: 16px; font-size: 29px; letter-spacing: -.05em; line-height: 1.15; position: relative; z-index: 1; }
	.spotlight-description { max-width: 180px; font-size: 12px; line-height: 1.7; margin-top: 12px; position: relative; z-index: 1; }
	.product-spotlight img { position: absolute; width: 180px; height: auto; right: -40px; bottom: -48px; transform: rotate(-12deg); opacity: .6; }
	.landing-header nav .product-spotlight > span { margin-left: 0; }
	.spotlight-link { display: flex; gap: 16px; margin-top: auto; padding-top: 40px; font-size: 12px; font-weight: 600; position: relative; z-index: 1; }
	.product-shortcuts { display: grid; padding: 6px 8px; }
	.landing-header nav .product-shortcuts a { padding: 12px; gap: 12px; border-radius: 8px; white-space: normal; }
	.landing-header nav .product-shortcuts a:hover { background: var(--color-light); }
	.shortcut-symbol { display: grid; place-items: center; width: 36px; height: 36px; flex: 0 0 36px; border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-primary); font-size: 20px; }
	.product-shortcuts strong { display: block; font-size: 13px; font-weight: 600; }
	.product-shortcuts small { display: block; margin-top: 5px; font-size: 11px; line-height: 1.5; color: var(--color-text-muted); }
	.shortcut-arrow { margin-left: auto; color: var(--color-primary); }
	.landing-header nav .product-shortcuts a > span { margin-left: 0; }
	.landing-header nav .product-shortcuts a > span:nth-child(2) { display: block; flex: 1; min-width: 0; }
	.landing-header nav .product-shortcuts a > .shortcut-arrow { display: block; margin-left: auto; }
	.product-panel-footer { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 8px 8px 0; padding: 8px; border-top: 1px solid var(--color-border); font-size: 11px; color: var(--color-text-muted); }
	.landing-header nav .product-panel-footer a { min-height: 36px; padding: 0; gap: 10px; font-size: 11px; font-weight: 600; }
	.nav-actions { display: flex; gap: var(--space-2); }
	.nav-cta { font-size: var(--text-sm); border-radius: var(--radius-pill); background: var(--color-ink); border-color: var(--color-ink); gap: var(--space-3); }
	.menu-toggle { display: none; width: 44px; height: 44px; padding: 0; align-items: center; justify-content: center; color: var(--color-ink); border-color: var(--color-border); background: transparent; }
	.menu-toggle svg path { stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; transform-origin: 12px 12px; transition: transform 220ms ease, opacity 150ms ease; }
	.opened .hamburger-top { transform: translateY(6px) rotate(45deg); transform-origin: 12px 6px; }
	.opened .hamburger-middle { opacity: 0; }
	.opened .hamburger-bottom { transform: translateY(-6px) rotate(-45deg); transform-origin: 12px 18px; }
	@keyframes hero-enter { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
	@keyframes step-enter { from { opacity: 0; transform: translate3d(0, 8px, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }
		/* Multi-directional GPU choreography: pure transform + opacity (no filter:blur repaint) on one silk curve cubic-bezier(.22, 1, .36, 1). */
		.landing { --reveal-spring: cubic-bezier(.22, 1, .36, 1); }
		.capability-line, .capability-line span, .workflow-section .section-intro > *, .workflow-controls button, .workflow-detail, .team-heading, .audience-layout article, .faq-intro, .faq-list details, .closing, .closing-copy, .closing :global(.receipt-artwork), .footer-brand, .footer-col, .footer-giant-mark span { backface-visibility: hidden; will-change: transform, opacity; }
		/* 1. Capability line: horizontal border wipe + staggered pill slide */
		.capability-line { transform-origin: left center; transition: transform 850ms var(--reveal-spring), opacity 850ms var(--reveal-spring); }
		.capability-line span { display: inline-block; transition: opacity 750ms var(--reveal-spring), transform 750ms var(--reveal-spring); }
		.capability-line span:nth-child(2) { transition-delay: 60ms; }
		.capability-line span:nth-child(3) { transition-delay: 120ms; }
		.capability-line span:nth-child(4) { transition-delay: 180ms; }
		.capability-line:global(.awaiting-reveal) { opacity: 0; transform: scaleX(.94); }
		.capability-line:global(.awaiting-reveal) span { opacity: 0; transform: translate3d(-16px, 0, 0); }
		/* 2. Workflow section: intro split (left/right) + steps cascade from left + detail card scale-in from right */
		.workflow-section .section-intro > * { transition: opacity 900ms var(--reveal-spring), transform 900ms var(--reveal-spring); }
		.workflow-section .section-intro > :nth-child(2) { transition-delay: 80ms; }
		.workflow-section:global(.awaiting-reveal) .section-intro > :nth-child(1) { opacity: 0; transform: translate3d(-28px, 14px, 0); }
		.workflow-section:global(.awaiting-reveal) .section-intro > :nth-child(2) { opacity: 0; transform: translate3d(28px, 14px, 0); }
		.workflow-controls button { transition: color 180ms var(--ease-out), padding-left 220ms var(--ease-out), border-color 180ms ease, opacity 800ms var(--reveal-spring), transform 800ms var(--reveal-spring); }
		.workflow-controls button:nth-child(1) { transition-delay: 90ms; }
		.workflow-controls button:nth-child(2) { transition-delay: 155ms; }
		.workflow-controls button:nth-child(3) { transition-delay: 220ms; }
		.workflow-controls button:nth-child(4) { transition-delay: 285ms; }
		.workflow-section:global(.awaiting-reveal) .workflow-controls button { opacity: 0; transform: translate3d(-24px, 10px, 0); }
		.workflow-detail { transition: opacity 950ms 140ms var(--reveal-spring), transform 950ms 140ms var(--reveal-spring); transform-origin: right center; }
		.workflow-section:global(.awaiting-reveal) .workflow-detail { opacity: 0; transform: translate3d(32px, 14px, 0) scale(.96); }
		/* 3. Team section: heading + employee & finance cards converge from opposite sides with subtle tilt */
		.team-heading { transition: opacity 850ms var(--reveal-spring), transform 850ms var(--reveal-spring); }
		.team-section:global(.awaiting-reveal) .team-heading { opacity: 0; transform: translate3d(0, 24px, 0); }
		.audience-layout article { transition: border-color 220ms ease, opacity 950ms var(--reveal-spring), transform 950ms var(--reveal-spring); }
		.audience-layout .employee-section { transition-delay: 90ms; transform-origin: left bottom; }
		.audience-layout .finance-section { transition-delay: 170ms; transform-origin: right bottom; }
		.team-section:global(.awaiting-reveal) .employee-section { opacity: 0; transform: translate3d(-34px, 18px, 0) rotate(-.9deg) scale(.98); }
		.team-section:global(.awaiting-reveal) .finance-section { opacity: 0; transform: translate3d(34px, 18px, 0) rotate(.9deg) scale(.98); }
		/* 4. FAQ section: intro slides from left + FAQ rows cascade in from right */
		.faq-intro { transition: opacity 850ms var(--reveal-spring), transform 850ms var(--reveal-spring); }
		.faq-section:global(.awaiting-reveal) .faq-intro { opacity: 0; transform: translate3d(-28px, 12px, 0); }
		.faq-list details { transition: opacity 800ms var(--reveal-spring), transform 800ms var(--reveal-spring); }
		.faq-list details:nth-child(1) { transition-delay: 70ms; }
		.faq-list details:nth-child(2) { transition-delay: 135ms; }
		.faq-list details:nth-child(3) { transition-delay: 200ms; }
		.faq-list details:nth-child(4) { transition-delay: 265ms; }
		.faq-section:global(.awaiting-reveal) .faq-list details { opacity: 0; transform: translate3d(28px, 10px, 0); }
		/* 5. Closing dark banner: card scales & lifts + copy from left + receipt artwork swoops from right */
		.closing { transition: opacity 900ms var(--reveal-spring), transform 900ms var(--reveal-spring); }
		.closing-copy { transition: opacity 900ms 110ms var(--reveal-spring), transform 900ms 110ms var(--reveal-spring); }
		.closing :global(.receipt-artwork) { transition: opacity 980ms 190ms var(--reveal-spring), transform 980ms 190ms var(--reveal-spring); }
		.closing:global(.awaiting-reveal) { opacity: 0; transform: scale(.955) translate3d(0, 24px, 0); }
		.closing:global(.awaiting-reveal) .closing-copy { opacity: 0; transform: translate3d(-24px, 10px, 0); }
		.closing:global(.awaiting-reveal) :global(.receipt-artwork) { opacity: 0; transform: translate3d(32px, 18px, 0) rotate(2.5deg) scale(.94); }
		/* 6. Footer: columns stagger + giant T-e-r-a letters rise from below the mask */
		.footer-brand, .footer-col { transition: opacity 850ms var(--reveal-spring), transform 850ms var(--reveal-spring); }
		.footer-col:nth-child(1) { transition-delay: 70ms; }
		.footer-col:nth-child(2) { transition-delay: 135ms; }
		.footer-col:nth-child(3) { transition-delay: 200ms; }
		.landing-footer:global(.awaiting-reveal) .footer-brand { opacity: 0; transform: translate3d(-20px, 14px, 0); }
		.landing-footer:global(.awaiting-reveal) .footer-col { opacity: 0; transform: translate3d(0, 20px, 0); }
		.landing-footer:global(.awaiting-reveal) .footer-giant-mark span { opacity: 0; transform: translate3d(0, 65%, 0) scale(.94); }
		.hero-copy > * { animation: hero-enter 650ms cubic-bezier(.22, 1, .36, 1) both; }
		.hero-copy > p { animation-delay: 100ms; }
		.hero-actions { animation-delay: 180ms; }
		.hero-copy > .hero-note { animation-delay: 240ms; }
		.hero :global(.receipt-artwork) { animation: hero-enter 900ms 160ms cubic-bezier(.22, 1, .36, 1) both; }
		.landing a.button, .hero-secondary { transition: transform 180ms ease, background-color 180ms ease; }
		.landing a.button:hover, .hero-secondary:hover { transform: translateY(-2px); }
		.quiet-link span, .nav-cta span { transition: transform 180ms ease; }
		.quiet-link:hover span, .nav-cta:hover span { transform: translate(2px, -2px); }
		.landing a.button:active, .hero-secondary:active { transform: translateY(0) scale(.985); }
		.workflow-detail-body { width: 100%; animation: step-enter 260ms var(--ease-out) both; }
		.workflow-detail-body :is(.extraction-example > div, .detail-list li) { animation: step-enter 280ms var(--ease-out) both; }
		.workflow-detail-body :is(.extraction-example > div, .detail-list li):nth-child(1) { animation-delay: 35ms; }
		.workflow-detail-body :is(.extraction-example > div, .detail-list li):nth-child(2) { animation-delay: 70ms; }
		.workflow-detail-body :is(.extraction-example > div, .detail-list li):nth-child(3) { animation-delay: 105ms; }
		.workflow-detail-body :is(.extraction-example > div, .detail-list li):nth-child(4) { animation-delay: 140ms; }
		.workflow-controls button:hover, .workflow-controls button.chosen { padding-left: 6px; }
		.workflow-controls .step-select { display: inline-block; transition: transform 220ms var(--ease-out), color 180ms ease; }
		.workflow-controls button.chosen .step-select { transform: rotate(180deg); color: var(--color-primary); }
		.audience-layout article:hover { border-top-color: var(--color-primary); }
		.employee-note { transition: transform 240ms var(--ease-out), box-shadow 240ms var(--ease-out); }
		.employee-section:hover .employee-note { transform: translateY(-2px); box-shadow: 0 10px 24px rgb(9 89 81 / .07); }
		.faq-answer { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 260ms var(--ease-out), opacity 220ms ease; }
		.faq-list details[open]:not(:global(.closing-faq)) .faq-answer { grid-template-rows: 1fr; opacity: 1; }
		.faq-answer > div { overflow: hidden; }
		.faq-list summary { transition: color 180ms ease; }
		.faq-list summary:hover { color: var(--color-primary-dark); }
		.faq-list summary::after { display: inline-block; transition: transform 240ms var(--ease-out); }
		.faq-list details[open]:not(:global(.closing-faq)) summary::after { content: '+'; transform: rotate(45deg); }
	.hero-stage { position: relative; isolation: isolate; overflow: clip; margin-top: calc(-1 * var(--nav-offset)); padding-top: var(--nav-offset); background: linear-gradient(to bottom, var(--color-paper), transparent 220px), linear-gradient(110deg, var(--color-paper) 40%, var(--color-light)); }
	.hero-stage :global(.brand-ribbon) { mask-image: linear-gradient(to bottom, transparent, #000 26%); }
	.hero { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: var(--space-12); align-items: center; padding-block: var(--space-6) var(--space-20); }
	.hero h1 { font: 800 clamp(3rem, 5vw, 4.5rem)/1.05 var(--font-display); letter-spacing: -0.065em; margin: 0 0 var(--space-6); }
	.hero h1 span { color: var(--color-primary); }
	.hero-copy > p { color: var(--color-text-muted); font-size: var(--text-md); line-height: 1.8; max-width: 420px; margin: 0; }
	.hero-actions { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3); margin-block: var(--space-8) var(--space-5); }
	.hero-actions .button, .hero-secondary { border-radius: var(--radius-pill); min-height: 48px; padding-inline: var(--space-6); }
	.hero-actions .button { background: var(--color-ink); border-color: var(--color-ink); }
	.hero-actions .button:hover { background: var(--color-primary-dark); border-color: var(--color-primary-dark); }
	.hero-secondary { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--color-ink); border: 1px solid var(--color-border-strong); text-decoration: none; font-size: var(--text-sm); font-weight: 600; white-space: nowrap; }
	.hero-secondary:hover { background: var(--color-light); }
	.play-icon { display: grid; place-items: center; background: var(--color-primary-dark); color: var(--color-inverse); width: 19px; height: 19px; font-size: 8px; border-radius: 50%; padding-left: 1px; }
	.quiet-link { display: inline-flex; align-items: center; gap: var(--space-3); min-height: 44px; color: var(--color-ink); text-decoration: none; font-size: var(--text-sm); font-weight: 600; white-space: nowrap; }
	.quiet-link:hover { color: var(--color-primary); }
	.quiet-link span { font-size: 18px; }
	.hero-copy > .hero-note { font-size: var(--text-xs); }
	.capability-line { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-4); border-block: 1px solid var(--color-border); padding-block: var(--space-6); color: var(--color-text-muted); font-size: var(--text-xs); }
	.workflow-section { padding-block: 104px; scroll-margin-top: var(--space-6); }
	.section-intro { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-16); align-items: center; margin-bottom: var(--space-12); }
	.landing h2 { font: 700 clamp(1.875rem, 3vw, 2.5rem)/1.2 var(--font-display); letter-spacing: -0.045em; margin: 0; }
	.section-intro p, .team-heading p { font-size: var(--text-sm); line-height: 1.8; color: var(--color-text-muted); margin: 0; max-width: 440px; }
	.workflow-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .85fr); gap: var(--space-16); }
	.workflow-controls button { background: transparent; border: 0; border-radius: 0; border-top: 1px solid var(--color-border); padding: var(--space-6) 0; display: flex; align-items: baseline; gap: var(--space-5); width: 100%; color: var(--color-text-muted); text-align: left; white-space: normal; }
	.workflow-controls button:last-child { border-bottom: 1px solid var(--color-border); }
	.workflow-controls button.chosen, .workflow-controls button:hover { color: var(--color-primary-dark); }
	.step-number { font: var(--text-xs) var(--font-mono); }
	.workflow-controls strong { font-size: var(--text-md); font-weight: 650; }
	.step-description { display: block; font-size: var(--text-xs); line-height: 1.8; font-weight: 400; margin-top: var(--space-2); color: var(--color-text-muted); }
	.step-select { margin-left: auto; font-size: 20px; }
	.workflow-detail { padding: var(--space-10); background: var(--color-soft); border-radius: var(--radius-md); display: flex; flex-direction: column; align-items: flex-start; }
	.workflow-detail-body { width: 100%; display: flex; flex-direction: column; align-items: flex-start; }
	.detail-position { color: var(--color-text-muted); font-size: var(--text-xs); margin-bottom: var(--space-5); }
	.workflow-detail h3 { font-size: var(--text-xl); letter-spacing: -.03em; margin: 0 0 var(--space-3); }
	.workflow-detail p { color: var(--color-text-muted); font-size: var(--text-sm); margin: 0 0 var(--space-6); }
	.extraction-example { width: 100%; font-size: var(--text-xs); margin: 0 0 var(--space-6); }
	.extraction-example > div { display: flex; justify-content: space-between; gap: var(--space-3); padding-block: var(--space-3); border-bottom: 1px solid var(--color-border); }
	.extraction-example dt { color: var(--color-text-muted); }
	.extraction-example dd { margin: 0; text-align: right; }
	.detail-list { padding: 0; list-style: none; font-size: var(--text-sm); margin: 0 0 var(--space-8); }
	.detail-list li { padding-block: var(--space-3); border-bottom: 1px solid var(--color-border); }
	.workflow-detail .quiet-link { margin-top: auto; }
	.team-section { padding-bottom: 104px; scroll-margin-top: var(--space-6); }
	.team-heading { margin-bottom: var(--space-12); }
	.team-heading h2 span { color: var(--color-primary); }
	.team-heading p { margin-top: var(--space-5); }
	.audience-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-16); }
	.audience-layout article { border-top: 1px solid var(--color-border); padding-top: var(--space-6); }
	.audience-label { color: var(--color-text-muted); font-size: var(--text-xs); }
	.audience-layout h3 { font-size: 26px; line-height: 1.35; letter-spacing: -.04em; margin: var(--space-6) 0 var(--space-4); }
	.audience-layout article > p { font-size: var(--text-sm); color: var(--color-text-muted); max-width: 440px; margin: 0 0 var(--space-4); }
	.employee-note { background: var(--color-light); border-radius: var(--radius-md); padding: var(--space-6); margin-top: var(--space-8); display: flex; gap: var(--space-4); align-items: center; }
	.employee-note > span { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--color-primary); color: var(--color-inverse); flex-shrink: 0; }
	.employee-note p { font-size: var(--text-sm); margin: 0; }
	.finance-note { margin-top: var(--space-8); }
	.finance-note > div { display: flex; justify-content: space-between; gap: var(--space-3); padding-block: var(--space-3); border-bottom: 1px solid var(--color-border); font-size: var(--text-xs); }
	.finance-note span { color: var(--color-text-muted); }
	.finance-note strong { font-weight: 500; text-align: right; }
	.faq-section { display: grid; grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr); gap: var(--space-16); padding-bottom: 104px; scroll-margin-top: var(--space-6); }
	.faq-intro p { margin-block: var(--space-5); color: var(--color-text-muted); font-size: var(--text-sm); max-width: 320px; }
	.faq-list details { border-bottom: 1px solid var(--color-border); }
	.faq-list details:first-child { border-top: 1px solid var(--color-border); }
	.faq-list summary { display: flex; align-items: center; justify-content: space-between; gap: var(--space-5); padding-block: var(--space-6); font-size: var(--text-sm); font-weight: 600; cursor: pointer; list-style: none; }
	.faq-list summary::-webkit-details-marker { display: none; }
	.faq-list summary::after { content: '+'; color: var(--color-primary); font-size: 22px; font-weight: 400; }
	.faq-list details[open] summary::after { content: '−'; }
	.faq-list details p { margin: 0; padding-bottom: var(--space-6); padding-right: var(--space-8); color: var(--color-text-muted); font-size: var(--text-sm); line-height: 1.8; }
	.closing { position: relative; isolation: isolate; overflow: clip; display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr); align-items: center; gap: var(--space-8); background: var(--color-ink); color: var(--color-inverse); border-radius: var(--radius-lg); padding: var(--space-12); }
	.closing-copy > img { margin-bottom: var(--space-6); }
	.closing h2 { font-size: clamp(2rem, 3.2vw, 3rem); }
	.closing h2 span { color: var(--color-mint); }
	.closing-copy p { color: var(--color-light); font-size: var(--text-sm); margin: var(--space-6) 0; }
	.closing-button { color: var(--color-ink); background: var(--color-mint); border-color: var(--color-mint); flex-shrink: 0; border-radius: var(--radius-pill); }
	.closing-button:hover { background: var(--color-light); border-color: var(--color-light); }
	.landing-footer { padding-block: var(--space-16) var(--space-10); }
	.footer-shell { border-top: 1px solid var(--color-border); padding-top: var(--space-12); }
	.footer-grid { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.35fr); gap: var(--space-16); align-items: start; }
	.footer-brand { display: flex; flex-direction: column; align-items: flex-start; }
	.footer-brand .wordmark span { font-size: 26px; }
	.footer-brand .wordmark img { transition: transform 240ms var(--ease-out); }
	.footer-brand .wordmark:hover img { transform: rotate(-8deg) scale(1.06); }
	.footer-summary { max-width: 380px; margin: var(--space-4) 0 var(--space-6); color: var(--color-text-muted); font-size: var(--text-sm); line-height: 1.75; }
	.footer-callout { display: inline-flex; align-items: center; flex-wrap: wrap; gap: var(--space-3); padding: 6px 6px 6px var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border-strong); border-radius: var(--radius-pill); transition: border-color 200ms ease, box-shadow 200ms ease, background-color 200ms ease; }
	.footer-callout:hover { border-color: var(--color-primary); background: var(--color-light); box-shadow: 0 10px 24px rgb(9 89 81 / 0.08); }
	.callout-copy { font-size: var(--text-xs); font-weight: 600; color: var(--color-ink); }
	.footer-pill { display: inline-flex; align-items: center; gap: var(--space-2); min-height: 36px; padding-inline: var(--space-4); border-radius: var(--radius-pill); background: var(--color-ink); color: var(--color-inverse); font-size: var(--text-xs); font-weight: 600; text-decoration: none; white-space: nowrap; transition: background-color 180ms ease, transform 180ms var(--ease-out); }
	.footer-pill span { transition: transform 180ms var(--ease-out); }
	.footer-callout:hover .footer-pill, .footer-pill:hover { background: var(--color-primary-dark); }
	.footer-pill:hover { transform: translateY(-1px); }
	.footer-callout:hover .footer-pill span, .footer-pill:hover span { transform: translateX(3px); }
	.footer-nav { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-8); }
	.footer-col { display: flex; flex-direction: column; align-items: flex-start; }
	.footer-heading { margin: 0 0 var(--space-3); font-size: var(--text-xs); font-weight: 700; color: var(--color-ink); letter-spacing: 0.02em; }
	.footer-nav .footer-col a { display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 4px 0; border-radius: 0; background: transparent; color: var(--color-text-muted); font-size: var(--text-sm); text-decoration: none; transition: color 180ms ease, opacity 180ms ease, transform 200ms var(--ease-out); }
	.footer-nav .footer-col a span { margin-left: 0; }
	.footer-col:hover a:not(:hover):not(:focus-visible) { opacity: 0.55; }
	.footer-nav .footer-col a:hover, .footer-nav .footer-col a:focus-visible { background: transparent; color: var(--color-primary-dark); transform: translateX(4px); }
	.footer-link-arrow { font-size: 12px; color: var(--color-primary); opacity: 0; transform: translate(-6px, 2px); transition: opacity 180ms ease, transform 200ms var(--ease-out); }
	.footer-nav .footer-col a:hover .footer-link-arrow, .footer-nav .footer-col a:focus-visible .footer-link-arrow { opacity: 1; transform: translate(0, 0); }
	.footer-wordmark-stage { overflow: clip; margin-top: var(--space-12); padding-top: var(--space-4); text-align: center; user-select: none; mask-image: linear-gradient(to bottom, #000 42%, transparent 98%); }
	.footer-giant-mark { display: inline-flex; justify-content: center; font: 800 clamp(5.5rem, 22vw, 16rem)/0.8 var(--font-display); letter-spacing: -0.065em; color: var(--color-primary-dark); }
	.footer-giant-mark span { display: inline-block; opacity: 0.14; transform: translateY(8%); transition: transform 420ms var(--ease-out), opacity 320ms ease, color 320ms ease; }
	.footer-giant-mark span:nth-child(2) { transition-delay: 35ms; }
	.footer-giant-mark span:nth-child(3) { transition-delay: 70ms; }
	.footer-giant-mark span:nth-child(4) { transition-delay: 105ms; }
	.footer-wordmark-stage:hover .footer-giant-mark span { opacity: 0.28; color: var(--color-primary); transform: translateY(1%); }
	.footer-giant-mark span:hover { opacity: 0.45 !important; transform: translateY(-2%) !important; }
	.footer-bottom { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-4); padding-top: var(--space-5); border-top: 1px solid var(--color-border); font-size: var(--text-xs); color: var(--color-text-muted); }
	.footer-bottom p { margin: 0; }
	.footer-meta-links { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-6); }
	.footer-pillars { color: var(--color-text-muted); }
	.footer-backtop { display: inline-flex; align-items: center; gap: var(--space-2); min-height: 44px; color: var(--color-ink); font-weight: 600; text-decoration: none; transition: color 180ms ease; }
	.backtop-icon { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--color-border-strong); color: var(--color-ink); font-size: 12px; transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease, transform 200ms var(--ease-out); }
	.footer-backtop:hover { color: var(--color-primary-dark); }
	.footer-backtop:hover .backtop-icon { background: var(--color-primary); border-color: var(--color-primary); color: var(--color-inverse); transform: translateY(-2px); }
	@media (max-width: 960px) {
		.landing { --nav-offset: 106px; }
		.landing-header { min-height: 72px; flex-wrap: wrap; gap: var(--space-3); position: relative; }
		.landing-header { z-index: 10; }
		.landing-header nav { position: absolute; top: calc(100% - 4px); left: 0; display: grid; grid-template-rows: 0fr; align-items: stretch; width: 100%; padding: 0 var(--space-5); gap: 0; background: var(--color-surface); border-radius: var(--radius-md); box-shadow: 0 14px 28px rgb(0 45 40 / .1); visibility: hidden; transition: grid-template-rows 240ms ease, visibility 240ms; }
		.landing-header nav.expanded { grid-template-rows: 1fr; visibility: visible; }
		.nav-links { min-height: 0; width: 100%; overflow: hidden; display: flex; flex-direction: column; align-items: stretch; gap: 0; }
		.landing-header nav { grid-template-columns: minmax(0, 1fr); justify-content: stretch; }
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
		.hero { gap: var(--space-8); }
		.section-intro, .workflow-layout, .audience-layout { gap: var(--space-8); }
		.hero h1 { font-size: 3rem; }
		.closing { gap: var(--space-4); padding: var(--space-8); }
		.footer-grid { grid-template-columns: minmax(0, 1fr); gap: var(--space-10); }
	}
	@media (max-width: 768px) {
		.landing { --nav-offset: 88px; }
		.landing-header, .hero, .capability-line, .workflow-section, .team-section, .faq-section, .closing, .landing-footer { width: calc(100% - 40px); }
		.navbar-shell { top: 10px; width: calc(100% - 24px); margin-block: 10px; border-radius: 16px; }
		.landing-header { width: 100%; padding: 10px; min-height: 66px; flex-wrap: wrap; gap: var(--space-2); position: relative; }
		.landing-header .wordmark { gap: 4px; }
		.landing-header .wordmark img { width: 28px; height: 28px; }
		.nav-cta { padding-inline: var(--space-3); }
		.menu-toggle { display: inline-flex; }
		.wordmark span { font-size: 25px; }
		.hero { grid-template-columns: minmax(0, 1fr); padding-block: var(--space-6) var(--space-16); gap: var(--space-6); }
		.hero h1 { font-size: clamp(2.625rem, 8vw, 4rem); }
		.hero-copy > p { max-width: 520px; }
		.hero-actions .button, .hero-secondary { font-size: 12px; padding-inline: var(--space-4); }
		.capability-line { justify-content: flex-start; column-gap: var(--space-6); font-size: 11px; }
		.workflow-section { padding-block: var(--space-16); }
		.section-intro, .workflow-layout, .audience-layout { grid-template-columns: minmax(0, 1fr); gap: var(--space-8); }
		.workflow-detail { padding: var(--space-6); min-height: 340px; }
		.team-section { padding-bottom: var(--space-16); }
		.faq-section { grid-template-columns: minmax(0, 1fr); gap: var(--space-8); padding-bottom: var(--space-16); }
		.audience-layout { gap: var(--space-12); }
		.closing { grid-template-columns: minmax(0, 1fr); padding: var(--space-8) var(--space-6) var(--space-12); }
		.landing-footer { padding-block: var(--space-12) var(--space-8); }
		.footer-shell { padding-top: var(--space-8); }
		.footer-nav { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-6); }
		.footer-callout { border-radius: var(--radius-md); padding: var(--space-3); width: 100%; justify-content: space-between; }
		.footer-wordmark-stage { margin-top: var(--space-8); }
		.footer-pillars { display: none; }
	}
	@media (max-width: 374px) {
		.nav-cta { font-size: 11px; }
		.menu-toggle { padding-inline: var(--space-3); font-size: 11px; }
		.footer-nav { grid-template-columns: minmax(0, 1fr); }
	}
	@media (max-width: 960px) and (prefers-reduced-motion: reduce) { .landing-header nav { transition: none; } }
	@media (prefers-reduced-motion: reduce) { .product-panel, .product-trigger svg, .footer-brand .wordmark img, .footer-callout, .footer-pill, .footer-pill span, .footer-col a, .footer-link-arrow, .footer-giant-mark span, .backtop-icon { transition: none; } }
</style>
