<script lang="ts">
	import { api, message, money, dateTime, statusLabels, type Claim } from '$lib/api';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	let employee = $state('');
	let claims = $state<Claim[]>([]);
	let busy = $state(false);
	let loaded = $state(false);
	let error = $state('');
	let status = $state('');
	let shown = $derived(claims.filter(claim => !status || claim.status === status));
	async function load(event?: SubmitEvent) {
		event?.preventDefault();
		if (!employee.trim() || busy) return;
		busy = true; loaded = false; error = ''; claims = [];
		try { claims = (await api<{ items: Claim[] }>(`/claims?employee_id=${encodeURIComponent(employee.trim())}`)).items.sort((a, b) => b.submitted_at.localeCompare(a.submitted_at)); loaded = true; }
		catch (err) { error = message(err); } finally { busy = false; }
	}
</script>
<svelte:head><title>Riwayat klaim · Tera</title></svelte:head>
<p class="eyebrow">02 / Riwayat klaim</p><h1>Setiap pengeluaran,<br />jelas perkembangannya.</h1>
<p class="lead">Temukan pengajuan dengan referensi karyawan, lalu buka klaim untuk melihat hasil pemeriksaan dan tindak lanjut.</p>
<section class="panel">
	<form onsubmit={load} class="lookup"><div class="field"><label for="employee">Referensi karyawan</label><input id="employee" bind:value={employee} oninput={() => { loaded = false; claims = []; error = ''; }} required maxlength="100" placeholder="Contoh: EMP-001" disabled={busy} /></div><button disabled={busy}>{busy ? 'Memuat…' : 'Cari pengajuan'}</button></form>
	<p class="muted">Referensi ini adalah filter pencarian pada prototipe, bukan akun login.</p>
</section>
{#if error}<div class="notice" role="alert"><p>{error}</p><button class="secondary" onclick={() => load()}>Coba lagi</button></div>{/if}
{#if busy}<p class="loading" role="status">Memuat riwayat dari server…</p>
{:else if loaded}
	<div class="stats"><div class="stat"><span class="muted">Total pengajuan</span><strong>{claims.length}</strong></div><div class="stat"><span class="muted">Disetujui</span><strong>{claims.filter(c => c.status === 'approved').length}</strong></div><div class="stat"><span class="muted">Perlu jawaban</span><strong>{claims.filter(c => c.status === 'needs_clarification').length}</strong></div></div>
	<section class="panel"><div class="section-top"><h2>Daftar pengajuan</h2><div><label for="status">Status </label><select id="status" bind:value={status} style="width:auto"><option value="">Semua status</option>{#each Object.entries(statusLabels) as [value, label]}<option value={value}>{label}</option>{/each}</select></div></div>
		{#if shown.length}<div class="table-wrap"><table><thead><tr><th>Klaim</th><th>Diajukan</th><th>Nominal pengajuan</th><th>Status</th><th>Detail</th></tr></thead><tbody>{#each shown as claim (claim.id)}<tr><td><a href="/claims/{claim.id}">{claim.id.slice(0, 8).toUpperCase()}</a><small>{claim.employee_id}</small></td><td>{dateTime(claim.submitted_at)}</td><td class="amount">{money(claim.declared_amount, claim.currency)}</td><td><StatusBadge status={claim.status} /></td><td><a href="/claims/{claim.id}" aria-label="Lihat klaim {claim.id.slice(0, 8)}">Lihat ↗</a></td></tr>{/each}</tbody></table></div>
		{:else}<div class="empty"><h2>{claims.length ? 'Tidak ada klaim dengan status ini.' : 'Belum ada pengajuan.'}</h2><p>{claims.length ? 'Pilih status lain untuk melihat pengajuan.' : 'Periksa referensi karyawan atau mulai pengajuan baru.'}</p><a class="button secondary" href="/">Ajukan pengeluaran</a></div>{/if}
	</section>
{:else if !error}<div class="panel empty"><h2>Riwayatmu dimulai di sini.</h2><p>Masukkan referensi karyawan untuk memuat pengajuan yang tersimpan.</p></div>{/if}
<style>.lookup { display: flex; flex-wrap: wrap; align-items: end; gap: 16px; } .lookup .field { flex: 1; min-width: 200px; margin: 0; }</style>
