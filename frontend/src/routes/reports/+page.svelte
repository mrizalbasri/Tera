<script lang="ts">
	import { onMount } from 'svelte';
	import { downloadReport, getReportSummary, type ReportSummary, type ReportFilters } from '$lib/api/reports';

	let summary = $state<ReportSummary | null>(null);
	let error = $state('');
	let exportError = $state('');
	let validationError = $state('');
	let busy = $state(true);
	let exporting = $state(false);

	// Kontrol filter
	let periodFrom = $state('');
	let periodTo = $state('');
	let employeeId = $state('');
	let appliedFilters = $state<ReportFilters>({});

	// Request sequence token to prevent out-of-order race conditions
	let loadSeq = 0;

	const outcomes = $derived(summary ? [
		{ label: 'Disetujui', value: summary.approved_claims },
		{ label: 'Ditolak', value: summary.rejected_claims },
		{ label: 'Menunggu tindak lanjut', value: summary.pending_claims }
	] : []);

	const hasActiveFilters = $derived(
		Boolean(appliedFilters.periodFrom || appliedFilters.periodTo || appliedFilters.employeeId)
	);

	onMount(() => { void load(); });

	async function load() {
		const currentSeq = ++loadSeq;
		busy = true;
		error = '';
		try {
			const res = await getReportSummary(appliedFilters);
			if (currentSeq === loadSeq) {
				summary = res;
			}
		} catch (cause) {
			if (currentSeq === loadSeq) {
				error = cause instanceof Error ? cause.message : 'Laporan tidak dapat dimuat.';
			}
		} finally {
			if (currentSeq === loadSeq) {
				busy = false;
			}
		}
	}

	function applyFilters() {
		validationError = '';
		if (periodFrom && periodTo && periodFrom > periodTo) {
			validationError = 'Tanggal awal tidak boleh melebihi tanggal akhir.';
			return;
		}

		appliedFilters = {
			periodFrom: periodFrom || undefined,
			periodTo: periodTo || undefined,
			employeeId: employeeId.trim() || undefined
		};

		void load();
	}

	function resetFilters() {
		periodFrom = '';
		periodTo = '';
		employeeId = '';
		validationError = '';
		appliedFilters = {};
		void load();
	}

	async function exportCsv() {
		if (exporting) return;
		exporting = true;
		exportError = '';
		try {
			const blob = await downloadReport(appliedFilters);
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = url;
			const fromLabel = appliedFilters.periodFrom ?? 'awal';
			const toLabel = appliedFilters.periodTo ?? 'akhir';
			const empLabel = appliedFilters.employeeId ? `-${appliedFilters.employeeId}` : '';
			anchor.download = `laporan-klaim-tera-${fromLabel}-sd-${toLabel}${empLabel}.csv`;
			anchor.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		} catch (cause) {
			exportError = cause instanceof Error ? cause.message : 'Laporan gagal diunduh. Coba lagi.';
		} finally {
			exporting = false;
		}
	}
</script>

<svelte:head><title>Laporan · Tera</title></svelte:head>

<section class="reports-page">
	<header class="page-header">
		<div>
			<h1>Laporan klaim</h1>
			<p class="lead">Pengajuan, keputusan, dan hasil pemeriksaan dalam satu ringkasan.</p>
		</div>
		<button
			type="button"
			class="button"
			onclick={exportCsv}
			disabled={busy || !!error || exporting || !!validationError}
		>
			{exporting ? 'Mengunduh...' : 'Unduh CSV'}
		</button>
	</header>

	<!-- Filter Panel: Kontrol tanggal awal/akhir dan karyawan -->
	<section class="filter-panel" aria-label="Filter laporan klaim">
		<form class="filter-grid" onsubmit={(e) => { e.preventDefault(); applyFilters(); }}>
			<div class="filter-field">
				<label for="filter-from">Periode dari</label>
				<input
					type="date"
					id="filter-from"
					bind:value={periodFrom}
					aria-invalid={!!validationError}
				/>
			</div>
			<div class="filter-field">
				<label for="filter-to">Periode sampai</label>
				<input
					type="date"
					id="filter-to"
					bind:value={periodTo}
					aria-invalid={!!validationError}
				/>
			</div>
			<div class="filter-field">
				<label for="filter-emp">ID Karyawan</label>
				<input
					type="text"
					id="filter-emp"
					placeholder="Contoh: salesman-001"
					bind:value={employeeId}
				/>
			</div>
			<div class="filter-actions">
				<button type="submit" class="button secondary btn-apply" disabled={busy}>
					Terapkan
				</button>
				{#if hasActiveFilters || periodFrom || periodTo || employeeId}
					<button type="button" class="button subtle btn-reset" onclick={resetFilters} disabled={busy}>
						Reset
					</button>
				{/if}
			</div>
		</form>

		{#if validationError}
			<p class="filter-validation-error" role="alert">{validationError}</p>
		{/if}

		{#if hasActiveFilters}
			<div class="active-filter-chips">
				<span class="active-label">Filter aktif:</span>
				{#if appliedFilters.periodFrom}
					<span class="chip">Dari: {appliedFilters.periodFrom}</span>
				{/if}
				{#if appliedFilters.periodTo}
					<span class="chip">Sampai: {appliedFilters.periodTo}</span>
				{/if}
				{#if appliedFilters.employeeId}
					<span class="chip">Karyawan: {appliedFilters.employeeId}</span>
				{/if}
			</div>
		{/if}
	</section>

	{#if exportError}
		<p class="notice" role="alert">{exportError}</p>
	{/if}

	{#if busy}
		<div class="report-state" role="status">Memuat laporan klaim...</div>
	{:else if error}
		<div class="report-state" role="alert">
			<h2>Laporan belum dapat dimuat</h2>
			<p>{error}</p>
			<button type="button" class="button" onclick={load}>Coba lagi</button>
		</div>
	{:else if summary}
		{#if summary.total_claims === 0}
			<div class="report-state">
				<img src="/logo.webp" width="48" height="48" alt="" />
				<h2>Belum ada pengajuan dalam laporan.</h2>
				<p>
					{hasActiveFilters
						? 'Tidak ada pengajuan yang cocok dengan filter yang dipilih. Coba sesuaikan rentang tanggal atau ID karyawan.'
						: 'Kirim nota pertama untuk mulai mencatat pengeluaran dan hasil pemeriksaannya.'}
				</p>
				{#if hasActiveFilters}
					<button type="button" class="button secondary" onclick={resetFilters}>Reset filter</button>
				{:else}
					<a class="button" href="/pengajuan">Ajukan klaim</a>
				{/if}
			</div>
		{:else}
			<div class="report-overview">
				<div class="report-total">
					<span>Total pengajuan</span>
					<strong>{summary.total_claims}</strong>
					<p>Klaim tercatat</p>
				</div>
				<dl class="outcome-list">
					{#each outcomes as outcome}
						<div>
							<dt>{outcome.label}</dt>
							<dd>{outcome.value}</dd>
						</div>
					{/each}
				</dl>
			</div>

			<section class="report-breakdown">
				<h2>Hasil pemeriksaan</h2>
				<dl>
					<div>
						<dt>Diproses otomatis</dt>
						<dd>{summary.automated_claims}</dd>
					</div>
					<div>
						<dt>Melalui review manual</dt>
						<dd>{summary.manual_claims}</dd>
					</div>
					<div>
						<dt>Temuan duplikat</dt>
						<dd>{summary.duplicate_count}</dd>
					</div>
					<div>
						<dt>Pemeriksaan anomali</dt>
						<dd>{summary.anomaly_count}</dd>
					</div>
					<div>
						<dt>Rata-rata durasi proses</dt>
						<dd>
							{summary.average_duration_ms != null
								? `${Math.round(summary.average_duration_ms / 1000)} detik`
								: 'Belum tersedia'}
						</dd>
					</div>
					<div>
						<dt>Waktu dihemat (estimasi)</dt>
						<dd>{summary.estimated_time_saved_minutes} menit</dd>
					</div>
				</dl>
			</section>

			<p class="report-note">
				Pemeriksaan anomali mencakup hasil tanpa indikasi risiko. Temuan duplikat dan pemeriksaan anomali dapat muncul pada klaim yang sama. Estimasi waktu dihemat menggunakan asumsi review manual 5 menit per nota. Unduh CSV untuk melihat rincian pengajuan.
			</p>
		{/if}
	{/if}
</section>

<style>
	/* Hallmark · genre: modern-minimal · macrostructure: Workbench · design-system: DESIGN.md · designed-as-app */
	.reports-page { max-width: 1040px; }
	.page-header { display: flex; justify-content: space-between; gap: var(--space-6); margin-bottom: var(--space-6); }
	.lead { margin-bottom: 0; }

	/* Filter panel */
	.filter-panel {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		padding: var(--space-5) var(--space-6);
		margin-bottom: var(--space-8);
	}
	.filter-grid {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--space-4);
	}
	.filter-field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 160px;
		flex: 1;
	}
	.filter-field label {
		font-size: var(--text-xs);
		font-weight: 600;
		color: var(--color-text-muted);
	}
	.filter-field input {
		background: var(--color-bg, #ffffff);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		min-height: 44px;
		padding: var(--space-3);
		font-size: var(--text-sm);
		font-family: inherit;
		color: var(--color-text);
		transition: border-color 0.15s ease;
	}
	.filter-field input:focus {
		border-color: var(--color-primary, #0f766e);
	}
	.filter-field input[aria-invalid="true"] {
		border-color: #b91c1c;
	}
	.filter-actions {
		display: flex;
		gap: var(--space-2);
		align-items: center;
	}
	.btn-apply {
		min-height: 44px;
		padding: 0 var(--space-4);
		font-size: var(--text-sm);
		font-weight: 600;
	}
	.btn-reset {
		min-height: 44px;
		padding: 0 var(--space-4);
		font-size: var(--text-sm);
		color: var(--color-text-muted);
		background: none;
		border: 1px solid transparent;
		cursor: pointer;
	}
	.btn-reset:hover {
		color: var(--color-text);
		text-decoration: underline;
	}
	.filter-validation-error {
		margin: var(--space-3) 0 0;
		font-size: var(--text-xs);
		color: #b91c1c;
		font-weight: 600;
	}
	.active-filter-chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		align-items: center;
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px solid var(--color-border);
	}
	.active-label {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
		font-weight: 600;
	}
	.chip {
		background: var(--color-light, #f0fdf4);
		color: var(--color-primary, #0f766e);
		border: 1px solid var(--color-border);
		font-size: var(--text-xs);
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: var(--radius-sm);
	}

	.report-overview { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: var(--space-16); padding-block: var(--space-8); border-block: 1px solid var(--color-border); }
	.report-total > span { color: var(--color-text-muted); font-size: var(--text-sm); }
	.report-total strong { display: block; font-size: 64px; line-height: 1.3; font-weight: 650; letter-spacing: -.06em; font-variant-numeric: tabular-nums; }
	.report-total p { color: var(--color-text-muted); margin: 0; font-size: var(--text-xs); }
	dl { margin: 0; }
	dl > div { display: flex; align-items: center; justify-content: space-between; gap: var(--space-5); padding-block: var(--space-5); border-bottom: 1px solid var(--color-border); }
	.outcome-list > div:last-child { border-bottom: 0; }
	dt { color: var(--color-text-muted); font-size: var(--text-sm); }
	dd { margin: 0; font-weight: 650; font-size: var(--text-xl); font-variant-numeric: tabular-nums; }
	.report-breakdown { margin-top: var(--space-12); }
	.report-breakdown dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: var(--space-12); }
	.report-note { font-size: var(--text-xs); color: var(--color-text-muted); margin-top: var(--space-6); }
	.report-state { text-align: center; padding: var(--space-16) var(--space-6); border: 1px solid var(--color-border); background: var(--color-surface); border-radius: var(--radius-md); }
	.report-state h2 { margin-top: var(--space-5); }
	.report-state p { max-width: 480px; margin: 0 auto var(--space-6); color: var(--color-text-muted); }
	.notice { color: #b91c1c; font-size: var(--text-sm); margin: var(--space-3) 0; }
	@media (max-width: 768px) { .report-overview, .report-breakdown dl { grid-template-columns: minmax(0, 1fr); gap: var(--space-6); } }
</style>
