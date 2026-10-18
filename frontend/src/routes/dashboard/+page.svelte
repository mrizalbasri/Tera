<script lang="ts">
	import { onMount } from 'svelte';
	import { listClaims } from '$lib/api/claims';
	import { formatCurrency } from '$lib/formatters/currency';
	import { formatDateTime } from '$lib/formatters/date';
	import { shortClaimRef } from '$lib/formatters/claim';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import type { Claim } from '$lib/types/claim';

	let claims = $state<Claim[]>([]);
	let loading = $state(true);
	let error = $state('');
	let searchQuery = $state('');
	const approved = $derived(claims.filter((claim) => claim.status === 'approved').length);
	const review = $derived(claims.filter((claim) => claim.status === 'escalated').length);
	const clarification = $derived(claims.filter((claim) => claim.status === 'needs_clarification').length);
	const recent = $derived([...claims].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at)).slice(0, 8));
	const filteredRecent = $derived(
		recent.filter((claim) => {
			const q = searchQuery.trim().toLowerCase();
			if (!q) return true;
			return (
				shortClaimRef(claim.id).toLowerCase().includes(q) ||
				claim.employee_id.toLowerCase().includes(q) ||
				claim.status.toLowerCase().includes(q)
			);
		})
	);

	async function load() {
		loading = true;
		error = '';
		try {
			claims = (await listClaims()).items;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Ringkasan klaim tidak dapat dimuat.';
		} finally {
			loading = false;
		}
	}
	onMount(() => { void load(); });
</script>

<svelte:head><title>Ringkasan · Tera</title></svelte:head>
<section class="dashboard-page">
	<header class="page-header"><div><h1>Pengeluaran, dalam satu pandangan.</h1><p class="lead">Ikuti pengajuan terbaru dan lihat klaim yang membutuhkan perhatian.</p></div><a href="/reports" class="button secondary">Buka laporan</a></header>
	{#if loading}
		<div class="state-panel" role="status">Memuat ringkasan pengajuan...</div>
	{:else if error}
		<div class="state-panel" role="alert"><h2>Ringkasan belum dapat dimuat</h2><p>{error}</p><button type="button" onclick={load}>Coba lagi</button></div>
	{:else if claims.length === 0}
		<div class="dashboard-empty"><img src="/logo.webp" width="56" height="56" alt="" /><h2>Ringkasan dimulai dari nota pertama.</h2><p>Belum ada pengajuan untuk ditampilkan. Setelah nota dikirim, status dan aktivitas klaim akan muncul di sini.</p><a href="/pengajuan" class="button">Ajukan klaim</a></div>
	{:else}
		<dl class="dashboard-metrics"><div><dt>Klaim diajukan</dt><dd>{claims.length}</dd></div><div><dt>Disetujui</dt><dd>{approved}</dd></div><div><dt>Perlu review</dt><dd>{review}</dd></div><div><dt>Perlu klarifikasi</dt><dd>{clarification}</dd></div></dl>
		{#if review > 0 || clarification > 0}
			<div class="attention"><div><h2>Ada klaim yang perlu ditindaklanjuti.</h2><p>{review} pengajuan menunggu review dan {clarification} memerlukan informasi tambahan.</p></div><a class="button secondary" href={review > 0 ? '/reviews' : '/riwayat'}>{review > 0 ? 'Buka review' : 'Lihat riwayat'}</a></div>
		{/if}
		<section class="recent-claims">
			<div class="section-top">
				<div class="section-heading">
					<h2>Pengajuan terbaru</h2>
					<input
						type="search"
						bind:value={searchQuery}
						placeholder="Cari ref, karyawan, atau status..."
						aria-label="Filter pengajuan terbaru"
						class="search-input"
					/>
				</div>
				<a href="/riwayat">Lihat riwayat</a>
			</div>
			<div class="table-wrap" role="region" aria-label="Pengajuan terbaru">
				{#if filteredRecent.length === 0}
					<p class="search-empty">Tidak ada pengajuan terbaru yang cocok dengan pencarian "{searchQuery}".</p>
				{:else}
					<table>
						<thead><tr><th>Klaim</th><th>Karyawan</th><th>Diajukan</th><th>Nominal</th><th>Status</th><th><span class="sr-only">Detail</span></th></tr></thead>
						<tbody>
							{#each filteredRecent as claim (claim.id)}
								<tr>
									<td>{shortClaimRef(claim.id)}</td>
									<td>{claim.employee_id}</td>
									<td>{formatDateTime(claim.submitted_at)}</td>
									<td class="amount">{formatCurrency(claim.declared_amount, claim.currency)}</td>
									<td><StatusBadge status={claim.status} size="sm" /></td>
									<td>
										{#if claim.status === 'escalated'}
											<a class="detail-link review-link" href={`/reviews/${encodeURIComponent(claim.id)}`}>Tinjau klaim</a>
										{:else}
											<a class="detail-link" href={`/riwayat/${encodeURIComponent(claim.id)}`}>Lihat klaim</a>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</div>
		</section>
	{/if}
</section>

<style>
	/* Hallmark · genre: modern-minimal · macrostructure: Workbench · design-system: DESIGN.md · designed-as-app */
	.dashboard-page { max-width: 1120px; }
	.page-header { display: flex; justify-content: space-between; gap: var(--space-6); margin-bottom: var(--space-8); }
	.page-header h1 { max-width: 640px; }
	.lead { margin: var(--space-3) 0 0; }
	.dashboard-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); padding: var(--space-6) 0; margin: 0 0 var(--space-8); border-block: 1px solid var(--color-border); gap: var(--space-6); }
	.dashboard-metrics dt { color: var(--color-text-muted); font-size: var(--text-xs); }
	.dashboard-metrics dd { margin: var(--space-3) 0 0; font-size: 36px; font-weight: 650; letter-spacing: -.05em; font-variant-numeric: tabular-nums; }
	.attention { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-5); background: var(--color-light); padding: var(--space-6); border-radius: var(--radius-md); margin-bottom: var(--space-10); }
	.attention h2 { font-size: var(--text-md); margin: 0; }
	.attention p { margin: var(--space-2) 0 0; color: var(--color-text-muted); font-size: var(--text-xs); }
	.recent-claims { margin-top: var(--space-10); }
	.section-top { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-4); margin-bottom: var(--space-4); }
	.section-heading { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
	.section-top > a { font-size: var(--text-xs); display: inline-flex; align-items: center; min-height: 44px; white-space: nowrap; }
	.search-input {
		font-size: var(--text-xs);
		padding: 0.4rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-bg, #ffffff);
		color: var(--color-text);
		min-width: 220px;
	}
	.search-input:focus { border-color: var(--color-primary, #0f766e); outline: none; }
	.search-empty { padding: var(--space-6); color: var(--color-text-muted); font-size: var(--text-sm); text-align: center; }
	.review-link { font-weight: 600; color: #0f766e; }
	.dashboard-empty { padding: var(--space-20) var(--space-6); text-align: center; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
	.dashboard-empty h2 { font-size: var(--text-xl); margin: var(--space-6) 0 var(--space-3); }
	.dashboard-empty p { color: var(--color-text-muted); max-width: 480px; margin: 0 auto var(--space-6); }
	.state-panel { padding: var(--space-12); text-align: center; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: clip; clip-path: inset(50%); }
	@media (max-width: 768px) {
		.dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.dashboard-empty { padding-block: var(--space-12); }
		.section-top { flex-direction: column; align-items: stretch; }
		.search-input { width: 100%; min-width: 0; }
	}
</style>
