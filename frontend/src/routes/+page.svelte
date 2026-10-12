<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, message, type Claim } from '$lib/api';
	let employee = $state('');
	let amount = $state<number>();
	let files = $state<FileList>();
	let busy = $state(false);
	let error = $state('');
	let key = '';
	function changed() { key = ''; error = ''; }
	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (busy) return;
		error = '';
		if (!employee.trim() || !files?.length) { error = 'Isi referensi karyawan dan pilih sedikitnya satu nota.'; return; }
		if (Array.from(files).some(file => !['image/jpeg', 'image/png', 'application/pdf'].includes(file.type) || file.size === 0)) {
			error = 'Gunakan file JPG, PNG, atau PDF yang tidak kosong.'; return;
		}
		busy = true;
		key ||= crypto.randomUUID();
		const form = new FormData();
		form.set('employee_id', employee.trim()); form.set('currency', 'IDR');
		if (amount !== undefined) form.set('declared_amount', String(amount));
		for (const file of files) form.append('files', file);
		try {
			const saved = await api<{ claim: Claim }>('/claims', { method: 'POST', headers: { 'Idempotency-Key': key }, body: form });
			await goto(`/claims/${saved.claim.id}`);
		} catch (err) { error = message(err); }
		finally { busy = false; }
	}
</script>
<svelte:head><title>Pengajuan baru · Tera</title><meta name="description" content="Ajukan nota pengeluaran dan pantau proses reimbursement bersama Tera." /></svelte:head>
<p class="eyebrow">01 / Pengajuan baru</p>
<h1>Nota tersimpan.<br />Pekerjaan terus berjalan.</h1>
<p class="lead">Kumpulkan bukti pengeluaranmu di satu tempat. Tera membantu membaca nota, memeriksa kebijakan, dan menjelaskan hasilnya.</p>
<div class="split">
	<section class="panel">
		<div class="section-top"><h2>Ajukan pengeluaran</h2><span class="muted">Mulai dari bukti transaksi</span></div>
		{#if error}<div class="notice" role="alert">{error}</div>{/if}
		<form onsubmit={submit}>
			<fieldset disabled={busy} style="border:0;padding:0;margin:0;min-width:0">
				<div class="form-row">
					<div class="field"><label for="employee">Referensi karyawan</label><input id="employee" bind:value={employee} oninput={changed} maxlength="100" required placeholder="Contoh: EMP-001" /><small>Gunakan referensi yang sama saat membuka riwayat.</small></div>
					<div class="field"><label for="amount">Nominal pengajuan (Rp)</label><input id="amount" type="number" bind:value={amount} oninput={changed} min="0.01" step="0.01" placeholder="Opsional" /><small>Nilai ini akan dibandingkan dengan hasil pembacaan.</small></div>
				</div>
				<div class="upload-zone">
					<span class="upload-icon" aria-hidden="true">↥</span>
					<label for="receipts">Pilih nota pengeluaran</label>
					<p>Pastikan tanggal, nama vendor, dan total terlihat jelas.</p>
					<input id="receipts" type="file" accept="image/jpeg,image/png,application/pdf" multiple bind:files oninput={changed} required aria-describedby="file-help" />
					<small id="file-help">JPG, PNG, atau PDF · Bisa lebih dari satu nota</small>
				</div>
				{#if files?.length}<ul class="file-list">{#each Array.from(files) as file}<li><span>{file.name}</span><small>{(file.size / 1024).toFixed(0)} KB</small></li>{/each}</ul>{/if}
				<div class="submit-row"><small class="muted">Nota disimpan sebelum mulai diproses.</small><button type="submit">{busy ? 'Menyimpan nota…' : 'Simpan & lihat klaim'} <span aria-hidden="true">↗</span></button></div>
			</fieldset>
		</form>
	</section>
	<aside>
		<section class="guide"><p class="eyebrow">Cara kerja Tera</p><h2>Dari nota ke keputusan,<br />langkah demi langkah.</h2>
			<ol><li><strong>Simpan bukti</strong><p>Unggah nota dan isi referensi karyawan.</p></li><li><strong>Mulai pemeriksaan</strong><p>Tera membaca data dan memeriksa kebijakan pengeluaran.</p></li><li><strong>Ikuti hasilnya</strong><p>Lihat keputusan, jawab klarifikasi, atau tunggu review.</p></li></ol>
			<a href="/riwayat">Sudah pernah mengajukan? Buka riwayat ↗</a>
		</section>
		<p class="muted privacy-note">Gunakan nota sintetis atau anonim untuk pengujian prototipe ini.</p>
	</aside>
</div>
<style>
	.upload-zone { display: grid; justify-items: center; gap: 10px; text-align: center; padding: 28px 20px; border: 1px dashed #aebda2; background: #f4f7ee; border-radius: 12px; }
	.upload-icon { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; background: #e1ead6; font-size: 26px; }
	.upload-zone p { margin: 0; color: #6a7965; font-size: 12px; }
	.upload-zone input { max-width: 100%; font-size: 12px; background: white; }
	.upload-zone small { font-size: 11px; color: #73806e; }
	.submit-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 18px; margin-top: 26px; }
	.guide { padding: 30px; border-radius: 18px; background: #e8eddb; }
	.guide h2 { font: 25px/1.3 'Georgia', serif; }
	ol { padding: 0; list-style: none; counter-reset: steps; margin: 30px 0; }
	li { counter-increment: steps; position: relative; padding-left: 36px; margin: 22px 0; font-size: 13px; }
	ol li::before { content: '0' counter(steps); position: absolute; left: 0; top: 2px; font-size: 11px; color: #799367; }
	li p { margin: 6px 0 0; color: #6c7b61; font-size: 12px; }
	.guide a { font-size: 12px; }
	.privacy-note { padding: 0 14px; font-size: 11px; }
	.file-list { list-style: none; padding: 0; }
	.file-list li { padding: 0; display: flex; justify-content: space-between; gap: 10px; margin: 12px 0; overflow-wrap: anywhere; }
</style>
