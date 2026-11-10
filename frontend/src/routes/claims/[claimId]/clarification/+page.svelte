<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { answerClarification, listClarifications } from '$lib/api/claims';
	import type { Clarification } from '$lib/types/claim';
	import ClarificationFields from '$lib/components/ClarificationFields.svelte';

	let clarification = $state<Clarification | null>(null);
	let answer = $state('');
	let confirmedFields = $state<Record<string, string>>({});
	const structured = $derived(clarification?.fields.some((field) => ['vendor', 'receipt_date', 'total', 'currency', 'category'].includes(field)));
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');
	let generation = 0;

	async function load(claimId: string | undefined) {
		if (!claimId) return;
		const request = ++generation;
		clarification = null;
		confirmedFields = {};
		answer = '';
		error = '';
		loading = true;
		submitting = false;
		try {
			const response = await listClarifications(claimId);
			if (request !== generation) return;
			clarification = response.items.find((item) => item.status === 'open') ?? null;
			if (!clarification) error = 'Tidak ada klarifikasi terbuka untuk klaim ini.';
		} catch (cause) {
			if (request === generation) error = cause instanceof Error ? cause.message : 'Klarifikasi tidak dapat dimuat.';
		} finally {
			if (request === generation) loading = false;
		}
	}

	$effect(() => {
		void load(page.params.claimId);
		return () => { generation++; };
	});

	async function submit() {
		const claimId = page.params.claimId;
		if (!claimId || !clarification || (!structured && !answer.trim()) || submitting) return;
		const request = generation;
		submitting = true;
		error = '';
		try {
			await answerClarification({ claimId, clarificationId: clarification.id, answer: answer.trim(), confirmedFields: structured ? confirmedFields : undefined });
			if (request !== generation) return;
			await goto(`/claims/${encodeURIComponent(claimId)}`);
		} catch (cause) {
			if (request === generation) error = cause instanceof Error ? cause.message : 'Jawaban tidak dapat disimpan.';
		} finally {
			if (request === generation) submitting = false;
		}
	}
</script>

<svelte:head><title>Klarifikasi Klaim</title></svelte:head>
<main class="page">
	<a href={`/claims/${encodeURIComponent(page.params.claimId ?? '')}`}>← Kembali ke klaim</a>
	<h1>Jawaban Klarifikasi</h1>
	{#if error}
		<p id="clarification-error" class="error" role="alert">{error}</p>
	{/if}
	{#if loading}
		<p>Memuat klarifikasi...</p>
	{:else if clarification}
		<form onsubmit={(event) => { event.preventDefault(); void submit(); }}>
			<p>{clarification.question}</p>
			{#if structured}<ClarificationFields fields={clarification.fields} bind:values={confirmedFields} disabled={submitting} />
			{:else}<textarea bind:value={answer} required aria-label="Jawaban klarifikasi" aria-describedby={error ? 'clarification-error' : undefined} placeholder="Tulis jawaban yang akan disimpan di backend"></textarea>{/if}
			<button type="submit" disabled={submitting || (!structured && !answer.trim())}>
				{submitting ? 'Mengirim...' : 'Kirim jawaban'}
			</button>
		</form>
	{/if}
</main>

<style>
	.page { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
	form { margin-top: 1.5rem; padding: 1.25rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	textarea { display: block; width: 100%; min-height: 140px; margin: 1rem 0; padding: .75rem; }
	.error { color: #991b1b; }
</style>
