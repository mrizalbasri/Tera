<script lang="ts">
	import { onMount } from 'svelte';
	import { downloadReport, getReportSummary, type ReportSummary } from '$lib/api/reports';
	let summary = $state<ReportSummary | null>(null);
	let error = $state('');
	let exportError = $state('');
	let busy = $state(true);
	let exporting = $state(false);
	const outcomes = $derived(summary ? [
		{ label: 'Disetujui', value: summary.approved_claims },
		{ label: 'Ditolak', value: summary.rejected_claims },
		{ label: 'Menunggu tindak lanjut', value: summary.pending_claims }
	] : []);
	const approvedPct = $derived(summary ? Math.round((summary.approved_claims / (summary.total_claims || 1)) * 100) : 0);
	const rejectedPct = $derived(summary ? Math.round((summary.rejected_claims / (summary.total_claims || 1)) * 100) : 0);
	const pendingPct = $derived(summary ? Math.max(0, 100 - approvedPct - rejectedPct) : 0);
	const autoPct = $derived(summary ? Math.round((summary.automated_claims / (summary.total_claims || 1)) * 100) : 0);
	onMount(() => { void load(); });
	async function load() {
		busy = true;
		error = '';
		try { summary = await getReportSummary(); }
		catch (cause) { error = cause instanceof Error ? cause.message : 'Laporan tidak dapat dimuat.'; }
		finally { busy = false; }
	}
	async function exportCsv() {
		if (exporting) return;
		exporting = true;
		exportError = '';
		try {
			const blob = await downloadReport();
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = url;
			anchor.download = 'laporan-klaim-tera.csv';
			anchor.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		} catch (cause) { exportError = cause instanceof Error ? cause.message : 'Laporan gagal diunduh. Coba lagi.'; }
		finally { exporting = false; }
	}
</script>

<svelte:head><title>Laporan · Tera</title></svelte:head>
<section class="reports-page">
	<header class="page-header"><div><h1>Laporan klaim</h1><p class="lead">Pengajuan, keputusan, dan hasil pemeriksaan dalam satu ringkasan.</p></div><button type="button" onclick={exportCsv} disabled={busy || !!error || exporting}>{exporting ? 'Mengunduh...' : 'Unduh CSV'}</button></header>
	{#if exportError}<p class="notice" role="alert">{exportError}</p>{/if}
	{#if busy}<div class="report-state" role="status">Memuat laporan klaim...</div>
	{:else if error}<div class="report-state" role="alert"><h2>Laporan belum dapat dimuat</h2><p>{error}</p><button type="button" onclick={load}>Coba lagi</button></div>
	{:else if summary}
		{#if summary.total_claims === 0}
			<div class="report-state"><img src="/logo.webp" width="48" height="48" alt="" /><h2>Belum ada pengajuan dalam laporan.</h2><p>Kirim nota pertama untuk mulai mencatat pengeluaran dan hasil pemeriksaannya.</p><a class="button" href="/pengajuan">Ajukan klaim</a></div>
		{:else}
			<div class="report-overview">
				<div class="report-total">
					<span>Total pengajuan</span>
					<strong>{summary.total_claims}</strong>
					<p>Klaim tercatat</p>
				</div>
				<div class="outcome-col">
					<dl class="outcome-list">
						{#each outcomes as outcome}
							<div><dt>{outcome.label}</dt><dd>{outcome.value}</dd></div>
						{/each}
					</dl>
					<div class="ratio-bar-wrap">
						<div class="ratio-bar" role="progressbar" aria-label="Distribusi keputusan klaim" aria-valuenow={approvedPct} aria-valuemin="0" aria-valuemax="100">
							<div class="ratio-segment approved" style="width: {approvedPct}%;" title="Disetujui: {approvedPct}%"></div>
							<div class="ratio-segment pending" style="width: {pendingPct}%;" title="Menunggu: {pendingPct}%"></div>
							<div class="ratio-segment rejected" style="width: {rejectedPct}%;" title="Ditolak: {rejectedPct}%"></div>
						</div>
						<div class="ratio-legend">
							<span><span class="legend-dot approved"></span> Disetujui ({approvedPct}%)</span>
							<span><span class="legend-dot pending"></span> Menunggu ({pendingPct}%)</span>
							<span><span class="legend-dot rejected"></span> Ditolak ({rejectedPct}%)</span>
						</div>
					</div>
				</div>
			</div>
			<section class="report-breakdown">
				<h2>Hasil pemeriksaan</h2>
				<div class="automation-meter">
					<div class="meter-header">
						<span>Tingkat Otomatisasi AI Agent</span>
						<strong>{autoPct}% Otomatis</strong>
					</div>
					<div class="meter-bar">
						<div class="meter-fill" style="width: {autoPct}%;"></div>
					</div>
					<span class="meter-caption">{summary.automated_claims} dari {summary.total_claims} klaim diproses otomatis tanpa eskalasi manusia.</span>
				</div>
				<dl>
					<div><dt>Diproses otomatis</dt><dd>{summary.automated_claims}</dd></div>
					<div><dt>Melalui review manual</dt><dd>{summary.manual_claims}</dd></div>
					<div><dt>Temuan duplikat</dt><dd>{summary.duplicate_count}</dd></div>
					<div><dt>Temuan anomali</dt><dd>{summary.anomaly_count}</dd></div>
				</dl>
			</section>
			<p class="report-note">Temuan duplikat dan anomali dapat muncul pada klaim yang sama. Unduh CSV untuk melihat rincian pengajuan.</p>
		{/if}
	{/if}
</section>

<style>
	/* Hallmark · genre: modern-minimal · macrostructure: Workbench · design-system: DESIGN.md · designed-as-app */
	.reports-page { max-width: 1040px; }
	.page-header { display: flex; justify-content: space-between; gap: var(--space-6); margin-bottom: var(--space-10); }
	.lead { margin-bottom: 0; }
	.report-overview { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: var(--space-16); padding-block: var(--space-8); border-block: 1px solid var(--color-border); }
	.outcome-col { display: flex; flex-direction: column; gap: var(--space-6); justify-content: center; }
	.ratio-bar-wrap { display: flex; flex-direction: column; gap: var(--space-2); }
	.ratio-bar { display: flex; height: 10px; width: 100%; border-radius: var(--radius-pill); overflow: hidden; background: var(--color-border); }
	.ratio-segment.approved { background: var(--color-primary); }
	.ratio-segment.pending { background: var(--color-warning); }
	.ratio-segment.rejected { background: var(--color-danger); }
	.ratio-legend { display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: var(--text-xs); color: var(--color-text-muted); }
	.ratio-legend span { display: inline-flex; align-items: center; gap: var(--space-1); }
	.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
	.legend-dot.approved { background: var(--color-primary); }
	.legend-dot.pending { background: var(--color-warning); }
	.legend-dot.rejected { background: var(--color-danger); }

	.automation-meter { padding: var(--space-5); background: var(--color-soft); border-radius: var(--radius-md); margin-bottom: var(--space-6); display: flex; flex-direction: column; gap: var(--space-2); }
	.meter-header { display: flex; justify-content: space-between; align-items: center; font-size: var(--text-sm); }
	.meter-header strong { color: var(--color-primary-dark); font-variant-numeric: tabular-nums; }
	.meter-bar { height: 8px; width: 100%; border-radius: var(--radius-pill); background: var(--color-border); overflow: hidden; }
	.meter-fill { height: 100%; background: var(--color-primary); border-radius: var(--radius-pill); transition: width var(--transition); }
	.meter-caption { font-size: var(--text-xs); color: var(--color-text-muted); }

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
	@media (max-width: 768px) { .report-overview, .report-breakdown dl { grid-template-columns: minmax(0, 1fr); gap: var(--space-6); } }
</style>
