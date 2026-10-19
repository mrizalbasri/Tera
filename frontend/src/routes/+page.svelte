<script lang="ts">
	import TeraReceiptArtwork from '$lib/components/TeraReceiptArtwork.svelte';
	import TeraBrandRibbon from '$lib/components/TeraBrandRibbon.svelte';
	import { reveal } from '$lib/actions/reveal';
	import { onMount } from 'svelte';

	let { data } = $props();
	let mobileMenu = $state(false);
	let productMenu = $state(false);
	let productButton = $state<HTMLButtonElement>();
	let headerElement = $state<HTMLElement>();
	function closeMenus() { mobileMenu = false; productMenu = false; }
	let menuButton = $state<HTMLButtonElement>();

	let activeStep = $state(0);
	let isWorkflowPaused = $state(false);

	const workflow = [
		{
			title: 'Nota dibaca',
			description: 'Vendor, tanggal, dan nominal diambil dari nota via Vision AI.',
			label: 'Ekstraksi Cerdas & Presisi',
			detail: 'Model vision membaca teks dan struktur nota beresolusi tinggi, mendeteksi item dan total pengeluaran.'
		},
		{
			title: 'Kebijakan dicocokkan',
			description: 'Pengeluaran diperiksa terhadap aturan plafon & batas operasional.',
			label: 'Pencocokan Kebijakan Otomatis',
			detail: 'Sistem membandingkan nominal dengan batasan divisi, jam operasional kerja, dan kategori eligibilitas.'
		},
		{
			title: 'Risiko diperiksa',
			description: 'Deteksi duplikasi riwayat dan analisis anomali pengeluaran.',
			label: 'Inspeksi Integritas & Risiko',
			detail: 'Algoritma mendeteksi pengajuan ganda serta anomali nominal sebelum klaim diputuskan.'
		},
		{
			title: 'Tindak lanjut ditentukan',
			description: 'Klaim disetujui instan, diklarifikasi, atau diteruskan ke reviewer.',
			label: 'Keputusan Transparan & Audit Trail',
			detail: 'Setiap keputusan dilengkapi alasan rasional dan rekam jejak pemeriksaan yang dapat diaudit.'
		}
	];
	const selected = $derived(workflow[activeStep]);

	onMount(() => {
		const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
		if (mediaQuery.matches) return;

		const timer = setInterval(() => {
			if (!isWorkflowPaused) {
				activeStep = (activeStep + 1) % workflow.length;
			}
		}, 4600);

		return () => clearInterval(timer);
	});

	function handleStepSelect(index: number) {
		activeStep = index;
	}

	function handleCardSpotlight(event: PointerEvent) {
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		target.style.setProperty('--spotlight-x', `${event.clientX - rect.left}px`);
		target.style.setProperty('--spotlight-y', `${event.clientY - rect.top}px`);
	}
</script>

<svelte:head>
	<title>Tera · AI Expense Agent untuk tim modern</title>
	<meta name="description" content="Tera membantu membaca nota, memeriksa kebijakan, dan menata proses reimbursement. Ajukan klaim dan ikuti setiap langkah pemeriksaannya." />
</svelte:head>

<svelte:window
	onpointerdown={(event) => { if (event.target instanceof Node && !headerElement?.contains(event.target)) closeMenus(); }}
	onkeydown={(event) => {
		if (event.key === 'Escape') {
			if (productMenu) { productMenu = false; productButton?.focus(); }
			else if (mobileMenu) { mobileMenu = false; menuButton?.focus(); }
		}
	}}
/>

<div class="landing">
	<div class="navbar-shell">
		<header
			bind:this={headerElement}
			class="landing-header"
			onfocusout={(event) => { if (event.relatedTarget instanceof Node && !headerElement?.contains(event.relatedTarget)) productMenu = false; }}
		>
			<a class="wordmark" href="/" aria-label="Tera, beranda">
				<img src="/logo.webp" alt="" width="36" height="36" />
				<span>Tera</span>
			</a>
			<nav class:expanded={mobileMenu} id="landing-nav" aria-label="Navigasi beranda">
				<div class="nav-links">
					<button
						bind:this={productButton}
						type="button"
						class="product-trigger"
						class:selected={productMenu}
						aria-expanded={productMenu}
						aria-controls="product-panel"
						onclick={() => (productMenu = !productMenu)}
					>
						Produk
						<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
							<path d="m4 6 4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					</button>
					<div class="product-panel" class:shown={productMenu} id="product-panel" inert={!productMenu}>
						<div class="product-panel-content">
							<a class="product-spotlight" href="#cara-kerja" onclick={closeMenus}>
								<span class="menu-eyebrow">KENALI TERA</span>
								<strong>Dari nota<br />ke keputusan.</strong>
								<span class="spotlight-description">Lihat bagaimana Tera memeriksa pengeluaran kerja.</span>
								<img src="/brand/tera-receipt-curved.png" alt="" width="1280" height="1280" />
								<span class="spotlight-link">Jelajahi alurnya <span aria-hidden="true">↗</span></span>
							</a>
							<div class="product-shortcuts">
								<a href="/pengajuan" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">↥</span>
									<span><strong>Ajukan klaim</strong><small>Unggah nota dan mulai pemeriksaan.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/riwayat" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">≡</span>
									<span><strong>Riwayat pengajuan</strong><small>Ikuti status dan jejak setiap klaim.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/reviews" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">✓</span>
									<span><strong>Review klaim</strong><small>Tinjau bukti dan tentukan tindak lanjut.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
								<a href="/reports" onclick={closeMenus}>
									<span class="shortcut-symbol" aria-hidden="true">↗</span>
									<span><strong>Laporan pengeluaran</strong><small>Lihat ringkasan dan ekspor data klaim.</small></span>
									<span class="shortcut-arrow" aria-hidden="true">↗</span>
								</a>
							</div>
							<div class="product-panel-footer">
								<span>Satu alur untuk karyawan dan finance.</span>
								<a href="#untuk-tim" onclick={closeMenus}>Tera untuk tim <span aria-hidden="true">→</span></a>
							</div>
						</div>
					</div>
					<a href="#fitur" onclick={closeMenus}>Fitur</a>
					<a href="#cara-kerja" onclick={closeMenus}>Cara kerja</a>
					<a href="#untuk-tim" onclick={closeMenus}>Untuk tim</a>
					<a href="#faq" onclick={closeMenus}>FAQ</a>
					<a href={data.demoMode ? '/reviews' : '/login'} onclick={closeMenus}>{data.demoMode ? 'Buka review' : 'Login admin'}</a>
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
					onclick={() => { mobileMenu = !mobileMenu; productMenu = false; }}
				>
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
		<div class="hero-stage" id="produk">
			<div class="ambient-aura aura-1" aria-hidden="true"></div>
			<div class="ambient-aura aura-2" aria-hidden="true"></div>
			<TeraBrandRibbon />
			<section class="hero" aria-labelledby="hero-title">
				<div class="hero-copy">
					<div class="hero-badge">
						<span class="badge-dot"></span>
						<span>Otomatisasi Reimbursement Cerdas</span>
					</div>
					<h1 id="hero-title">AI Expense<br />Agent untuk<br /><span>Tim Modern.</span></h1>
					<p>Dari nota hingga keputusan klaim. Tera membantu membaca bukti transaksi, memverifikasi kepatuhan kebijakan, dan mengeliminasi friksi reimbursement.</p>
					<div class="hero-actions">
						<a class="button hero-cta" href="/pengajuan">
							<span>Ajukan klaim</span>
							<span aria-hidden="true">→</span>
						</a>
						<a class="hero-secondary" href="#cara-kerja">
							<span class="play-icon" aria-hidden="true">▶</span>
							<span>Lihat alurnya</span>
						</a>
					</div>
					<p class="hero-note">Kirim nota. Ikuti prosesnya secara transparan. Lanjutkan pekerjaan.</p>
				</div>
				<TeraReceiptArtwork />
			</section>
		</div>

		<!-- Smooth Infinite Feature Marquee -->
		<div class="marquee-strip" id="fitur" aria-label="Fitur Utama Tera">
			<div class="marquee-track">
				<div class="marquee-content">
					<span><span class="m-dot"></span> Ekstraksi Vision AI Multi-Format</span>
					<span><span class="m-dot"></span> Verifikasi Batas Plafon Kebijakan</span>
					<span><span class="m-dot"></span> Deteksi Duplikat & Anomali Real-Time</span>
					<span><span class="m-dot"></span> Klarifikasi Mandiri Karyawan</span>
					<span><span class="m-dot"></span> Rekam Jejak Audit Transparan</span>
					<span><span class="m-dot"></span> Antrean Review & Ekspor CSV Cepat</span>
				</div>
				<div class="marquee-content" aria-hidden="true">
					<span><span class="m-dot"></span> Ekstraksi Vision AI Multi-Format</span>
					<span><span class="m-dot"></span> Verifikasi Batas Plafon Kebijakan</span>
					<span><span class="m-dot"></span> Deteksi Duplikat & Anomali Real-Time</span>
					<span><span class="m-dot"></span> Klarifikasi Mandiri Karyawan</span>
					<span><span class="m-dot"></span> Rekam Jejak Audit Transparan</span>
					<span><span class="m-dot"></span> Antrean Review & Ekspor CSV Cepat</span>
				</div>
			</div>
		</div>

		<!-- Workflow Section with Auto-Progressing Stepper -->
		<section
			use:reveal
			class="workflow-section scroll-reveal"
			id="cara-kerja"
			aria-labelledby="workflow-title"
			onpointerenter={() => (isWorkflowPaused = true)}
			onpointerleave={() => (isWorkflowPaused = false)}
		>
			<div class="section-intro">
				<h2 id="workflow-title">Bukan sekadar<br />menyimpan nota.</h2>
				<p>Setiap pengajuan diproses melalui 4 tahapan verifikasi otomatis. Kamu bisa melihat apa yang dibaca, apa yang divalidasi, dan mengapa sebuah keputusan diambil.</p>
			</div>
			<div class="workflow-layout">
				<div class="workflow-controls" aria-label="Jelajahi alur pemeriksaan">
					{#each workflow as step, i}
						<button
							type="button"
							class="workflow-step-btn"
							class:chosen={activeStep === i}
							aria-pressed={activeStep === i}
							aria-controls="workflow-detail"
							onclick={() => handleStepSelect(i)}
						>
							<span class="step-number" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
							<div class="step-text">
								<strong>{step.title}</strong>
								<span class="step-description">{step.description}</span>
							</div>
							<span class="step-select" aria-hidden="true">{activeStep === i ? '●' : '+'}</span>
							{#if activeStep === i}
								<div class="step-progress-track">
									<div class="step-progress-bar" style="animation-play-state: {isWorkflowPaused ? 'paused' : 'running'};"></div>
								</div>
							{/if}
						</button>
					{/each}
				</div>

				<div class="workflow-detail" id="workflow-detail" aria-live="polite">
					{#key activeStep}
						<div class="workflow-detail-body">
							<div class="detail-header-row">
								<span class="detail-position">Langkah {activeStep + 1} dari {workflow.length}</span>
								<span class="step-live-pill">
									<span class="step-pulse"></span>
									Simulasi AI
								</span>
							</div>
							<h3>{selected.label}</h3>
							<p>{selected.detail}</p>

							{#if activeStep === 0}
								<div class="step-interactive-display">
									<div class="extraction-card">
										<div class="card-item"><span class="k">Merchant</span><strong class="v">SPBU Shell BSD</strong><span class="conf">99.4%</span></div>
										<div class="card-item"><span class="k">Tanggal</span><strong class="v">18 Okt 2026</strong><span class="conf">100%</span></div>
										<div class="card-item"><span class="k">Nominal</span><strong class="v highlight">Rp 350.000</strong><span class="conf">99.8%</span></div>
										<div class="card-item"><span class="k">Kategori</span><strong class="v">Bahan Bakar (BBM)</strong><span class="conf">98.5%</span></div>
									</div>
								</div>
							{:else if activeStep === 1}
								<div class="step-interactive-display">
									<ul class="detail-checklist">
										<li><span class="badge-check">✓</span> <span>Plafon BBM: <strong>Rp 350.000 / Rp 500.000 (Sesuai)</strong></span></li>
										<li><span class="badge-check">✓</span> <span>Kesesuaian Departemen: <strong>Operasional Lapangan</strong></span></li>
										<li><span class="badge-check">✓</span> <span>Batas Waktu Transaksi: <strong>Kurang dari 30 hari</strong></span></li>
									</ul>
								</div>
							{:else if activeStep === 2}
								<div class="step-interactive-display">
									<div class="risk-meter-box">
										<div class="risk-row"><span>Pemeriksaan Duplikat Nota:</span> <strong class="clean">0 Ditemukan (Bebas Duplikat)</strong></div>
										<div class="risk-row"><span>Skor Anomali Pembelian:</span> <strong class="clean">0.04 · Normal (Lolos Deteksi)</strong></div>
										<div class="risk-bar-track"><div class="risk-bar-fill"></div></div>
									</div>
								</div>
							{:else}
								<div class="step-interactive-display">
									<div class="decision-outcome-box">
										<div class="outcome-badge">
											<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
											<strong>Status: Disetujui Otomatis (Straight-Through)</strong>
										</div>
										<p class="outcome-desc">Semua parameter valid. Tidak memerlukan eskalasi manual ke tim finance.</p>
									</div>
								</div>
							{/if}

							<a class="quiet-link" href="/pengajuan">Coba dengan notamu <span aria-hidden="true">↗</span></a>
						</div>
					{/key}
				</div>
			</div>
		</section>

		<!-- Bento audience with interactive spotlight glow -->
		<section use:reveal class="team-section scroll-reveal" id="untuk-tim" aria-labelledby="team-title">
			<div class="team-heading">
				<h2 id="team-title">Tera memeriksa.<br /><span>Tim tetap memegang kendali.</span></h2>
				<p>Satu platform terintegrasi untuk mengajukan, melengkapi klarifikasi, dan meninjau pengeluaran kerja.</p>
			</div>
			<div class="audience-layout">
				<article class="employee-section spotlight-card" onpointermove={handleCardSpotlight}>
					<span class="audience-label">UNTUK KARYAWAN</span>
					<h3>Ajukan sekali.<br />Pantau sampai tuntas.</h3>
					<p>Unggah foto atau dokumen PDF nota, ikuti progres pemeriksaan secara real-time, dan lengkapi informasi jika Tera memerlukan klarifikasi tambahan.</p>
					<a class="quiet-link" href="/riwayat">Lihat riwayat klaim <span aria-hidden="true">↗</span></a>
					<div class="employee-note">
						<span aria-hidden="true">✓</span>
						<p>Bukti nota fisik, hasil pembacaan AI, dan status pengajuan tersimpan aman dalam satu klaim terpadu.</p>
					</div>
				</article>

				<article class="finance-section spotlight-card" onpointermove={handleCardSpotlight}>
					<span class="audience-label">UNTUK FINANCE & REVIEWER</span>
					<h3>Lihat buktinya.<br />Tentukan tindak lanjutnya.</h3>
					<p>Tinjau antrean klaim yang dieskalasi dengan sinyal risiko dan aturan yang dilanggar. Setiap keputusan reviewer tercatat dalam riwayat audit permanen.</p>
					<a class="quiet-link" href="/reviews">Buka antrean review <span aria-hidden="true">↗</span></a>
					<div class="finance-note">
						<div><span>Bukti nota</span><strong>Tersimpan utuh & dapat dirotasi/diperbesar</strong></div>
						<div><span>Audit Trail</span><strong>Keputusan dilengkapi catatan & timestamp</strong></div>
						<div><span>Pelaporan</span><strong>Dapat difilter dan diekspor ke CSV</strong></div>
					</div>
				</article>
			</div>
		</section>

		<section use:reveal class="faq-section scroll-reveal" id="faq" aria-labelledby="faq-title">
			<div class="faq-intro">
				<h2 id="faq-title">Sebelum mengirim<br />nota pertamamu.</h2>
				<p>Pertanyaan umum mengenai alur pengajuan dan validasi otomatis di Tera.</p>
				<a class="quiet-link" href="/pengajuan">Mulai pengajuan <span aria-hidden="true">↗</span></a>
			</div>
			<div class="faq-list">
				<details>
					<summary>Apa saja yang diperiksa oleh Tera?</summary>
					<p>Tera membaca informasi pada nota (merchant, tanggal, total, line items), membandingkan pengeluaran dengan kebijakan plafon perusahaan, serta memeriksa duplikasi dan anomali nominal.</p>
				</details>
				<details>
					<summary>Apakah semua klaim otomatis disetujui?</summary>
					<p>Klaim yang memenuhi seluruh kebijakan langsung disetujui otomatis. Klaim yang melampaui batas atau mengandung anomali akan masuk ke antrean klarifikasi karyawan atau review tim finance.</p>
				</details>
				<details>
					<summary>Bagaimana karyawan memantau status pengajuan?</summary>
					<p>Buka menu Riwayat di aplikasi untuk melihat status, rincian pembacaan, dan timeline keputusan. Karyawan juga dapat langsung menjawab klarifikasi dari halaman yang sama.</p>
				</details>
				<details>
					<summary>Apa kapabilitas khusus untuk tim finance?</summary>
					<p>Tim finance memiliki akses antrean review untuk memvalidasi bukti nota secara visual (zoom/rotate), memberikan keputusan akhir, serta mengunduh rekap pengeluaran format CSV.</p>
				</details>
			</div>
		</section>

		<section use:reveal class="closing scroll-reveal" aria-labelledby="closing-title">
			<TeraBrandRibbon dark />
			<div class="closing-copy">
				<img src="/logo.webp" width="40" height="40" alt="" />
				<h2 id="closing-title">Ubah nota kertas.<br /><span>Rapikan pengeluaran.</span></h2>
				<p>Tera memeriksa detailnya dengan presisi AI,<br />agar kamu dan tim bisa fokus menyelesaikan pekerjaan utama.</p>
				<a class="button closing-button" href="/pengajuan">
					<span>Ajukan klaim pertamamu</span>
					<span aria-hidden="true">→</span>
				</a>
			</div>
			<TeraReceiptArtwork compact />
		</section>
	</main>

	<footer class="landing-footer">
		<a class="wordmark" href="/" aria-label="Tera, beranda">
			<img src="/logo.webp" width="28" height="28" alt="" />
			<span>Tera</span>
		</a>
		<p>Pengeluaran kerja, lebih tertata.</p>
		<a href="/pengajuan">Buka aplikasi</a>
		<a href="#cara-kerja">Cara kerja</a>
	</footer>
</div>

<style>
	.landing {
		--nav-offset: 110px;
		display: flow-root;
		color: var(--color-ink);
	}

	.navbar-shell {
		position: sticky;
		top: 16px;
		z-index: 50;
		width: min(1040px, calc(100% - 48px));
		margin: 16px auto;
		background: rgba(255, 255, 255, 0.88);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border: 1px solid var(--color-border);
		border-radius: 20px;
		box-shadow: 0 8px 24px -4px rgba(0, 45, 40, 0.08);
		transition: all 0.25s ease;
	}

	.landing :is(#produk, #fitur, #cara-kerja, #untuk-tim, #faq) {
		scroll-margin-top: 124px;
	}

	.landing-header, .hero, .workflow-section, .team-section, .faq-section, .closing, .landing-footer {
		width: min(1120px, calc(100% - 64px));
		margin-inline: auto;
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
		transition: color 0.18s ease;
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

	.product-panel-content {
		display: grid;
		grid-template-columns: .85fr 1.15fr;
		padding: 8px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 16px;
		box-shadow: 0 20px 48px rgba(0, 45, 40, 0.14);
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

	.landing-header nav .product-spotlight > span {
		margin-left: 0;
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

	.landing-header nav .product-shortcuts a > span {
		margin-left: 0;
	}

	.landing-header nav .product-shortcuts a > span:nth-child(2) {
		display: block;
		flex: 1;
		min-width: 0;
	}

	.landing-header nav .product-shortcuts a > .shortcut-arrow {
		display: block;
		margin-left: auto;
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

	.landing-header nav .product-panel-footer a {
		min-height: 36px;
		padding: 0;
		gap: 10px;
		font-size: 11px;
		font-weight: 600;
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

	/* Scroll Reveal & Motion */
	:global(.landing .scroll-reveal) {
		transition: opacity 700ms ease, transform 700ms cubic-bezier(.22, 1, .36, 1);
	}

	:global(.landing .awaiting-reveal) {
		opacity: 0;
		transform: translateY(28px);
	}

	@keyframes hero-enter {
		from { opacity: 0; transform: translateY(24px); }
		to { opacity: 1; transform: translateY(0); }
	}

	/* Ambient Aura Glowing Orbs */
	.ambient-aura {
		position: absolute;
		border-radius: 50%;
		pointer-events: none;
		filter: blur(80px);
		z-index: 0;
		opacity: 0.65;
	}

	.aura-1 {
		top: 8%;
		right: 12%;
		width: 480px;
		height: 480px;
		background: radial-gradient(circle, rgba(16, 185, 129, 0.22) 0%, rgba(15, 118, 110, 0.1) 45%, transparent 70%);
	}

	.aura-2 {
		top: 40%;
		left: 4%;
		width: 420px;
		height: 420px;
		background: radial-gradient(circle, rgba(45, 212, 191, 0.16) 0%, rgba(20, 184, 166, 0.06) 50%, transparent 70%);
	}

	@keyframes aura-drift-1 {
		from { transform: translate(0, 0) scale(1); }
		to { transform: translate(-35px, 25px) scale(1.12); }
	}

	@keyframes aura-drift-2 {
		from { transform: translate(0, 0) scale(1); }
		to { transform: translate(40px, -30px) scale(1.08); }
	}

	@media (prefers-reduced-motion: no-preference) {
		.aura-1 { animation: aura-drift-1 12s ease-in-out infinite alternate; }
		.aura-2 { animation: aura-drift-2 16s ease-in-out infinite alternate; }

		.hero-copy > * { animation: hero-enter 650ms cubic-bezier(.22, 1, .36, 1) both; }
		.hero-badge { animation-delay: 40ms; }
		.hero-copy > h1 { animation-delay: 100ms; }
		.hero-copy > p { animation-delay: 180ms; }
		.hero-actions { animation-delay: 240ms; }
		.hero-copy > .hero-note { animation-delay: 300ms; }
		.hero :global(.receipt-artwork) { animation: hero-enter 900ms 180ms cubic-bezier(.22, 1, .36, 1) both; }

		.landing a.button, .hero-secondary { transition: transform 180ms ease, background-color 180ms ease, box-shadow 180ms ease; }
		.landing a.button:hover, .hero-secondary:hover { transform: translateY(-2px); }
		.landing a.button:active, .hero-secondary:active { transform: translateY(0) scale(0.98); }

		.quiet-link span, .nav-cta span { transition: transform 180ms ease; }
		.quiet-link:hover span, .nav-cta:hover span { transform: translate(2px, -2px); }
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.landing .scroll-reveal), .menu-toggle svg path { transition: none; }
		:global(.landing .awaiting-reveal) { opacity: 1; transform: none; }
	}

	.hero-stage {
		position: relative;
		isolation: isolate;
		overflow: clip;
		margin-top: calc(-1 * var(--nav-offset));
		padding-top: var(--nav-offset);
		background: linear-gradient(to bottom, var(--color-paper), transparent 220px), linear-gradient(110deg, var(--color-paper) 40%, var(--color-light));
	}

	.hero-stage :global(.brand-ribbon) {
		mask-image: linear-gradient(to bottom, transparent, #000 26%);
	}

	.hero {
		position: relative;
		z-index: 1;
		display: grid;
		grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
		gap: var(--space-12);
		align-items: center;
		padding-block: var(--space-6) var(--space-20);
	}

	.hero-badge {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: 4px 12px;
		background: rgba(15, 118, 110, 0.08);
		border: 1px solid rgba(15, 118, 110, 0.2);
		border-radius: var(--radius-pill);
		font-size: var(--text-xs);
		font-weight: 650;
		color: var(--color-primary-dark);
		margin-bottom: var(--space-4);
		width: fit-content;
	}

	.badge-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--color-primary);
		box-shadow: 0 0 8px var(--color-primary);
	}

	.hero h1 {
		font: 800 clamp(3rem, 5vw, 4.5rem)/1.05 var(--font-display);
		letter-spacing: -0.065em;
		margin: 0 0 var(--space-6);
	}

	.hero h1 span {
		color: var(--color-primary);
	}

	.hero-copy > p {
		color: var(--color-text-muted);
		font-size: var(--text-md);
		line-height: 1.8;
		max-width: 440px;
		margin: 0;
	}

	.hero-actions {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-3);
		margin-block: var(--space-8) var(--space-5);
	}

	.hero-actions .button, .hero-secondary {
		border-radius: var(--radius-pill);
		min-height: 48px;
		padding-inline: var(--space-6);
	}

	.hero-actions .button {
		background: var(--color-ink);
		border-color: var(--color-ink);
		box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
	}

	.hero-actions .button:hover {
		background: var(--color-primary-dark);
		border-color: var(--color-primary-dark);
		box-shadow: 0 8px 20px rgba(15, 118, 110, 0.3);
	}

	/* Shimmer effect on buttons */
	.hero-cta, .closing-button, .nav-cta {
		position: relative;
		overflow: hidden;
	}

	.hero-cta::after, .closing-button::after, .nav-cta::after {
		content: '';
		position: absolute;
		top: -50%;
		left: -60%;
		width: 45%;
		height: 200%;
		background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.28), transparent);
		transform: rotate(25deg);
		pointer-events: none;
		opacity: 0;
	}

	.hero-cta:hover::after, .closing-button:hover::after, .nav-cta:hover::after {
		opacity: 1;
		animation: btn-shine 850ms cubic-bezier(0.2, 0.8, 0.2, 1);
	}

	@keyframes btn-shine {
		0% { left: -60%; }
		100% { left: 140%; }
	}

	.hero-secondary {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-ink);
		border: 1px solid var(--color-border-strong);
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 600;
		white-space: nowrap;
	}

	.hero-secondary:hover {
		background: var(--color-light);
	}

	.play-icon {
		display: grid;
		place-items: center;
		background: var(--color-primary-dark);
		color: var(--color-inverse);
		width: 19px;
		height: 19px;
		font-size: 8px;
		border-radius: 50%;
		padding-left: 1px;
	}

	.quiet-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-3);
		min-height: 44px;
		color: var(--color-ink);
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 600;
		white-space: nowrap;
	}

	.quiet-link:hover {
		color: var(--color-primary);
	}

	.quiet-link span {
		font-size: 18px;
	}

	.hero-copy > .hero-note {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
	}

	/* Infinite Feature Marquee */
	.marquee-strip {
		position: relative;
		overflow: hidden;
		width: 100%;
		padding-block: var(--space-5);
		border-block: 1px solid var(--color-border);
		background: var(--color-surface);
		mask-image: linear-gradient(to right, transparent, black 12%, black 88%, transparent);
		-webkit-mask-image: linear-gradient(to right, transparent, black 12%, black 88%, transparent);
	}

	.marquee-track {
		display: flex;
		width: max-content;
		animation: marquee-scroll 32s linear infinite;
	}

	.marquee-track:hover {
		animation-play-state: paused;
	}

	.marquee-content {
		display: flex;
		align-items: center;
		gap: var(--space-8);
		padding-right: var(--space-8);
		white-space: nowrap;
		font-size: var(--text-xs);
		font-weight: 600;
		color: var(--color-ink);
	}

	.m-dot {
		display: inline-block;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-primary);
		margin-right: var(--space-2);
		box-shadow: 0 0 6px rgba(15, 118, 110, 0.5);
	}

	@keyframes marquee-scroll {
		from { transform: translateX(0); }
		to { transform: translateX(-50%); }
	}

	/* Workflow Section */
	.workflow-section {
		padding-block: 104px;
		scroll-margin-top: var(--space-6);
	}

	.section-intro {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--space-16);
		align-items: center;
		margin-bottom: var(--space-12);
	}

	.landing h2 {
		font: 700 clamp(1.875rem, 3vw, 2.5rem)/1.2 var(--font-display);
		letter-spacing: -0.045em;
		margin: 0;
	}

	.section-intro p, .team-heading p {
		font-size: var(--text-sm);
		line-height: 1.8;
		color: var(--color-text-muted);
		margin: 0;
		max-width: 440px;
	}

	.workflow-layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, .95fr);
		gap: var(--space-14);
		align-items: stretch;
	}

	.workflow-controls {
		display: flex;
		flex-direction: column;
	}

	.workflow-step-btn {
		position: relative;
		background: transparent;
		border: 0;
		border-radius: 0;
		border-top: 1px solid var(--color-border);
		padding: var(--space-6) 0;
		display: flex;
		align-items: flex-start;
		gap: var(--space-5);
		width: 100%;
		color: var(--color-text-muted);
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: color 0.2s ease;
	}

	.workflow-step-btn:last-child {
		border-bottom: 1px solid var(--color-border);
	}

	.workflow-step-btn.chosen, .workflow-step-btn:hover {
		color: var(--color-primary-dark);
	}

	.step-number {
		font: var(--text-xs) var(--font-mono);
		font-weight: 700;
		margin-top: 2px;
	}

	.step-text {
		flex: 1;
	}

	.workflow-step-btn strong {
		font-size: var(--text-md);
		font-weight: 650;
		display: block;
	}

	.step-description {
		display: block;
		font-size: var(--text-xs);
		line-height: 1.7;
		font-weight: 400;
		margin-top: var(--space-2);
		color: var(--color-text-muted);
	}

	.step-select {
		margin-left: auto;
		font-size: 16px;
		font-weight: 700;
		color: var(--color-primary);
	}

	.step-progress-track {
		position: absolute;
		bottom: -1px;
		left: 0;
		width: 100%;
		height: 2px;
		background: var(--color-border);
		overflow: hidden;
	}

	.step-progress-bar {
		width: 100%;
		height: 100%;
		background: var(--color-primary);
		transform-origin: left;
		animation: step-timer 4.6s linear forwards;
	}

	@keyframes step-timer {
		from { transform: scaleX(0); }
		to { transform: scaleX(1); }
	}

	/* Workflow Detail Panel with Interactive Displays */
	.workflow-detail {
		padding: var(--space-8);
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: 0 12px 30px -4px rgba(0, 45, 40, 0.08);
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		min-height: 380px;
	}

	.workflow-detail-body {
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		animation: step-fade 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
	}

	@keyframes step-fade {
		from { opacity: 0; transform: translateY(8px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.detail-header-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		margin-bottom: var(--space-4);
	}

	.detail-position {
		color: var(--color-text-muted);
		font-size: var(--text-xs);
		font-weight: 600;
	}

	.step-live-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 3px 8px;
		background: rgba(16, 185, 129, 0.1);
		color: var(--color-primary-dark);
		border-radius: var(--radius-pill);
		font-size: 10px;
		font-weight: 700;
	}

	.step-pulse {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: #10b981;
		animation: pulse-ping 1.6s infinite;
	}

	.workflow-detail h3 {
		font-size: var(--text-xl);
		letter-spacing: -.03em;
		margin: 0 0 var(--space-2);
		color: var(--color-ink);
	}

	.workflow-detail-body > p {
		color: var(--color-text-muted);
		font-size: var(--text-sm);
		line-height: 1.7;
		margin: 0 0 var(--space-5);
	}

	.step-interactive-display {
		width: 100%;
		margin-bottom: var(--space-6);
	}

	.extraction-card {
		display: grid;
		gap: var(--space-2);
		background: var(--color-soft);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		padding: var(--space-4);
	}

	.card-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: var(--text-xs);
		padding-block: 4px;
		border-bottom: 1px solid rgba(0, 0, 0, 0.05);
	}

	.card-item:last-child {
		border-bottom: 0;
	}

	.card-item .k {
		color: var(--color-text-muted);
	}

	.card-item .v {
		color: var(--color-ink);
		font-weight: 600;
	}

	.card-item .v.highlight {
		color: var(--color-primary-dark);
		font-weight: 700;
	}

	.card-item .conf {
		font-size: 10px;
		font-weight: 700;
		color: #10b981;
		background: rgba(16, 185, 129, 0.12);
		padding: 1px 6px;
		border-radius: 4px;
	}

	.detail-checklist {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: var(--space-3);
		font-size: var(--text-xs);
	}

	.detail-checklist li {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		background: var(--color-soft);
		padding: var(--space-3) var(--space-4);
		border-radius: var(--radius-sm);
		border: 1px solid var(--color-border);
	}

	.badge-check {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #10b981;
		color: #fff;
		display: grid;
		place-items: center;
		font-size: 10px;
		font-weight: 800;
		flex-shrink: 0;
	}

	.risk-meter-box {
		background: var(--color-soft);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		padding: var(--space-4);
		display: grid;
		gap: var(--space-3);
		font-size: var(--text-xs);
	}

	.risk-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.risk-row .clean {
		color: #059669;
		font-weight: 700;
	}

	.risk-bar-track {
		width: 100%;
		height: 6px;
		background: var(--color-border);
		border-radius: 3px;
		overflow: hidden;
	}

	.risk-bar-fill {
		width: 6%;
		height: 100%;
		background: #10b981;
		border-radius: 3px;
	}

	.decision-outcome-box {
		background: rgba(16, 185, 129, 0.08);
		border: 1px solid rgba(16, 185, 129, 0.3);
		border-radius: var(--radius-sm);
		padding: var(--space-4);
	}

	.outcome-badge {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-primary-dark);
		font-size: var(--text-xs);
		margin-bottom: var(--space-2);
	}

	.outcome-desc {
		margin: 0;
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		line-height: 1.6;
	}

	.workflow-detail .quiet-link {
		margin-top: auto;
	}

	/* Team Section & Spotlight Cards */
	.team-section {
		padding-bottom: 104px;
		scroll-margin-top: var(--space-6);
	}

	.team-heading {
		margin-bottom: var(--space-12);
	}

	.team-heading h2 span {
		color: var(--color-primary);
	}

	.team-heading p {
		margin-top: var(--space-5);
	}

	.audience-layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--space-8);
	}

	.spotlight-card {
		position: relative;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-8);
		background: radial-gradient(450px circle at var(--spotlight-x, -500px) var(--spotlight-y, -500px), rgba(15, 118, 110, 0.09), transparent 60%), var(--color-surface);
		transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
	}

	.spotlight-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 18px 36px -8px rgba(0, 45, 40, 0.12);
		border-color: var(--color-primary);
	}

	.audience-label {
		color: var(--color-primary);
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.08em;
	}

	.audience-layout h3 {
		font-size: 26px;
		line-height: 1.35;
		letter-spacing: -.04em;
		margin: var(--space-4) 0;
	}

	.audience-layout article > p {
		font-size: var(--text-sm);
		color: var(--color-text-muted);
		line-height: 1.7;
		margin: 0 0 var(--space-4);
	}

	.employee-note {
		background: var(--color-light);
		border-radius: var(--radius-md);
		padding: var(--space-5);
		margin-top: var(--space-6);
		display: flex;
		gap: var(--space-4);
		align-items: center;
	}

	.employee-note > span {
		display: grid;
		place-items: center;
		width: 30px;
		height: 30px;
		border-radius: 50%;
		background: var(--color-primary);
		color: var(--color-inverse);
		flex-shrink: 0;
		font-weight: 700;
	}

	.employee-note p {
		font-size: var(--text-xs);
		margin: 0;
		line-height: 1.6;
	}

	.finance-note {
		margin-top: var(--space-6);
	}

	.finance-note > div {
		display: flex;
		justify-content: space-between;
		gap: var(--space-3);
		padding-block: var(--space-3);
		border-bottom: 1px solid var(--color-border);
		font-size: var(--text-xs);
	}

	.finance-note span {
		color: var(--color-text-muted);
	}

	.finance-note strong {
		font-weight: 600;
		text-align: right;
	}

	/* FAQ */
	.faq-section {
		display: grid;
		grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr);
		gap: var(--space-16);
		padding-bottom: 104px;
		scroll-margin-top: var(--space-6);
	}

	.faq-intro p {
		margin-block: var(--space-5);
		color: var(--color-text-muted);
		font-size: var(--text-sm);
		max-width: 320px;
	}

	.faq-list details {
		border-bottom: 1px solid var(--color-border);
		transition: background-color 0.2s ease;
	}

	.faq-list details:first-child {
		border-top: 1px solid var(--color-border);
	}

	.faq-list summary {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-5);
		padding-block: var(--space-6);
		font-size: var(--text-sm);
		font-weight: 600;
		cursor: pointer;
		list-style: none;
	}

	.faq-list summary::-webkit-details-marker {
		display: none;
	}

	.faq-list summary::after {
		content: '+';
		color: var(--color-primary);
		font-size: 22px;
		font-weight: 400;
		transition: transform 0.2s ease;
	}

	.faq-list details[open] summary::after {
		content: '−';
	}

	.faq-list details p {
		margin: 0;
		padding-bottom: var(--space-6);
		padding-right: var(--space-8);
		color: var(--color-text-muted);
		font-size: var(--text-sm);
		line-height: 1.8;
	}

	/* Closing */
	.closing {
		position: relative;
		isolation: isolate;
		overflow: clip;
		display: grid;
		grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr);
		align-items: center;
		gap: var(--space-8);
		background: var(--color-ink);
		color: var(--color-inverse);
		border-radius: var(--radius-lg);
		padding: var(--space-12);
		box-shadow: 0 24px 48px -12px rgba(0, 45, 40, 0.25);
	}

	.closing-copy > img {
		margin-bottom: var(--space-6);
	}

	.closing h2 {
		font-size: clamp(2rem, 3.2vw, 3rem);
	}

	.closing h2 span {
		color: var(--color-mint);
	}

	.closing-copy p {
		color: var(--color-light);
		font-size: var(--text-sm);
		margin: var(--space-6) 0;
	}

	.closing-button {
		color: var(--color-ink);
		background: var(--color-mint);
		border-color: var(--color-mint);
		flex-shrink: 0;
		border-radius: var(--radius-pill);
		font-weight: 650;
	}

	.closing-button:hover {
		background: var(--color-light);
		border-color: var(--color-light);
	}

	.landing-footer {
		display: flex;
		align-items: center;
		gap: var(--space-6);
		padding-block: var(--space-10);
	}

	.landing-footer .wordmark span {
		font-size: 23px;
	}

	.landing-footer p {
		margin: 0 auto 0 0;
		font-size: var(--text-xs);
		color: var(--color-text-muted);
	}

	.landing-footer > a:not(.wordmark) {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		text-decoration: none;
		min-height: 44px;
		display: flex;
		align-items: center;
		white-space: nowrap;
	}

	@media (max-width: 960px) {
		.landing { --nav-offset: 106px; }
		.landing-header { min-height: 72px; flex-wrap: wrap; gap: var(--space-3); position: relative; }
		.landing-header nav { position: absolute; top: calc(100% - 4px); left: 0; display: grid; grid-template-rows: 0fr; align-items: stretch; width: 100%; padding: 0 var(--space-5); gap: 0; background: var(--color-surface); border-radius: var(--radius-md); box-shadow: 0 14px 28px rgba(0, 45, 40, 0.1); visibility: hidden; transition: grid-template-rows 240ms ease, visibility 240ms; }
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
	}

	@media (max-width: 768px) {
		.landing { --nav-offset: 88px; }
		.landing-header, .hero, .workflow-section, .team-section, .faq-section, .closing, .landing-footer { width: calc(100% - 40px); }
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
		.workflow-section { padding-block: var(--space-16); }
		.section-intro, .workflow-layout, .audience-layout { grid-template-columns: minmax(0, 1fr); gap: var(--space-8); }
		.workflow-detail { padding: var(--space-6); min-height: 340px; }
		.team-section { padding-bottom: var(--space-16); }
		.faq-section { grid-template-columns: minmax(0, 1fr); gap: var(--space-8); padding-bottom: var(--space-16); }
		.audience-layout { gap: var(--space-8); }
		.closing { grid-template-columns: minmax(0, 1fr); padding: var(--space-8) var(--space-6) var(--space-12); }
		.landing-footer { flex-wrap: wrap; gap: var(--space-3) var(--space-5); }
		.landing-footer p { flex-basis: calc(100% - 110px); margin: 0; }
	}

	@media (max-width: 374px) {
		.nav-cta { font-size: 11px; }
		.menu-toggle { padding-inline: var(--space-3); font-size: 11px; }
	}

	@media (max-width: 960px) and (prefers-reduced-motion: reduce) {
		.landing-header nav { transition: none; }
	}

	@media (prefers-reduced-motion: reduce) {
		.product-panel, .product-trigger svg, .marquee-track, .step-progress-bar, .aura-1, .aura-2 {
			animation: none !important;
			transition: none !important;
		}
	}
</style>
