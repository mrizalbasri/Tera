<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { onMount } from 'svelte';
	import { getNotifications, markNotificationRead, type Notification } from '$lib/api/workspace';
	import { formatDateTime } from '$lib/formatters/date';
	let { data } = $props();
	let items = $state<Notification[]>([]);
	let busy = $state(true);
	let error = $state('');
	let actionError = $state('');
	let marking = $state('');
	let offset = $state(0);
	async function load() {
		busy = true;
		error = '';
		try { items = (await getNotifications(offset)).items; }
		catch (cause) { error = cause instanceof Error ? cause.message : 'Notifikasi tidak dapat dimuat.'; }
		finally { busy = false; }
	}
	async function read(item: Notification) {
		marking = item.id;
		actionError = '';
		try { const saved = await markNotificationRead(item.id); items = items.map(row => row.id === saved.id ? saved : row); }
		catch (cause) { actionError = cause instanceof Error ? cause.message : 'Status baca belum tersimpan.'; }
		finally { marking = ''; }
	}
	function destination(item: Notification) {
		const id = encodeURIComponent(item.payload.claim_id);
		if (data.admin && item.payload.status === 'escalated' && !item.payload.resolved) return `/reviews/${id}`;
		return data.admin ? `/admin/claims/${id}` : `/riwayat/${id}`;
	}
	onMount(load);
</script>

<svelte:head><title>Notifikasi · Tera</title></svelte:head>
<section class="inbox" aria-labelledby="inbox-title">
	<header class="page-header"><div><h1 id="inbox-title">Notifikasi</h1><p>Informasi baru dan klaim yang membutuhkan tindak lanjut.</p></div><button type="button" onclick={load} disabled={busy}><Icon name="refresh" size={18} />Muat ulang</button></header>
	{#if busy}<p role="status">Memuat notifikasi...</p>
	{:else if error}<div class="notice" role="alert"><p>{error}</p><button type="button" onclick={load}>Coba lagi</button></div>
	{:else if items.length === 0}<div class="empty"><Icon name="bell" size={32} /><h2>Belum ada notifikasi</h2><p>Permintaan informasi, antrean review, dan hasil klaim akan tampil di sini.</p></div>
	{:else}
		{#if actionError}<p class="error" role="alert">{actionError}</p>{/if}
		<ul>{#each items as item (item.id)}
			<li class:unread={!item.payload.read_at && !item.payload.resolved}>
				<div><p class="meta">{item.payload.reminder ? 'Pengingat' : 'Pembaruan klaim'} · {formatDateTime(item.created_at)}</p><a href={destination(item)}>{item.payload.message}</a><p class="meta">{item.payload.resolved ? 'Sudah ditindaklanjuti' : item.payload.read_at ? 'Sudah dibaca' : 'Belum dibaca'}</p></div>
				{#if !item.payload.read_at}<button type="button" class="secondary" disabled={Boolean(marking)} onclick={() => read(item)}>{marking === item.id ? 'Menyimpan...' : 'Tandai dibaca'}</button>{/if}
			</li>
		{/each}</ul>
	{/if}
	<nav class="pagination" aria-label="Halaman notifikasi"><button type="button" disabled={busy || offset === 0} onclick={() => { offset = Math.max(0, offset - 50); void load(); }}>Sebelumnya</button><span>Halaman {offset / 50 + 1}</span><button type="button" disabled={busy || items.length < 50} onclick={() => { offset += 50; void load(); }}>Berikutnya</button></nav>
</section>

<style>
	.inbox { max-width: 960px; margin: 0 auto; }
	header, li { display: flex; justify-content: space-between; align-items: start; gap: var(--space-5); }
	h1 { font-size: var(--text-title); margin: 0; } header p, .meta { color: var(--color-text-muted); }
	ul { list-style: none; padding: 0; margin: var(--space-8) 0; border-top: 1px solid var(--color-border); }
	li { padding: var(--space-5); border-bottom: 1px solid var(--color-border); background: var(--color-surface); }
	li.unread { border-left: 4px solid var(--color-primary); background: var(--color-light); }
	li a { color: var(--color-primary-dark); font-weight: 600; text-underline-offset: 3px; }
	.meta { font-size: var(--text-sm); margin: 0 0 var(--space-2); } li .meta:last-child { margin-top: var(--space-3); }
	button { min-height: 44px; border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); padding: var(--space-3) var(--space-4); background: var(--color-surface); color: var(--color-text); cursor: pointer; }
	button:disabled { opacity: .55; cursor: default; } .pagination { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-4); margin-top: var(--space-6); }
	.notice, .empty { padding: var(--space-8); background: var(--color-soft); border-radius: var(--radius-md); margin-top: var(--space-6); }.error { color: var(--color-danger); }
	@media (max-width: 600px) { header, li { flex-direction: column; } li { padding: var(--space-4); } }
</style>
