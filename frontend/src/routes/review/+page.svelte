<script lang="ts">
	import { onMount } from 'svelte';
	import { api, message, money, dateTime, type ReviewItem } from '$lib/api';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	let items = $state<ReviewItem[]>([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let filtered = $derived(items.filter(item => `${item.claim.employee_id} ${item.claim.id}`.toLowerCase().includes(search.toLowerCase())));
	async function load() {
		loading = true; error = ''; items = [];
		try { items = (await api<{ items: ReviewItem[] }>('/reviews')).items; }
		catch (err) { error = message(err); } finally { loading = false; }
	}
	onMount(() => { void load(); });
</script>
<svelte:head><title>Review klaim · Tera</title></svelte:head>
<p class="eyebrow">03 / Review klaim</p><h1>Keputusan yang perlu<br />sentuhan manusia.</h1>
<p class="lead">Tinjau bukti, pahami alasan eskalasi, lalu berikan keputusan yang tercatat bersama pertimbangannya.</p>
<div class="section-top"><h2>Antrean review {loading ? '' : `(${items.length})`}</h2><button class="secondary" onclick={load} disabled={loading}>{loading ? 'Memuat…' : 'Perbarui antrean'}</button></div>
{#if error}<div class="notice" role="alert"><p>{error}</p><button class="secondary" onclick={load}>Coba lagi</button></div>
{:else if loading}<p class="loading" role="status">Mengambil klaim yang menunggu review…</p>
{:else}<section class="panel"><div class="field"><label for="search">Cari referensi karyawan atau ID klaim</label><input id="search" type="search" bind:value={search} placeholder="Cari dalam antrean…" /></div>
	{#if filtered.length}<div class="table-wrap"><table><thead><tr><th>Klaim / Karyawan</th><th>Diajukan</th><th>Nominal pengajuan</th><th>Alasan eskalasi</th><th>Tindakan</th></tr></thead><tbody>{#each filtered as item (item.review.id)}<tr><td><a href="/claims/{item.claim.id}">{item.claim.id.slice(0, 8).toUpperCase()}</a><small>{item.claim.employee_id}</small><div style="margin-top:12px"><StatusBadge status={item.claim.status} /></div></td><td>{dateTime(item.claim.submitted_at)}</td><td class="amount">{money(item.claim.declared_amount, item.claim.currency)}</td><td>{item.decision?.explanation ?? 'Lihat detail pemeriksaan.'}{#each item.signals as signal}<small>{signal.explanation}</small>{/each}</td><td><a class="button secondary" href="/claims/{item.claim.id}#review">Tinjau ↗</a></td></tr>{/each}</tbody></table></div>
	{:else}<div class="empty"><h2>{items.length ? 'Tidak ada klaim yang cocok.' : 'Antrean sudah bersih.'}</h2><p>{items.length ? 'Coba referensi atau ID klaim lainnya.' : 'Klaim yang membutuhkan keputusan reviewer akan muncul di sini.'}</p></div>{/if}
</section>{/if}
