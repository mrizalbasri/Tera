<script>
	
	let activeTimeTab = $state('MONTHLY');

	let stats = [
		{ title: 'Total Klaim Bulan Ini', value: 'Rp 48.65M', sub: '342 Nota Diproses', bg: 'linear-gradient(135deg, #7c3aed, #a855f7)', icon: '💳' },
		{ title: 'Otonom AI (Auto-Approve)', value: '84.5%', sub: 'Target BRD: ≥ 70%', bg: 'linear-gradient(135deg, #2563eb, #38bdf8)', icon: '⚡' },
		{ title: 'Waktu Kerja Dihemat', value: '114 Jam', sub: 'Target 105 Jam Tercapai', bg: 'linear-gradient(135deg, #e11d48, #fb7185)', icon: '⏱️' },
		{ title: 'Anomali / Kebocoran', value: '18 Kasus', sub: 'Terdeteksi & Dicegah', bg: 'linear-gradient(135deg, #ea580c, #f59e0b)', icon: '🛡️' }
	];

	let recentClaims = [
		{ id: 'CLM-1042', user: 'Budi Santoso', category: 'Hotel Surabaya', amount: 'Rp 650.000', status: 'Review', statusClass: 'warning', time: '10 mnt lalu' },
		{ id: 'CLM-1041', user: 'Fajar Nugraha', category: 'BBM Pertamina', amount: 'Rp 140.000', status: 'Approved', statusClass: 'success', time: '25 mnt lalu' },
		{ id: 'CLM-1040', user: 'Andi Wijaya', category: 'Tol Cipali', amount: 'Rp 45.000', status: 'Approved', statusClass: 'success', time: '1 jam lalu' },
		{ id: 'CLM-1039', user: 'Siti Rahma', category: 'Makan Dinas', amount: 'Rp 180.000', status: 'Rejected', statusClass: 'danger', time: '2 jam lalu' }
	];

	function downloadReport() {
		alert('📥 Laporan spreadsheet analitik berhasil di-generate!');
	}
</script>

<svelte:head>
	<title>Expense Agent - Modern Analytics Dashboard</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
</svelte:head>

<div class="dashboard-wrapper">
	<!-- Top Navigation Bar -->
	<header class="top-nav">
		<div class="brand">
			<a href="/" class="brand-logo">
				<span class="logo-dot"></span>
				ExpenseAgent
			</a>
			<span class="page-title">/ Analytics Dashboard</span>
		</div>

		<div class="top-controls">
			<div class="search-pill">
				<span class="icon">🔍</span>
				<input type="text" placeholder="Search claims, salesman, receipts..." />
			</div>
			<a href="/review" class="alert-pill">
				<span class="ping"></span>
				3 Klaim Butuh Review
			</a>
			<button class="btn-action" onclick={downloadReport}>
				Export CSV
			</button>
		</div>
	</header>

	
	<section class="stat-cards-grid">
		{#each stats as card}
			<div class="gradient-card" style="background: {card.bg};">
				<div class="card-top">
					<span class="card-icon">{card.icon}</span>
					<span class="card-title">{card.title}</span>
				</div>
				<div class="card-value">{card.value}</div>
				<div class="card-sub">{card.sub}</div>
				<!-- Hiasan gelombang kartu -->
				<div class="card-wave"></div>
			</div>
		{/each}
	</section>

	
	<section class="visuals-grid">
		<!-- Left: Smooth Area Spline Chart (Grafik Gelombang Halus) -->
		<div class="card-panel chart-panel">
			<div class="panel-header">
				<div>
					<h3>Volume Klaim & Efisiensi AI</h3>
					<p class="panel-sub">Tren klaim yang diproses otonom vs yang dieskalasi ke manusia</p>
				</div>
				<div class="time-tabs">
					<button class:active={activeTimeTab === 'WEEKLY'} onclick={() => activeTimeTab = 'WEEKLY'}>Weekly</button>
					<button class:active={activeTimeTab === 'MONTHLY'} onclick={() => activeTimeTab = 'MONTHLY'}>Monthly</button>
					<button class:active={activeTimeTab === 'YEARLY'} onclick={() => activeTimeTab = 'YEARLY'}>Yearly</button>
				</div>
			</div>

			<div class="chart-container">
				<svg viewBox="0 0 650 200" class="spline-svg" preserveAspectRatio="none">
					<defs>
						<linearGradient id="purpleGlow" x1="0%" y1="0%" x2="0%" y2="100%">
							<stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.45" />
							<stop offset="100%" stop-color="#ec4899" stop-opacity="0.02" />
						</linearGradient>
						<linearGradient id="blueGlow" x1="0%" y1="0%" x2="0%" y2="100%">
							<stop offset="0%" stop-color="#38bdf8" stop-opacity="0.3" />
							<stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0" />
						</linearGradient>
					</defs>

					
					<line x1="0" y1="40" x2="650" y2="40" stroke="#f1f5f9" stroke-width="1" />
					<line x1="0" y1="90" x2="650" y2="90" stroke="#f1f5f9" stroke-width="1" />
					<line x1="0" y1="140" x2="650" y2="140" stroke="#f1f5f9" stroke-width="1" />

					
					<path
						d="M 0,150 Q 80,120 160,80 T 320,60 T 480,45 T 650,25 L 650,200 L 0,200 Z"
						fill="url(#purpleGlow)"
					/>
					<path
						d="M 0,150 Q 80,120 160,80 T 320,60 T 480,45 T 650,25"
						fill="none"
						stroke="#8b5cf6"
						stroke-width="3.5"
						stroke-linecap="round"
					/>

					
					<path
						d="M 0,180 Q 90,165 170,150 T 330,135 T 490,140 T 650,130 L 650,200 L 0,200 Z"
						fill="url(#blueGlow)"
					/>
					<path
						d="M 0,180 Q 90,165 170,150 T 330,135 T 490,140 T 650,130"
						fill="none"
						stroke="#06b6d4"
						stroke-width="2.5"
						stroke-dasharray="4,4"
					/>

			
					<circle cx="480" cy="45" r="5" fill="#7c3aed" stroke="#ffffff" stroke-width="3" />
					<circle cx="650" cy="25" r="5" fill="#ec4899" stroke="#ffffff" stroke-width="3" />
				</svg>

				<div class="x-axis-labels">
					<span>Jan</span>
					<span>Feb</span>
					<span>Mar</span>
					<span>Apr</span>
					<span>Mei</span>
					<span>Jun</span>
					<span>Jul</span>
					<span>Agu</span>
					<span>Sep</span>
					<span>Okt</span>
				</div>
			</div>

			<div class="chart-badges-row">
				<div class="legend-badge">
					<span class="indicator purple"></span>
					<strong>84.5% Otonom AI</strong>
					<span class="muted">(289 klaim langsung approve)</span>
				</div>
				<div class="legend-badge">
					<span class="indicator blue"></span>
					<strong>15.5% Eskalasi</strong>
					<span class="muted">(53 klaim butuh review)</span>
				</div>
			</div>
		</div>

		
		<div class="card-panel donut-panel">
			<div class="panel-header">
				<div>
					<h3>Distribusi Biaya</h3>
					<p class="panel-sub">Pengeluaran FMCG per Kategori</p>
				</div>
			</div>

			<div class="donut-wrapper">
				<div class="donut-circle">
					<div class="donut-hole">
						<span class="donut-main-number">84%</span>
						<span class="donut-sub-text">Efisiensi AI</span>
					</div>
				</div>
			</div>

			<div class="category-pills">
				<div class="cat-pill">
					<span class="dot bbm"></span>
					<span class="name">BBM Lapangan</span>
					<strong>42%</strong>
				</div>
				<div class="cat-pill">
					<span class="dot makan"></span>
					<span class="name">Makan Dinas</span>
					<strong>31%</strong>
				</div>
				<div class="cat-pill">
					<span class="dot hotel"></span>
					<span class="name">Hotel / Stay</span>
					<strong>22%</strong>
				</div>
				<div class="cat-pill">
					<span class="dot tol"></span>
					<span class="name">Tol & Parkir</span>
					<strong>5%</strong>
				</div>
			</div>
		</div>
	</section>


	<section class="card-panel table-panel">
		<div class="panel-header">
			<div>
				<h3>Klaim Terbaru Diproses</h3>
				<p class="panel-sub">Aktivitas real-time pemrosesan nota karyawan FMCG</p>
			</div>
			<a href="/review" class="btn-text-link">Buka Antrean Review Lengkap →</a>
		</div>

		<div class="table-responsive">
			<table class="modern-table">
				<thead>
					<tr>
						<th>ID Nota</th>
						<th>Salesman</th>
						<th>Kategori</th>
						<th>Nominal</th>
						<th>Waktu</th>
						<th>Status</th>
						<th>Aksi</th>
					</tr>
				</thead>
				<tbody>
					{#each recentClaims as claim}
						<tr>
							<td><span class="id-tag">#{claim.id}</span></td>
							<td><strong>{claim.user}</strong></td>
							<td><span class="cat-badge">{claim.category}</span></td>
							<td class="amount">{claim.amount}</td>
							<td class="time-col">{claim.time}</td>
							<td>
								<span class="status-pill {claim.statusClass}">
									{claim.status}
								</span>
							</td>
							<td>
								<a href="/review" class="table-link">Lihat Detail</a>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>
</div>

<style>
	:global(body) {
		margin: 0;
		background: #f1f4f9;
		font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
		color: #1e293b;
	}

	.dashboard-wrapper {
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

	.search-pill {
		background: #ffffff;
		border-radius: 999px;
		padding: 0.55rem 1.1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		box-shadow: 0 2px 6px rgba(0,0,0,0.02);
		border: 1px solid #e2e8f0;
	}

	.search-pill input {
		border: none;
		outline: none;
		font-family: inherit;
		font-size: 0.85rem;
		width: 220px;
	}

	.alert-pill {
		background: #fff7ed;
		color: #c2410c;
		border: 1px solid #ffedd5;
		padding: 0.55rem 1rem;
		border-radius: 999px;
		font-weight: 700;
		font-size: 0.82rem;
		text-decoration: none;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		transition: all 0.2s;
	}

	.alert-pill:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 10px rgba(234, 88, 12, 0.15);
	}

	.ping {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #ea580c;
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

	/* 4 Gradient Stat Cards */
	.stat-cards-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
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
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	.gradient-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 16px 25px -5px rgba(0, 0, 0, 0.2);
	}

	.card-top {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.6rem;
	}

	.card-icon {
		font-size: 1.1rem;
	}

	.card-title {
		font-size: 0.82rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		opacity: 0.9;
	}

	.card-value {
		font-size: 2.2rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		line-height: 1.1;
		margin-bottom: 0.4rem;
	}

	.card-sub {
		font-size: 0.82rem;
		opacity: 0.85;
		font-weight: 500;
	}

	.card-wave {
		position: absolute;
		right: -20px;
		bottom: -20px;
		width: 110px;
		height: 110px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.12);
		pointer-events: none;
	}

	/* Main Panels */
	.visuals-grid {
		display: grid;
		grid-template-columns: 2fr 1fr;
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	@media (max-width: 992px) {
		.visuals-grid {
			grid-template-columns: 1fr;
		}
	}

	.card-panel {
		background: #ffffff;
		border-radius: 20px;
		padding: 1.8rem;
		box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
		border: 1px solid #f1f5f9;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1.5rem;
	}

	.panel-header h3 {
		margin: 0;
		font-size: 1.2rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: #0f172a;
	}

	.panel-sub {
		margin: 0.3rem 0 0;
		font-size: 0.82rem;
		color: #94a3b8;
	}

	.time-tabs {
		background: #f8fafc;
		border-radius: 999px;
		padding: 3px;
		display: flex;
		border: 1px solid #e2e8f0;
	}

	.time-tabs button {
		background: none;
		border: none;
		padding: 0.35rem 0.85rem;
		font-size: 0.78rem;
		font-weight: 700;
		color: #64748b;
		cursor: pointer;
		border-radius: 999px;
		transition: all 0.2s;
	}

	.time-tabs button.active {
		background: #7c3aed;
		color: #ffffff;
		box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);
	}

	/* SVG Area Chart */
	.chart-container {
		width: 100%;
		overflow: hidden;
	}

	.spline-svg {
		width: 100%;
		height: 180px;
		display: block;
	}

	.x-axis-labels {
		display: flex;
		justify-content: space-between;
		padding: 0.6rem 0.5rem 0;
		font-size: 0.75rem;
		font-weight: 600;
		color: #94a3b8;
	}

	.chart-badges-row {
		display: flex;
		gap: 1.5rem;
		margin-top: 1.2rem;
		padding-top: 1rem;
		border-top: 1px solid #f1f5f9;
	}

	.legend-badge {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
	}

	.indicator {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.indicator.purple { background: #8b5cf6; }
	.indicator.blue { background: #06b6d4; }

	.muted {
		color: #94a3b8;
		font-size: 0.78rem;
	}

	/* Donut Chart (Pinterest Style) */
	.donut-wrapper {
		display: flex;
		justify-content: center;
		margin: 1.2rem 0 1.5rem;
	}

	.donut-circle {
		width: 170px;
		height: 170px;
		border-radius: 50%;
		background: conic-gradient(
			#7c3aed 0% 42%,
			#3b82f6 42% 73%,
			#ec4899 73% 95%,
			#f59e0b 95% 100%
		);
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 8px 20px rgba(124, 58, 237, 0.15);
	}

	.donut-hole {
		width: 110px;
		height: 110px;
		background: #ffffff;
		border-radius: 50%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.donut-main-number {
		font-size: 1.7rem;
		font-weight: 800;
		color: #0f172a;
		letter-spacing: -0.03em;
		line-height: 1;
	}

	.donut-sub-text {
		font-size: 0.75rem;
		font-weight: 600;
		color: #94a3b8;
		margin-top: 0.2rem;
	}

	.category-pills {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}

	.cat-pill {
		display: flex;
		align-items: center;
		font-size: 0.82rem;
		padding: 0.5rem 0.7rem;
		background: #f8fafc;
		border-radius: 10px;
	}

	.cat-pill .dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 0.6rem;
	}
	.dot.bbm { background: #7c3aed; }
	.dot.makan { background: #3b82f6; }
	.dot.hotel { background: #ec4899; }
	.dot.tol { background: #f59e0b; }

	.cat-pill .name {
		flex: 1;
		color: #475569;
		font-weight: 500;
	}

	/* Table Section */
	.table-responsive {
		overflow-x: auto;
	}

	.modern-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
	}

	.modern-table th {
		padding: 0.85rem 1rem;
		color: #94a3b8;
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid #f1f5f9;
	}

	.modern-table td {
		padding: 1rem;
		font-size: 0.88rem;
		border-bottom: 1px solid #f8fafc;
	}

	.id-tag {
		background: #f1f5f9;
		color: #475569;
		font-weight: 700;
		font-size: 0.8rem;
		padding: 0.2rem 0.5rem;
		border-radius: 6px;
	}

	.cat-badge {
		color: #475569;
		font-weight: 500;
	}

	.amount {
		font-weight: 700;
		color: #0f172a;
	}

	.time-col {
		color: #94a3b8;
		font-size: 0.82rem;
	}

	.status-pill {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
	}

	.status-pill.success { background: #dcfce7; color: #15803d; }
	.status-pill.warning { background: #fef3c7; color: #b45309; }
	.status-pill.danger { background: #fee2e2; color: #b91c1c; }

	.table-link {
		color: #7c3aed;
		font-weight: 700;
		text-decoration: none;
		font-size: 0.82rem;
	}

	.table-link:hover {
		text-decoration: underline;
	}

	.btn-text-link {
		color: #7c3aed;
		font-weight: 700;
		font-size: 0.85rem;
		text-decoration: none;
	}
</style>