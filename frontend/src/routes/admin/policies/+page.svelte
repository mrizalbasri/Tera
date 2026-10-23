<script lang="ts">
	import { onMount } from 'svelte';
	import { createPolicy, editPolicy, getPolicyVersions, publishPolicy, importBaselinePolicies, getPolicyAudit, type PolicyVersion, type PolicyRule } from '$lib/api/workspace';
	import { formatDateTime } from '$lib/formatters/date';
	type RuleRow = { id: string; type: string; amount: string; terms: string };
	const categories: Record<string, string> = { meals: 'Makan', fuel: 'BBM', toll_parking: 'Tol dan parkir', hotel: 'Hotel', other: 'Lainnya' };
	const ruleTypes: Record<string, string> = { max_amount_per_person: 'Batas per orang per klaim', max_amount: 'Batas nominal per klaim', receipt_required: 'Nota wajib', vendor_required: 'Jenis vendor wajib', evidence_required: 'Bukti pendukung wajib', amount_matches_declared: 'Nominal sesuai pengajuan', prohibited_items: 'Item yang dilarang' };
	const auditLabels: Record<string, string> = { 'policy.draft_created': 'Draft dibuat', 'policy.draft_updated': 'Draft diperbarui', 'policy.published': 'Versi diterbitkan', 'policy.baseline_imported': 'Kebijakan awal diimpor' };
	let versions = $state<PolicyVersion[]>([]);
	let loading = $state(true);
	let busy = $state(false);
	let loadError = $state('');
	let formError = $state('');
	let status = $state('');
	let category = $state('meals');
	let from = $state(new Date().toLocaleDateString('en-CA'));
	let to = $state('');
	let source = $state('');
	let rows = $state<RuleRow[]>([{ id: 'meal_limit', type: 'max_amount_per_person', amount: '75000', terms: '' }]);
	let editing = $state<PolicyVersion | null>(null);
	let confirming = $state<PolicyVersion | null>(null);
	let offset = $state(0);
	let auditId = $state('');
	let audit = $state<{ event_type: string; timestamp: string; safe_payload: { actor_reference?: string } }[]>([]);
	async function load() {
		loading = true; loadError = '';
		try { versions = (await getPolicyVersions(offset)).items; }
		catch (cause) { loadError = cause instanceof Error ? cause.message : 'Kebijakan belum dapat dimuat.'; }
		finally { loading = false; }
	}
	function begin(version: PolicyVersion) {
		const draft = version.payload.draft;
		editing = version.payload.status === 'draft' ? version : null;
		category = draft.category; from = draft.effective_from; to = draft.effective_to ?? ''; source = draft.source;
		rows = draft.rules.map(rule => ({ id: rule.rule_id, type: rule.rule_type, amount: String(rule.limit ?? ''), terms: (rule.rule_type === 'prohibited_items' ? rule.prohibited_terms : rule.required_terms)?.join(', ') ?? '' }));
		formError = ''; status = editing ? 'Draft dimuat untuk diedit.' : 'Isi versi terbit disalin. Atur tanggal berlaku untuk versi baru.';
		document.getElementById('policy-category')?.focus();
	}
	function reset() { editing = null; source = ''; rows = []; formError = ''; }
	async function save(event: SubmitEvent) {
		event.preventDefault();
		formError = ''; status = '';
		if (to && to < from) { formError = 'Tanggal akhir tidak boleh mendahului tanggal awal.'; return; }
		if (!rows.length && category !== 'other') { formError = 'Tambahkan setidaknya satu aturan untuk kategori ini.'; return; }
		const rules: PolicyRule[] = rows.map(row => ({ rule_id: row.id, rule_type: row.type, currency: 'IDR',
			limit: row.type.startsWith('max_amount') ? row.amount : null,
			required_terms: ['vendor_required', 'evidence_required'].includes(row.type) ? row.terms.split(',').map(term => term.trim()).filter(Boolean) : [],
			prohibited_terms: row.type === 'prohibited_items' ? row.terms.split(',').map(term => term.trim()).filter(Boolean) : [] }));
		busy = true;
		try {
			const draft = { category, effective_from: from, effective_to: to || null, source: source.trim(), rules };
			if (editing) await editPolicy(editing.id, draft, editing.revision); else await createPolicy(draft);
			reset(); status = 'Draft tersimpan. Periksa isi dan tanggal sebelum menerbitkan.'; offset = 0; await load();
		} catch (cause) { formError = cause instanceof Error ? cause.message : 'Draft belum tersimpan.'; }
		finally { busy = false; }
	}
	async function publish(version: PolicyVersion) {
		busy = true; formError = ''; status = '';
		try { await publishPolicy(version.id, version.revision); confirming = null; status = 'Versi kebijakan diterbitkan.'; await load(); }
		catch (cause) { formError = cause instanceof Error ? cause.message : 'Versi belum dapat diterbitkan.'; }
		finally { busy = false; }
	}
	async function importBaseline() {
		busy = true; formError = ''; status = '';
		try { await importBaselinePolicies(); status = 'Lima kebijakan awal tersedia. Import ulang tidak membuat versi ganda.'; offset = 0; await load(); }
		catch (cause) { formError = cause instanceof Error ? cause.message : 'Import belum berhasil.'; }
		finally { busy = false; }
	}
	async function showAudit(version: PolicyVersion) {
		busy = true; formError = '';
		try { audit = (await getPolicyAudit(version.id)).items; auditId = version.id; }
		catch (cause) { formError = cause instanceof Error ? cause.message : 'Riwayat perubahan belum dapat dimuat.'; }
		finally { busy = false; }
	}
	onMount(load);
</script>

<svelte:head><title>Kebijakan reimbursement · Tera</title></svelte:head>
<section class="policies" aria-labelledby="policy-title">
	<header><h1 id="policy-title">Kebijakan reimbursement</h1><p>Atur pemeriksaan klaim berdasarkan tanggal nota. Keputusan lama tetap menyimpan dasar kebijakannya.</p></header>
	{#if status}<p class="notice" role="status">{status}</p>{/if}
	{#if formError}<p class="error notice" role="alert">{formError}</p>{/if}
	<section class="editor" aria-labelledby="draft-title">
		<div class="section-heading"><h2 id="draft-title">{editing ? 'Edit draft' : 'Draft kebijakan baru'}</h2>{#if editing}<button type="button" onclick={reset} disabled={busy}>Batalkan edit</button>{/if}</div>
		<form onsubmit={save}>
			<div class="fields"><label>Kategori<select id="policy-category" bind:value={category} disabled={busy || Boolean(editing)}>{#each Object.entries(categories) as [value, label]}<option {value}>{label}</option>{/each}</select></label><label>Berlaku mulai<input type="date" bind:value={from} required disabled={busy} /></label><label>Berlaku sampai (opsional)<input type="date" bind:value={to} min={from} disabled={busy} /></label></div>
			<label>Sumber dan isi kebijakan<textarea bind:value={source} required maxlength="20000" rows="4" disabled={busy} placeholder="Tuliskan sumber kebijakan dan ketentuan yang menjadi dasar aturan di bawah."></textarea></label>
			<p class="hint">Batas nominal berlaku per klaim. Pilihan per orang mempertimbangkan jumlah peserta yang diklarifikasi.</p>
			<fieldset disabled={busy}><legend>Aturan pemeriksaan</legend>
				{#each rows as row, index (row.id)}<div class="rule"><label>Aturan {index + 1}<select bind:value={row.type}>{#each Object.entries(ruleTypes) as [value, label]}<option {value}>{label}</option>{/each}</select></label>
					{#if row.type.startsWith('max_amount')}<label>Batas (Rp)<input type="number" min="0.01" step="0.01" bind:value={row.amount} required /></label>
					{:else if ['vendor_required', 'evidence_required', 'prohibited_items'].includes(row.type)}<label>Istilah, pisahkan dengan koma<input type="text" bind:value={row.terms} required maxlength="2000" /></label>{/if}
					<button type="button" class="remove" aria-label={`Hapus aturan ${index + 1}`} onclick={() => { rows = rows.filter(item => item.id !== row.id); }}>Hapus</button></div>{/each}
				<button type="button" onclick={() => { rows = [...rows, { id: `rule_${crypto.randomUUID().slice(0, 8)}`, type: 'receipt_required', amount: '', terms: '' }]; }} disabled={rows.length >= 50}>Tambah aturan</button>
			</fieldset>
			<button class="primary" type="submit" disabled={busy}>{busy ? 'Menyimpan...' : editing ? 'Simpan perubahan draft' : 'Simpan draft'}</button>
		</form>
	</section>
	<section class="versions" aria-labelledby="versions-title"><div class="section-heading"><div><h2 id="versions-title">Versi kebijakan</h2><p class="hint">Versi terbit tidak dapat diedit. Versi baru dapat menggantikan kebijakan tanpa tanggal akhir mulai tanggal berlakunya.</p></div><button type="button" onclick={importBaseline} disabled={busy}>Import kebijakan awal</button></div>
		{#if loading}<p role="status">Memuat kebijakan...</p>{:else if loadError}<p class="error" role="alert">{loadError}</p><button type="button" onclick={load}>Coba lagi</button>{:else if !versions.length}<p>Belum ada versi tersimpan. Import kebijakan awal untuk melihat aturan bawaan, atau buat draft baru.</p>{:else}
			{#each versions as version (version.id)}<article>
				<div class="section-heading"><div><h3>{categories[version.payload.draft.category]} · {version.payload.status === 'published' ? `Versi ${version.payload.policy?.version}` : 'Draft'}</h3><p class="hint">{version.payload.draft.effective_from} hingga {version.payload.draft.effective_to ?? 'digantikan versi berikutnya'}</p></div><span>{version.payload.status === 'published' ? 'Terbit' : 'Belum terbit'}</span></div>
				<p class="source">{version.payload.draft.source}</p>
				<ul>{#each version.payload.draft.rules as rule}<li>{ruleTypes[rule.rule_type] ?? rule.rule_type}{rule.limit != null ? `: Rp${Number(rule.limit).toLocaleString('id-ID')}` : ''}{rule.required_terms?.length ? `: ${rule.required_terms.join(', ')}` : ''}{rule.prohibited_terms?.length ? `: ${rule.prohibited_terms.join(', ')}` : ''}</li>{/each}</ul>
				<div class="actions"><button type="button" disabled={busy} onclick={() => begin(version)}>{version.payload.status === 'draft' ? 'Edit draft' : 'Salin sebagai draft baru'}</button><button type="button" disabled={busy} onclick={() => showAudit(version)}>Riwayat perubahan</button>{#if version.payload.status === 'draft'}<button type="button" class="primary" disabled={busy} onclick={() => { confirming = version; }}>Periksa dan terbitkan</button>{/if}</div>
				{#if confirming?.id === version.id}<div class="confirm"><h4>Terbitkan kebijakan ini?</h4><p>Aturan {categories[version.payload.draft.category]} berlaku mulai {version.payload.draft.effective_from}. Setelah terbit, koreksi dilakukan lewat versi baru.</p><div class="actions"><button type="button" class="primary" disabled={busy} onclick={() => publish(version)}>Ya, terbitkan versi ini</button><button type="button" disabled={busy} onclick={() => { confirming = null; }}>Batal</button></div></div>{/if}
				{#if auditId === version.id}<ol class="audit">{#each audit as event}<li>{auditLabels[event.event_type] ?? 'Kebijakan diperbarui'} · {formatDateTime(event.timestamp)}{event.safe_payload.actor_reference ? ` · ${event.safe_payload.actor_reference}` : ''}</li>{/each}</ol>{/if}
			</article>{/each}
		{/if}
		<nav class="actions" aria-label="Halaman kebijakan"><button type="button" disabled={loading || busy || offset === 0} onclick={() => { offset = Math.max(0, offset - 50); void load(); }}>Sebelumnya</button><span>Halaman {offset / 50 + 1}</span><button type="button" disabled={loading || busy || versions.length < 50} onclick={() => { offset += 50; void load(); }}>Berikutnya</button></nav>
	</section>
</section>

<style>
	.policies { max-width: 1100px; margin: 0 auto; } h1 { font-size: var(--text-title); margin: 0; } header p, .hint { color: var(--color-text-muted); line-height: 1.6; }
	.editor, .versions { margin-top: var(--space-8); } .editor { padding: var(--space-6); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
	h2, h3 { margin: 0 0 var(--space-3); } h2 { font-size: var(--text-xl); } h3 { font-size: var(--text-lg); } h4 { margin-top: 0; }
	.section-heading, .actions { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; } .actions { justify-content: flex-start; }
	.fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-4); } label { display: grid; gap: var(--space-2); margin: var(--space-3) 0; font-size: var(--text-sm); font-weight: 600; min-width: 0; }
	input, select, textarea { width: 100%; min-width: 0; min-height: 44px; padding: var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); font: inherit; background: var(--color-surface); color: var(--color-text); box-sizing: border-box; }
	textarea { resize: vertical; } fieldset { border: 1px solid var(--color-border); padding: var(--space-4); border-radius: var(--radius-sm); margin: var(--space-5) 0; min-width: 0; } legend { padding: 0 var(--space-2); font-weight: 600; }
	.rule { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr) auto; align-items: end; gap: var(--space-3); margin-bottom: var(--space-4); } .rule button { margin-bottom: var(--space-3); }
	button { min-height: 44px; padding: var(--space-3) var(--space-4); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); background: var(--color-surface); color: var(--color-text); cursor: pointer; font: inherit; font-size: var(--text-sm); }
	button.primary { background: var(--color-primary); border-color: var(--color-primary); color: white; font-weight: 600; } button.remove { color: var(--color-danger); } button:disabled { opacity: .55; cursor: default; }
	article { border-top: 1px solid var(--color-border); padding: var(--space-6) 0; } .source { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.7; } li { margin-bottom: var(--space-2); overflow-wrap: anywhere; }
	.notice, .confirm { padding: var(--space-4); background: var(--color-light); border-radius: var(--radius-sm); margin: var(--space-4) 0; }.error { color: var(--color-danger); background: var(--color-danger-soft); }.audit { color: var(--color-text-muted); font-size: var(--text-sm); }
	@media (max-width: 700px) { .fields, .rule { grid-template-columns: minmax(0, 1fr); } .editor { padding: var(--space-4); }.rule { border-bottom: 1px solid var(--color-border); padding-bottom: var(--space-3); } }
</style>
