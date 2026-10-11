<script lang="ts">
	import { onMount } from 'svelte';
	import { downloadReport, getReportSummary, type ReportSummary } from '$lib/api/reports';

	let summary = $state<ReportSummary | null>(null);
	let error = $state('');
	let busy = $state(true);

	onMount(() => {
		void load();
	});

	async function load() {
		busy = true;
		try {
			summary = await getReportSummary();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Laporan tidak dapat dimuat.';
		} finally {
			busy = false;
		}
	}

	async function exportCsv() {
		try {
			const blob = await downloadReport();
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = url;
			anchor.download = 'claims-report.csv';
			anchor.click();
			URL.revokeObjectURL(url);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Export gagal.';
		}
	}
</script>

<svelte:head><title>Laporan Klaim</title></svelte:head>
<main class="page-shell">
	<div class="page-header">
		<div>
			<p class="eyebrow">REPORTING</p>
			<h1>Laporan Klaim</h1>
			<p class="scope-note">Ringkasan dan export dihitung oleh backend.</p>
		</div>
		<button type="button" onclick={exportCsv}>Export CSV</button>
	</div>
	{#if error}<p class="error">{error}</p>{/if}
	{#if busy}
		<p>Memuat laporan...</p>
	{:else if summary}
		<div class="metrics">
			{#each [
				['Total klaim', summary.total_claims],
				['Disetujui', summary.approved_claims],
				['Ditolak', summary.rejected_claims],
				['Menunggu', summary.pending_claims],
				['Duplikat', summary.duplicate_count],
				['Anomali', summary.anomaly_count],
				['Hemat waktu (menit)', summary.estimated_time_saved_minutes]
			] as metric}
				<div class="metric"><strong>{metric[1]}</strong><span>{metric[0]}</span></div>
			{/each}
		</div>
	{/if}
</main>

<style>
	.page-shell { max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }
	.page-header { display: flex; justify-content: space-between; gap: 1rem; align-items: center; }
	.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 2rem; }
	.metric { padding: 1rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	.metric strong, .metric span { display: block; }
	.metric strong { font-size: 1.5rem; }
	.metric span, .scope-note, .eyebrow { color: var(--color-text-muted); }
	.error { color: #b91c1c; }
</style>
