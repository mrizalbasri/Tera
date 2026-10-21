<script lang="ts">
	import { onMount } from 'svelte';
	import { listClaims, CURRENT_EMPLOYEE_ID } from '$lib/api/claims';
	import { formatCurrency } from '$lib/formatters/currency';
	import { formatDate } from '$lib/formatters/date';
	import { shortClaimRef } from '$lib/formatters/claim';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import type { Claim, ClaimStatus } from '$lib/types/claim';

	let { data } = $props();
	let claims = $state<Claim[]>([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	const labels: Record<ClaimStatus, string> = {
		received: 'diterima', processing: 'diproses', needs_clarification: 'perlu klarifikasi',
		escalated: 'perlu review', approved: 'disetujui', rejected: 'ditolak'
	};
	const ordered = $derived([...claims].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at)));
	const approved = $derived(claims.filter((claim) => claim.status === 'approved').length);
	const processing = $derived(claims.filter((claim) => ['received', 'processing', 'escalated'].includes(claim.status)).length);
	const needsAction = $derived(ordered.filter((claim) => data.admin ? claim.status === 'escalated' : claim.status === 'needs_clarification'));
	const matches = $derived(ordered.filter((claim) => `${claim.id} ${shortClaimRef(claim.id)} ${claim.employee_id} ${claim.status} ${labels[claim.status]} ${claim.declared_amount ?? ''}`.toLowerCase().includes(search.trim().toLowerCase())));
	const recent = $derived(matches.slice(0, 8));
	const reviewCount = $derived(claims.filter((claim) => claim.status === 'escalated').length);
	const clarificationCount = $derived(claims.filter((claim) => claim.status === 'needs_clarification').length);

	function destination(claim: Claim) {
		if (data.admin && claim.status === 'escalated') return `/reviews/${encodeURIComponent(claim.id)}`;
		if (data.admin) return `/admin/claims/${encodeURIComponent(claim.id)}`;
		if (claim.status === 'needs_clarification') return `/claims/${encodeURIComponent(claim.id)}/clarification`;
		return `/riwayat/${encodeURIComponent(claim.id)}`;
	}
	async function load() {
		loading = true;
		error = '';
		try {
			const employee = data.admin ? undefined : data.demoMode ? CURRENT_EMPLOYEE_ID : data.user?.username;
			claims = (await listClaims(employee)).items;
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Ringkasan klaim tidak dapat dimuat.';
		} finally { loading = false; }
	}
	onMount(() => { void load(); });
</script>

<svelte:head><title>Dashboard · Tera</title></svelte:head>
<section class="dashboard-page">
	<header class="page-header">
		<div><p class="workspace-caption">Ruang kerja {data.admin ? 'tim keuangan' : 'karyawan'}</p><h1>{data.admin ? 'Ringkasan operasional' : 'Ringkasan klaim saya'}</h1><p class="lead">{data.admin ? 'Pantau hasil pemeriksaan Tera dan pekerjaan yang membutuhkan reviewer.' : 'Pantau klaim, lalu lanjutkan yang perlu perhatian.'}</p></div>
		<a href={data.admin ? '/reviews' : '/pengajuan'} class="button">{data.admin ? 'Buka antrean review' : 'Ajukan klaim'}</a>
	</header>
	{#if loading}
		<div class="state-panel" role="status">Memuat ringkasan pengajuan…</div>
	{:else if error}
		<div class="state-panel" role="alert"><h2>Ringkasan belum dapat dimuat</h2><p>{error}</p><button type="button" onclick={load}>Coba lagi</button></div>
	{:else}
		<dl class="dashboard-metrics">
			<div><dt>Total pengajuan</dt><dd>{claims.length}<span>klaim tercatat</span></dd></div>
			<div><dt>Dalam pemeriksaan</dt><dd>{processing}<span>termasuk antrean review</span></dd></div>
			<div><dt>Disetujui</dt><dd>{approved}<span>keputusan tersimpan</span></dd></div>
			<div class:attention={needsAction.length > 0}><dt>Perlu perhatian</dt><dd>{needsAction.length}<span>tindak lanjut tersedia</span></dd></div>
		</dl>
		<div class="dashboard-grid">
			<section class="recent-claims surface" aria-labelledby="recent-title">
				<div class="panel-heading"><div><h2 id="recent-title">Pengajuan terbaru</h2><p>{claims.length ? 'Status terbaru dari pengajuan yang tercatat.' : 'Pengajuan akan muncul setelah karyawan mengirim nota.'}</p></div><a href={data.admin ? '/admin/claims' : '/riwayat'}>Lihat semua</a></div>
				{#if claims.length}
					<label class="search-label" for="claim-search">Cari klaim</label>
					<input id="claim-search" class="claim-search" type="search" bind:value={search} placeholder="Referensi, karyawan, nominal, atau status" />
					{#if recent.length}
						<!-- Keyboard users need a focusable region to scroll the wide table. -->
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<div class="table-wrap" role="region" aria-label="Pengajuan terbaru" tabindex="0">
							<table><thead><tr><th>Klaim</th><th>Nominal</th><th>Status</th><th><span class="sr-only">Tindakan</span></th></tr></thead>
								<tbody>{#each recent as claim (claim.id)}<tr>
									<td><strong>{shortClaimRef(claim.id)}</strong><small>{formatDate(claim.submitted_at)}{#if data.admin} · {claim.employee_id}{/if}</small></td>
									<td class="amount">{formatCurrency(claim.declared_amount, claim.currency)}</td>
									<td><StatusBadge status={claim.status} size="sm" /></td>
									<td><a class="detail-link" href={destination(claim)}>{claim.status === 'escalated' && data.admin ? 'Tinjau' : claim.status === 'needs_clarification' && !data.admin ? 'Lengkapi' : 'Detail'}<span class="sr-only"> klaim {shortClaimRef(claim.id)}</span></a></td>
								</tr>{/each}</tbody>
							</table>
						</div>
						<p class="table-note">Menampilkan {recent.length} dari {matches.length} klaim{search.trim() ? ' yang cocok' : ''}.</p>
					{:else}<div class="empty-panel"><h3>Klaim tidak ditemukan</h3><p>Coba referensi atau status lain.</p><button type="button" class="secondary" onclick={() => (search = '')}>Hapus pencarian</button></div>{/if}
				{:else}
					<div class="empty-panel"><img src="/logo.webp" width="48" height="48" alt="" /><h3>Belum ada klaim</h3><p>{data.admin ? 'Pengajuan karyawan dan hasil pemeriksaan akan tercatat di sini.' : 'Unggah nota untuk memulai. Hasil pemeriksaan dan status pengajuan akan muncul di sini.'}</p><a href={data.admin ? '/reviews' : '/pengajuan'} class="button">{data.admin ? 'Lihat antrean review' : 'Upload nota pertama'}</a></div>
				{/if}
			</section>
			<aside class="dashboard-aside">
				<section class="surface follow-ups" aria-labelledby="attention-title"><div class="panel-heading"><h2 id="attention-title">Tindak lanjut</h2><span class="count">{needsAction.length}</span></div>
					{#if needsAction.length}
						<p class="aside-note">{data.admin ? `${reviewCount} menunggu keputusan reviewer. ${clarificationCount} menunggu jawaban karyawan.` : `${clarificationCount} perlu jawabanmu.`}</p>
						<ul>{#each needsAction.slice(0, 4) as claim (claim.id)}<li><a href={destination(claim)}><div><strong>{shortClaimRef(claim.id)}</strong><span>{claim.status === 'escalated' ? 'Tinjau bukti dan keputusan' : 'Lengkapi informasi nota'}</span></div><span aria-hidden="true">→</span></a></li>{/each}</ul>
						{#if needsAction.length > 4}<a class="all-attention" href={data.admin ? '/reviews' : '/riwayat'}>Lihat daftar klaim</a>{/if}
					{:else}<p class="no-follow-up"><span aria-hidden="true">✓</span> Semua tindak lanjut beres.</p><p class="aside-note">Klaim yang membutuhkan jawaban atau keputusan akan tampil di sini.</p>{/if}
				</section>
				<section class="receipt-guide"><span class="guide-label">{data.admin ? 'Pemeriksaan dengan bukti' : 'Dari nota ke keputusan'}</span><h2>{data.admin ? 'Fokus pada pengecualian.' : 'Bukti jelas, pengajuan lebih mudah.'}</h2><p>{data.admin ? 'Tera memeriksa klaim sesuai aturan. Reviewer menangani kasus yang dieskalasi. Disetujui berarti keputusan klaim, belum konfirmasi pembayaran.' : 'Pastikan nama tempat, tanggal, dan total terlihat. Tera akan meminta informasi tambahan bila diperlukan.'}</p><a href={data.admin ? '/reports' : '/pengajuan'}>{data.admin ? 'Lihat laporan pemeriksaan' : 'Siapkan pengajuan'} <span aria-hidden="true">→</span></a></section>
				{#if data.demoMode}<p class="demo-note">Mode demo memakai data sementara. Klaim hilang saat backend dimulai ulang.</p>{/if}
			</aside>
		</div>
	{/if}
</section>

<style>
	/* Hallmark · pre-emit critique: P4 H5 E4 S5 R5 V4 · Workbench · DESIGN.md */
	.dashboard-page { width: 100%; max-width: 1440px; }
	.page-header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-6); margin-bottom: var(--space-8); }
	.workspace-caption { margin: 0 0 var(--space-2); color: var(--color-text-muted); font-size: var(--text-xs); }
	h1 { margin: 0; }
	.lead { margin: var(--space-2) 0 0; }
	.dashboard-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-4); margin: 0 0 var(--space-8); }
	.dashboard-metrics > div { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-5); }
	.dashboard-metrics > div.attention { background: var(--color-light); border-color: var(--color-border-strong); }
	dt { color: var(--color-text-muted); font-size: var(--text-xs); }
	dd { margin: var(--space-3) 0 0; font-size: 32px; font-weight: 700; font-variant-numeric: tabular-nums; letter-spacing: -.04em; }
	dd span { display: block; margin-top: var(--space-2); font-size: var(--text-xs); font-weight: 400; letter-spacing: 0; color: var(--color-text-muted); }
	.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; align-items: start; gap: var(--space-6); }
	.surface { min-width: 0; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
	.panel-heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-3); padding: var(--space-5); }
	.panel-heading h2 { margin: 0; font-size: var(--text-md); }
	.panel-heading p { margin: var(--space-2) 0 0; color: var(--color-text-muted); font-size: var(--text-xs); }
	.panel-heading a, .all-attention { display: inline-flex; align-items: center; min-height: 44px; font-size: var(--text-xs); white-space: nowrap; }
	.search-label { display: block; margin: 0 var(--space-5) var(--space-2); font-size: var(--text-xs); }
	.claim-search { width: calc(100% - 40px); margin: 0 var(--space-5) var(--space-5); padding: var(--space-3); }
	table { min-width: 560px; }
	td { vertical-align: middle; }
	td strong { font-size: var(--text-xs); font-weight: 600; }
	td small { font-size: 11px; overflow-wrap: anywhere; }
	.table-note { font-size: var(--text-xs); color: var(--color-text-muted); padding: var(--space-4) var(--space-5); margin: 0; }
	.dashboard-aside { display: grid; gap: var(--space-5); min-width: 0; }
	.count { display: grid; place-items: center; min-width: 28px; height: 28px; background: var(--color-light); color: var(--color-primary-dark); border-radius: var(--radius-sm); font-size: var(--text-xs); }
	.aside-note { color: var(--color-text-muted); font-size: var(--text-xs); margin: 0 var(--space-5) var(--space-5); }
	.follow-ups ul { list-style: none; padding: 0 var(--space-5); margin: 0; }
	.follow-ups li + li { border-top: 1px solid var(--color-border); }
	.follow-ups li a { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); padding-block: var(--space-4); text-decoration: none; }
	.follow-ups li strong, .follow-ups li div > span { display: block; font-size: var(--text-xs); }
	.follow-ups li div > span { margin-top: var(--space-2); color: var(--color-text-muted); }
	.all-attention { margin-inline: var(--space-5); }
	.no-follow-up { margin: 0 var(--space-5) var(--space-3); font-size: var(--text-sm); }
	.no-follow-up > span { color: var(--color-primary); margin-right: var(--space-2); }
	.receipt-guide { background: var(--color-light); border-radius: var(--radius-md); padding: var(--space-6); }
	.guide-label { font-size: var(--text-xs); color: var(--color-primary-dark); }
	.receipt-guide h2 { margin: var(--space-4) 0; font-size: var(--text-xl); line-height: 1.4; }
	.receipt-guide p, .demo-note { color: var(--color-text-muted); font-size: var(--text-xs); }
	.receipt-guide a { display: inline-flex; align-items: center; gap: var(--space-3); min-height: 44px; font-size: var(--text-xs); font-weight: 600; }
	.demo-note { margin: 0; line-height: 1.8; }
	.empty-panel { padding: var(--space-12) var(--space-6); text-align: center; }
	.empty-panel h3 { margin-top: var(--space-5); font-size: var(--text-lg); }
	.empty-panel p { max-width: 360px; margin: var(--space-3) auto var(--space-6); color: var(--color-text-muted); }
	.state-panel { padding: var(--space-12); text-align: center; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: clip; clip-path: inset(50%); }
	@media (max-width: 1200px) { .dashboard-grid { grid-template-columns: minmax(0, 1fr); } .dashboard-aside { grid-template-columns: repeat(2, minmax(0, 1fr)); } .demo-note { grid-column: 1 / -1; } }
	@media (max-width: 768px) { .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); } .dashboard-metrics > div { padding: var(--space-4); } dd { font-size: 28px; } .dashboard-aside { grid-template-columns: minmax(0, 1fr); } }
</style>
