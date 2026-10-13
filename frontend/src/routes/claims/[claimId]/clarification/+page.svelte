<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { answerClarification, listClarifications } from '$lib/api/claims';
	import type { Clarification } from '$lib/types/claim';

	let clarification = $state<Clarification | null>(null);
	let answer = $state('');
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');

	onMount(async () => {
		const claimId = page.params.claimId;
		if (!claimId) return;
		try {
			const response = await listClarifications(claimId);
			clarification = response.items.find((item) => item.status === 'open') ?? null;
			if (!clarification) error = 'Tidak ada klarifikasi terbuka untuk klaim ini.';
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Klarifikasi tidak dapat dimuat.';
		} finally {
			loading = false;
		}
	});

	async function submit() {
		const claimId = page.params.claimId;
		if (!claimId || !clarification || !answer.trim() || submitting) return;
		submitting = true;
		error = '';
		try {
			await answerClarification({ claimId, clarificationId: clarification.id, answer: answer.trim() });
			await goto(`/claims/${encodeURIComponent(claimId)}`);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Jawaban tidak dapat disimpan.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Klarifikasi Klaim</title></svelte:head>
<main class="page">
	<a href={`/claims/${encodeURIComponent(page.params.claimId ?? '')}`}>← Kembali ke klaim</a>
	<h1>Jawaban Klarifikasi</h1>
	{#if loading}
		<p>Memuat klarifikasi...</p>
	{:else if error}
		<p class="error" role="alert">{error}</p>
	{:else if clarification}
		<section>
			<p>{clarification.question}</p>
			<textarea bind:value={answer} placeholder="Tulis jawaban yang akan disimpan di backend"></textarea>
			<button type="button" onclick={submit} disabled={submitting || !answer.trim()}>
				{submitting ? 'Mengirim...' : 'Kirim jawaban'}
			</button>
		</section>
	{/if}
</main>

<style>
	.page { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
	section { margin-top: 1.5rem; padding: 1.25rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	textarea { display: block; width: 100%; min-height: 140px; margin: 1rem 0; padding: .75rem; }
	.error { color: #991b1b; }
</style>
