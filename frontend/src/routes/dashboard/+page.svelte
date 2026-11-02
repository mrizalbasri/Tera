<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
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
	const rejected = $derived(claims.filter((claim) => claim.status === 'rejected').length);
	const outcomes = $derived([
		{ label: 'Disetujui', count: approved, tone: 'approved' },
		{ label: 'Menunggu keputusan', count: claims.length - approved - rejected, tone: 'pending' },
		{ label: 'Ditolak', count: rejected, tone: 'rejected' }
	]);
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
		<a href={data.admin ? '/reviews' : '/pengajuan'} class="button"><Icon name={data.admin ? 'review' : 'plus'} />{data.admin ? 'Buka antrean review' : 'Ajukan klaim'}</a>
	</header>
	{#if loading}
		<div class="state-panel" role="status">Memuat ringkasan pengajuan…</div>
	{:else if error}
		<div class="state-panel" role="alert"><h2>Ringkasan belum dapat dimuat</h2><p>{error}</p><button type="button" onclick={load}><Icon name="refresh" />Coba lagi</button></div>
	{:else}
		<dl class="dashboard-metrics">
			<div><dt><span class="metric-icon"><Icon name="receipt" /></span>Total pengajuan</dt><dd>{claims.length}<span>klaim tercatat</span></dd></div>
			<div><dt><span class="metric-icon processing"><Icon name="clock" /></span>Dalam pemeriksaan</dt><dd>{processing}<span>termasuk antrean review</span></dd></div>
			<div><dt><span class="metric-icon approved"><Icon name="check" /></span>Disetujui</dt><dd>{approved}<span>keputusan tersimpan</span></dd></div>
			<div class:attention={needsAction.length > 0}><dt><span class="metric-icon warning"><Icon name="alert" /></span>Perlu perhatian</dt><dd>{needsAction.length}<span>tindak lanjut tersedia</span></dd></div>
		</dl>
		<div class="dashboard-grid">
			<section class="recent-claims surface" aria-labelledby="recent-title">
				<div class="panel-heading"><div><h2 id="recent-title">Pengajuan terbaru</h2><p>{claims.length ? 'Status terbaru dari pengajuan yang tercatat.' : 'Pengajuan akan muncul setelah karyawan mengirim nota.'}</p></div><a href={data.admin ? '/admin/claims' : '/riwayat'} class="panel-action"><Icon name="receipt" size={18} />Semua klaim</a></div>
				{#if claims.length}
					<label class="search-label" for="claim-search">Cari klaim</label>
					<div class="search-field"><Icon name="search" size={18} /><input id="claim-search" class="claim-search" type="search" bind:value={search} placeholder="Referensi, karyawan, nominal, atau status" /></div>
					{#if recent.length}
						<!-- Keyboard users need a focusable region to scroll the wide table. -->
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<div class="table-wrap" role="region" aria-label="Pengajuan terbaru" tabindex="0">
							<table><thead><tr><th>Klaim</th><th>Nominal</th><th>Status</th><th><span class="sr-only">Tindakan</span></th></tr></thead>
								<tbody>{#each recent as claim (claim.id)}<tr>
									<td><strong>{shortClaimRef(claim.id)}</strong><small>{formatDate(claim.submitted_at)}{#if data.admin} · {claim.employee_id}{/if}</small></td>
									<td class="amount">{formatCurrency(claim.declared_amount, claim.currency)}</td>
									<td><StatusBadge status={claim.status} size="sm" /></td>
									<td><a class="detail-link" href={destination(claim)}><Icon name={claim.status === 'escalated' && data.admin ? 'review' : claim.status === 'needs_clarification' && !data.admin ? 'edit' : 'eye'} size={18} />{claim.status === 'escalated' && data.admin ? 'Tinjau' : claim.status === 'needs_clarification' && !data.admin ? 'Lengkapi' : 'Lihat detail'}<span class="sr-only"> klaim {shortClaimRef(claim.id)}</span></a></td>
								</tr>{/each}</tbody>
							</table>
						</div>
						<p class="table-note">Menampilkan {recent.length} dari {matches.length} klaim{search.trim() ? ' yang cocok' : ''}.</p>
					{:else}<div class="empty-panel"><h3>Klaim tidak ditemukan</h3><p>Coba referensi atau status lain.</p><button type="button" class="secondary" onclick={() => (search = '')}>Hapus pencarian</button></div>{/if}
				{:else}
					<div class="empty-panel"><img src="/logo.webp" width="48" height="48" alt="" /><h3>Belum ada klaim</h3><p>{data.admin ? 'Pengajuan karyawan dan hasil pemeriksaan akan tercatat di sini.' : 'Unggah nota untuk memulai. Hasil pemeriksaan dan status pengajuan akan muncul di sini.'}</p><a href={data.admin ? '/reviews' : '/pengajuan'} class="button"><Icon name={data.admin ? 'review' : 'plus'} />{data.admin ? 'Lihat antrean review' : 'Upload nota pertama'}</a></div>
				{/if}
			</section>
			<aside class="dashboard-aside">
				<section class="surface follow-ups" aria-labelledby="attention-title"><div class="panel-heading"><h2 id="attention-title"><Icon name="review" />Tindak lanjut</h2><span class="count">{needsAction.length}</span></div>
					{#if needsAction.length}
						<p class="aside-note">{data.admin ? `${reviewCount} menunggu keputusan reviewer. ${clarificationCount} menunggu jawaban karyawan.` : `${clarificationCount} perlu jawabanmu.`}</p>
						<ul>{#each needsAction.slice(0, 4) as claim (claim.id)}<li><a href={destination(claim)}><div><strong>{shortClaimRef(claim.id)}</strong><span>{claim.status === 'escalated' ? 'Tinjau bukti dan keputusan' : 'Lengkapi informasi nota'}</span></div><span class="follow-up-icon"><Icon name={data.admin ? 'review' : 'edit'} /></span></a></li>{/each}</ul>
						{#if needsAction.length > 4}<a class="all-attention" href={data.admin ? '/reviews' : '/riwayat'}>Lihat daftar klaim</a>{/if}
					{:else}<p class="no-follow-up"><Icon name="check" /> Semua tindak lanjut beres.</p><p class="aside-note">Klaim yang membutuhkan jawaban atau keputusan akan tampil di sini.</p>{/if}
				</section>
				<section class="surface outcome-panel" aria-labelledby="outcome-title">
					<div class="panel-heading"><h2 id="outcome-title"><Icon name="chart" />Hasil pengajuan</h2></div>
					<div class="outcome-content">
						{#each outcomes as outcome (outcome.tone)}
							<div class="outcome-row {outcome.tone}"><div><span>{outcome.label}</span><strong>{outcome.count}</strong></div><progress max={claims.length || 1} value={outcome.count} aria-label={outcome.label}></progress></div>
						{/each}
						<p>{claims.length ? `Dari ${claims.length} pengajuan yang tercatat.` : 'Distribusi akan tampil setelah ada pengajuan.'}</p>
					</div>
				</section>
				<section class="quick-actions" aria-label="Akses cepat">
					<h2>Akses cepat</h2>
					<a href={data.admin ? '/reports' : '/pengajuan'}><span class="quick-icon"><Icon name={data.admin ? 'chart' : 'upload'} /></span><span><strong>{data.admin ? 'Laporan pemeriksaan' : 'Ajukan pengeluaran'}</strong><small>{data.admin ? 'Ringkasan hasil dan unduh CSV' : 'Unggah foto atau PDF nota'}</small></span></a>
					<a href={data.admin ? '/admin/policies' : '/riwayat'}><span class="quick-icon"><Icon name={data.admin ? 'shield' : 'receipt'} /></span><span><strong>{data.admin ? 'Kebijakan klaim' : 'Riwayat pengajuan'}</strong><small>{data.admin ? 'Aturan dan versi yang berlaku' : 'Status dan hasil pemeriksaan'}</small></span></a>
				</section>
			</aside>
		</div>
	{/if}
</section>

<style>
	.outcome-content { padding: 0 20px 20px; }
	.outcome-row { margin-bottom: 20px; }
	.outcome-row > div { display: flex; align-items: center; justify-content: space-between; font-size: 12px; margin-bottom: 8px; }
	.outcome-row strong { font-variant-numeric: tabular-nums; }
	.outcome-row progress { display: block; appearance: none; border: 0; width: 100%; height: 7px; border-radius: 8px; overflow: hidden; background: var(--color-soft); accent-color: var(--color-primary); }
	.outcome-row progress::-webkit-progress-bar { background: var(--color-soft); border-radius: 8px; }
	.outcome-row progress::-webkit-progress-value { background: var(--color-primary); border-radius: 8px; }
	.outcome-row progress::-moz-progress-bar { background: var(--color-primary); border-radius: 8px; }
	.outcome-row.approved progress::-webkit-progress-value { background: var(--color-success); }
	.outcome-row.approved progress::-moz-progress-bar { background: var(--color-success); }
	.outcome-row.pending progress::-webkit-progress-value { background: var(--color-warning); }
	.outcome-row.pending progress::-moz-progress-bar { background: var(--color-warning); }
	.outcome-row.rejected progress::-webkit-progress-value { background: var(--color-danger); }
	.outcome-row.rejected progress::-moz-progress-bar { background: var(--color-danger); }
	.outcome-content > p { margin: 0; color: var(--color-text-muted); font-size: 11px; }
	.quick-actions { padding: 20px; border-radius: var(--radius-lg); background: var(--color-light); }
	.quick-actions h2 { margin: 0 0 12px; font-size: 14px; }
	.quick-actions a { display: flex; align-items: center; gap: 12px; text-decoration: none; color: var(--color-ink); min-height: 64px; border-radius: 8px; transition: background var(--dur-short); }
	.quick-actions a:hover { background: var(--color-surface); }
	.quick-icon { display: inline-flex; padding: 10px; color: var(--color-primary); background: var(--color-surface); border-radius: 10px; }
	.quick-actions strong, .quick-actions small { display: block; font-size: 12px; }
	.quick-actions small { margin-top: 4px; color: var(--color-text-muted); font-size: 11px; }

	.metric-icon { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex-shrink: 0; border-radius: var(--radius-md); background: var(--color-light); color: var(--color-primary-dark); }
	.metric-icon.processing { background: var(--color-info-soft); color: var(--color-info); }
	.metric-icon.approved { background: var(--color-success-soft); color: var(--color-success); }
	.metric-icon.warning { background: var(--color-warning-soft); color: var(--color-warning); }
	.search-field { display: flex; align-items: center; gap: var(--space-1); margin: 0 var(--space-5) var(--space-5); padding-left: var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); color: var(--color-text-muted); background: var(--color-surface); }
	.search-field:focus-within { outline: 3px solid var(--color-focus); outline-offset: 3px; }
	.search-field input:focus-visible { outline: none; }
	.panel-action { gap: var(--space-2); text-decoration: none; font-weight: 600; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	.panel-action:hover { background: var(--color-light); border-color: var(--color-border-strong); }
	.panel-heading h2 { display: flex; align-items: center; gap: var(--space-2); }
	.detail-link { gap: var(--space-2); padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); background: var(--color-surface); text-decoration: none; font-weight: 600; white-space: nowrap; }
	.detail-link:hover { background: var(--color-primary); border-color: var(--color-primary); color: var(--color-inverse); }
	tbody tr:hover, tbody tr:focus-within { background: var(--color-soft); }
	.follow-up-icon { display: inline-flex; color: var(--color-primary); background: var(--color-light); padding: var(--space-2); border-radius: var(--radius-sm); }
	.follow-ups li a:hover { background: var(--color-soft); box-shadow: 0 0 0 8px var(--color-soft); }
	.dashboard-page { width: 100%; max-width: 1440px; }
	.page-header { padding: clamp(20px, 3vw, 32px); background: var(--color-light); border: 1px solid var(--color-border-strong); border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: space-between; gap: var(--space-6); margin-bottom: var(--space-8); }
	.workspace-caption { font-weight: 700; margin: 0 0 var(--space-2); color: var(--color-text-muted); font-size: var(--text-xs); }
	h1 { margin: 0; }
	.lead { margin: var(--space-2) 0 0; }
	.dashboard-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-4); margin: 0 0 var(--space-8); }
	.dashboard-metrics > div { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); box-shadow: var(--shadow-card); }
	.dashboard-metrics > div.attention { background: var(--color-warning-soft); border-color: var(--color-warning-border); }
	dt { display: flex; align-items: center; gap: var(--space-3); color: var(--color-text-muted); font-size: var(--text-sm); font-weight: 600; }
	dd { margin: var(--space-3) 0 0; font-size: 36px; font-weight: 700; font-variant-numeric: tabular-nums; letter-spacing: -.04em; }
	dd span { display: block; margin-top: var(--space-2); font-size: var(--text-xs); font-weight: 400; letter-spacing: 0; color: var(--color-text-muted); }
	.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) 296px; align-items: start; gap: var(--space-6); }
	.surface { box-shadow: var(--shadow-card); overflow: clip; min-width: 0; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
	.panel-heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-3); padding: var(--space-5); }
	.panel-heading h2 { margin: 0; font-size: var(--text-md); }
	.panel-heading p { margin: var(--space-2) 0 0; color: var(--color-text-muted); font-size: var(--text-xs); }
	.panel-heading a, .all-attention { display: inline-flex; align-items: center; min-height: 44px; font-size: var(--text-xs); white-space: nowrap; }
	.search-label { display: block; margin: 0 var(--space-5) var(--space-2); font-size: var(--text-xs); }
	.claim-search { width: 100%; border: 0; background: transparent; padding: var(--space-3); }
	table { min-width: 560px; }
	td { vertical-align: middle; }
	td strong { font-size: var(--text-xs); font-weight: 600; }
	td small { font-size: var(--text-xs); overflow-wrap: anywhere; }
	.table-note { font-size: var(--text-xs); color: var(--color-text-muted); padding: var(--space-4) var(--space-5); margin: 0; }
	.dashboard-aside { display: grid; gap: var(--space-5); min-width: 0; }
	.count { display: grid; place-items: center; min-width: 28px; height: 28px; background: var(--color-light); color: var(--color-primary-dark); border-radius: var(--radius-sm); font-size: var(--text-xs); }
	.aside-note { color: var(--color-text-muted); font-size: var(--text-xs); margin: 0 var(--space-5) var(--space-5); }
	.follow-ups ul { list-style: none; padding: 0 var(--space-5); margin: 0; }
	.follow-ups li + li { border-top: 1px solid var(--color-border); }
	.follow-ups li a { border-radius: var(--radius-sm); transition: background var(--dur-short), box-shadow var(--dur-short); display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); padding-block: var(--space-4); text-decoration: none; }
	.follow-ups li strong, .follow-ups li div > span { display: block; font-size: var(--text-xs); }
	.follow-ups li div > span { margin-top: var(--space-2); color: var(--color-text-muted); }
	.all-attention { margin-inline: var(--space-5); }
	.no-follow-up { display: flex; align-items: center; gap: var(--space-2); color: var(--color-success); font-weight: 600; margin: 0 var(--space-5) var(--space-3); font-size: var(--text-sm); }

	.empty-panel { padding: var(--space-12) var(--space-6); text-align: center; }
	.empty-panel h3 { margin-top: var(--space-5); font-size: var(--text-lg); }
	.empty-panel p { max-width: 360px; margin: var(--space-3) auto var(--space-6); color: var(--color-text-muted); }
	.state-panel { padding: var(--space-12); text-align: center; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: clip; clip-path: inset(50%); }
	@media (max-width: 1100px) { .dashboard-grid { grid-template-columns: minmax(0, 1fr); } .dashboard-aside { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
	@media (max-width: 768px) { .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); } .dashboard-metrics > div { padding: var(--space-4); } dt { flex-direction: column; align-items: flex-start; font-size: var(--text-xs); } .page-header { align-items: flex-start; } .page-header > .button { width: 100%; white-space: normal; } dd { font-size: 28px; } .dashboard-aside { grid-template-columns: minmax(0, 1fr); } }
</style>
