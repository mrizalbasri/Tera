<script lang="ts">
	import { page } from '$app/state';
	import { api, post, message, money, dateTime, percent, statusLabels, type Detail, type Timeline, type Clarification } from '$lib/api';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import ClaimAmount from '$lib/components/ClaimAmount.svelte';
	import ClarificationFields from '$lib/components/ClarificationFields.svelte';
	import ReviewActions from '$lib/components/ReviewActions.svelte';
	let detail = $state<Detail | null>(null);
	let timeline = $state<Timeline[]>([]);
	let clarifications = $state<Clarification[]>([]);
	let loading = $state(true);
	let busy = $state(false);
	let error = $state('');
	let success = $state('');
	let answer = $state('');
	let confirmedFields = $state<Record<string, string>>({});
	let generation = 0;
	let currentDecision = $derived(detail?.decisions.find(item => item.id === detail?.claim.current_decision_id));
	let currentRun = $derived([...timeline].reverse().find(item => item.processing_run_id)?.processing_run_id);
	let openQuestion = $derived(clarifications.find(item => item.status === 'open'));
	const structured = $derived(openQuestion?.fields.some((field) => ['vendor', 'receipt_date', 'total', 'currency', 'category'].includes(field)));
	let currentExtractions = $derived(detail?.receipts.flatMap(receipt => detail?.extractions.filter(item => item.receipt_id === receipt.id).slice(-1) ?? []) ?? []);
	let evidenceRun = $derived(currentExtractions.at(-1)?.processing_run_id ?? currentRun);
	let findings = $derived([...(detail?.validation_findings ?? []), ...(detail?.policy_evaluations ?? [])].filter(item => item.processing_run_id === evidenceRun));
	const stepLabels: Record<string, string> = { 'claim.received': 'Klaim diterima', 'run.started': 'Pemeriksaan dimulai', extraction: 'Nota dibaca', validation: 'Validasi data', policy: 'Pemeriksaan kebijakan', extraction_attempt: 'Percobaan pembacaan', 'signal.anomaly': 'Pemeriksaan anomali', 'signal.duplicate': 'Pemeriksaan duplikat', decision: 'Keputusan', clarification: 'Klarifikasi diminta', 'clarification.answered': 'Klarifikasi dijawab', 'run.completed': 'Pemeriksaan selesai', 'review.opened': 'Review dibuka', 'review.decided': 'Keputusan reviewer' };
	function value(value: unknown): string { return typeof value === 'string' || typeof value === 'number' ? String(value) : 'Belum terbaca'; }
	async function load(id: string) {
		const request = ++generation;
		loading = true; error = ''; detail = null;
		try {
			const [saved, steps, questions] = await Promise.all([
				api<Detail>(`/claims/${id}`), api<{ items: Timeline[] }>(`/claims/${id}/timeline`), api<{ items: Clarification[] }>(`/claims/${id}/clarifications`)
			]);
			if (request !== generation) return;
			detail = saved; timeline = steps.items; clarifications = questions.items;
		} catch (err) { if (request === generation) error = message(err); }
		finally { if (request === generation) loading = false; }
	}
	$effect(() => {
		const id = page.params.claimId;
		success = ''; answer = ''; busy = false;
		confirmedFields = {};
		if (id) void load(id);
	});
	async function process() {
		if (busy || !detail) return;
		const id = detail.claim.id;
		busy = true; error = ''; success = '';
		try {
			await post(`/claims/${id}/process`);
			if (page.params.claimId === id) {
				success = 'Pemeriksaan selesai. Hasil terbaru sudah tersimpan.';
			}
		} catch (err) {
			if (page.params.claimId === id) {
				error = message(err);
			}
		} finally {
			if (page.params.claimId === id) {
				const actionError = error;
				await load(id);
				if (actionError) error = actionError;
			}
			busy = false;
		}
	}
	async function submitAnswer(event: SubmitEvent) {
		event.preventDefault();
		if (busy || !detail || !openQuestion || (!structured && !answer.trim())) return;
		const id = detail.claim.id;
		busy = true; error = ''; success = '';
		try {
			await post(`/claims/${id}/clarifications/${openQuestion.id}/answer`, { answer: answer.trim(), ...(structured ? { confirmed_fields: confirmedFields } : {}) });
			if (page.params.claimId === id) {
				answer = ''; success = 'Jawaban tersimpan dan klaim sudah diperiksa kembali.';
			}
		} catch (err) {
			if (page.params.claimId === id) {
				error = message(err);
			}
		} finally {
			if (page.params.claimId === id) {
				const actionError = error;
				await load(id);
				if (actionError) error = actionError;
			}
			busy = false;
		}
	}
	async function reviewed(id: string) {
		if (page.params.claimId !== id) return;
		success = 'Keputusan reviewer berhasil tersimpan.';
		await load(id);
	}
</script>
<svelte:head><title>Detail klaim · Tera</title></svelte:head>
<div class="section-top"><a href="/riwayat">← Riwayat klaim</a><button class="secondary" onclick={() => load(page.params.claimId!)} disabled={loading || busy}>Muat ulang</button></div>
<p class="eyebrow">Bukti / Pemeriksaan / Keputusan</p><h1>Perjalanan klaimmu.</h1>
{#if success}<p class="notice success" role="status">{success}</p>{/if}
{#if error}<div class="notice" role="alert"><p>{error}</p>{#if !detail}<button class="secondary" onclick={() => load(page.params.claimId!)} disabled={loading}>Coba muat lagi</button>{/if}</div>{/if}
{#if loading}<p class="loading" role="status">Memuat klaim dan jejak pemeriksaan…</p>
{:else if detail}
	<div class="section-top"><div><h2>Klaim {detail.claim.id.slice(0, 8).toUpperCase()}</h2><p class="muted">{detail.claim.employee_id} · {dateTime(detail.claim.submitted_at)} WIB</p></div><StatusBadge status={detail.claim.status} /></div>
	<div class="split"><div>
		<section class="panel result"><p class="eyebrow">Hasil pemeriksaan</p>
			{#if currentDecision}<h2>{statusLabels[currentDecision.outcome]}</h2><p>{currentDecision.explanation}</p><p class="muted">{currentDecision.created_by === 'reviewer' ? 'Diputuskan reviewer' : 'Diputuskan sistem'} · {dateTime(currentDecision.created_at)}</p><div class="decision-metrics"><span>Keyakinan <strong>{percent(currentDecision.confidence)}</strong></span><span>Skor anomali <strong>{percent(currentDecision.anomaly_score)}</strong></span></div>
			{:else}<h2>{detail.claim.status === 'received' ? 'Nota siap diperiksa.' : 'Belum ada keputusan akhir.'}</h2><p class="muted">{detail.claim.status === 'received' ? 'Mulai pembacaan untuk mengekstrak data nota dan memeriksa kebijakan.' : 'Periksa timeline dan tindak lanjut di bawah. Jika proses sebelumnya gagal, kamu bisa mencoba kembali.'}</p>{/if}
			{#if ['received', 'processing'].includes(detail.claim.status)}<button onclick={process} disabled={busy}>{busy ? 'Memeriksa nota…' : detail.claim.status === 'received' ? 'Mulai pemeriksaan' : 'Coba proses kembali'}</button>{/if}
			{#if detail.claim.status === 'escalated'}<p class="muted">Klaim ini menunggu pemeriksaan reviewer. Keputusan sebelumnya tetap tercatat.</p>{/if}
		</section>
		{#if openQuestion}<section class="panel"><p class="eyebrow">Perlu informasi tambahan</p><h2>{openQuestion.fields.includes('participant_count') ? 'Berapa orang yang ikut dalam pengeluaran ini?' : 'Lengkapi informasi klaim'}</h2><p class="muted">{openQuestion.question}</p>
			{#if openQuestion.fields.includes('participant_count')}<p class="muted">Masukkan jumlah peserta sebagai angka bulat, misalnya 2.</p>{/if}
			{#if openQuestion.code === 'extraction_confidence_low'}<p class="muted">Lengkapi data sesuai nota. Jawaban dan bukti akan diteruskan ke finance untuk diverifikasi.</p>{/if}
			<form onsubmit={submitAnswer}>
				{#if structured}<ClarificationFields fields={openQuestion.fields} bind:values={confirmedFields} disabled={busy} />
				{:else}<div class="field"><label for="answer">Jawaban klarifikasi</label><textarea id="answer" bind:value={answer} required maxlength="2000" disabled={busy} placeholder="Isi informasi yang diminta Tera."></textarea></div>{/if}
				<button disabled={busy || (!structured && !answer.trim())}>{busy ? 'Memeriksa jawaban…' : 'Kirim jawaban & periksa ulang'}</button>
			</form>
		</section>{/if}
		<section class="panel"><h2>Hasil pembacaan nota</h2>
			{#if !currentExtractions.length}<p class="muted">Data akan muncul setelah nota berhasil dibaca.</p>{/if}
			{#each currentExtractions as extraction (extraction.id)}
				<div class="extraction"><h3>{value(extraction.vendor.value)}</h3><p class="muted">{extraction.provider.startsWith('mock') ? 'Pembacaan simulasi (mock)' : extraction.provider_degraded ? 'Pembacaan fallback — perlu review' : 'Hasil pembacaan provider'}</p>
				<dl>{#each [{ label: 'Vendor', field: extraction.vendor }, { label: 'Tanggal nota', field: extraction.receipt_date }, { label: 'Total', field: extraction.total }, { label: 'Mata uang', field: extraction.currency }, { label: 'Kategori', field: extraction.category }] as item}<div><dt>{item.label}</dt><dd>{item.label === 'Total' ? money(item.field.value) : value(item.field.value)}<small>Keyakinan {percent(item.field.confidence)}</small></dd></div>{/each}</dl>
				{#if extraction.line_items.length}<div class="table-wrap"><table><thead><tr><th>Rincian</th><th>Jumlah</th><th>Total</th></tr></thead><tbody>{#each extraction.line_items as item}<tr><td>{item.description}</td><td>{item.quantity}</td><td class="amount">{money(item.total)}</td></tr>{/each}</tbody></table></div>{/if}
				{#each extraction.warnings as warning}<p class="muted">Catatan: {warning}</p>{/each}</div>
			{/each}
		</section>
		<section class="panel"><h2>Validasi & kebijakan</h2><p class="muted">Bukti dari pembacaan nota terakhir. Keputusan mengikuti pemeriksaan backend.</p>
			{#each findings.filter(item => !item.passed) as finding}<div class="evidence"><strong>△ Perlu perhatian</strong><p>{finding.explanation}</p><small>{finding.rule_id}</small></div>{/each}
			{#if findings.length}<details><summary>{findings.filter(item => item.passed).length} pemeriksaan lolos · Lihat rincian</summary>{#each findings.filter(item => item.passed) as finding}<div class="evidence"><strong>✓ Lolos</strong><p>{finding.explanation}</p><small>{finding.rule_id}</small></div>{/each}</details>{:else}<p class="muted">Belum ada hasil validasi untuk proses ini.</p>{/if}
			{#each detail.signals.filter(item => item.processing_run_id === evidenceRun) as signal}<div class="evidence"><strong>{signal.signal_type === 'duplicate' ? 'Duplikat' : signal.signal_type === 'anomaly' ? 'Anomali' : 'Status provider'}</strong><p>{signal.explanation}</p></div>{/each}
		</section>
		{#if detail.claim.status === 'escalated'}<ReviewActions claimId={detail.claim.id} ondecided={reviewed} />{/if}
	</div><aside>
		<section class="panel"><h2>Bukti tersimpan</h2><p class="muted">Nominal klaim</p><p class="claim-amount"><ClaimAmount claim={detail.claim} /></p>
			{#each detail.receipts as receipt}<div class="evidence"><strong class="filename">{receipt.original_filename}</strong><p>Kualitas gambar: {percent(receipt.quality_score)}</p>{#each receipt.quality_findings as finding}<p class="muted">{finding}</p>{/each}</div>{/each}
		</section>
		<section class="panel"><h2>Jejak pemeriksaan</h2><details><summary>{timeline.length} aktivitas tercatat</summary><ol class="timeline">{#each timeline as step}<li><strong>{stepLabels[step.step_name] ?? step.step_name.replaceAll('_', ' ')}</strong><span>{statusLabels[step.status as keyof typeof statusLabels] ?? ({ completed: 'Selesai', passed: 'Lolos', failed: 'Gagal', succeeded: 'Berhasil', open: 'Terbuka', info: 'Informasi' } as Record<string, string>)[step.status] ?? step.status}</span><p>{step.summary}</p><small>{dateTime(step.timestamp)}{step.error_code ? ` · ${step.error_code}` : ''}</small></li>{:else}<li><p>Belum ada aktivitas pemeriksaan.</p></li>{/each}</ol></details></section>
		{#if clarifications.some(item => item.status === 'answered')}<section class="panel"><h2>Riwayat klarifikasi</h2>{#each clarifications.filter(item => item.status === 'answered') as item}<div class="evidence"><strong>{item.question}</strong><p>{item.answer}</p></div>{/each}</section>{/if}
	</aside></div>
{/if}
<style>
	.result { border-top: 4px solid #416d45; } .result h2 { line-height: 1.5; } .decision-metrics { display: flex; gap: 28px; margin: 24px 0; font-size: 12px; color: #6a7b68; } .decision-metrics strong { display: block; font-size: 24px; color: #2b5036; margin-top: 8px; }
	.claim-amount { font: 28px 'Georgia', serif; } .filename { overflow-wrap: anywhere; font-size: 13px; }
	dl { margin: 16px 0; } dl > div { display: flex; justify-content: space-between; gap: 16px; padding: 14px 0; border-bottom: 1px solid #e6eadf; font-size: 13px; } dt { color: #6d7c68; } dd { text-align: right; margin: 0; overflow-wrap: anywhere; } dd small { display: block; color: #7a8674; margin-top: 6px; font-size: 10px; }
	.extraction + .extraction { border-top: 2px solid #d4dec8; padding-top: 24px; margin-top: 24px; }
	.timeline { padding-left: 20px; margin: 0; } .timeline li { padding: 0 0 26px 8px; font-size: 12px; } .timeline li::marker { color: #84a56d; } .timeline strong { text-transform: capitalize; display: block; } .timeline span { display: inline-block; padding: 3px 7px; background: #edf1e5; border-radius: 5px; margin-top: 7px; font-size: 10px; } .timeline p { margin: 8px 0; color: #596c53; } .timeline small { color: #7b8875; font-size: 10px; }
</style>
