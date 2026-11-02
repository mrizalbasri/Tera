<script lang="ts">
	import { goto } from '$app/navigation';
	import { createClaim, ALLOWED_RECEIPT_TYPES, MAX_RECEIPT_SIZE_BYTES } from '$lib/api/claims';

	let file = $state<File | null>(null);
	let declaredAmount = $state('');
	let submitting = $state(false);
	let error = $state('');

	function selectFile(event: Event) {
		file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
		error = '';
	}

	async function submit() {
		if (!file || submitting) return;
		if (!ALLOWED_RECEIPT_TYPES.includes(file.type as (typeof ALLOWED_RECEIPT_TYPES)[number])) {
			error = 'Format file tidak didukung.';
			return;
		}
		if (file.size > MAX_RECEIPT_SIZE_BYTES) {
			error = 'Ukuran file melebihi batas maksimal 10 MB.';
			return;
		}
		submitting = true;
		error = '';
		try {
			const response = await createClaim({
				file,
				declaredAmount: declaredAmount ? Number(declaredAmount) : null,
				idempotencyKey: crypto.randomUUID()
			});
			await goto(`/claims/${encodeURIComponent(response.claim.id)}`);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Klaim tidak dapat dikirim.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Ajukan Klaim</title></svelte:head>
<main class="page">
	<a href="/pengajuan">Kembali ke pengajuan</a>
	<h1>Ajukan klaim lewat formulir</h1>
	<p>Unggah foto atau PDF nota. Nominal dapat diisi jika sudah diketahui.</p>
	<form onsubmit={(event) => { event.preventDefault(); void submit(); }}>
		<label>
			Nota
			<input type="file" accept="image/jpeg,image/png,application/pdf" onchange={selectFile} required />
		</label>
		<label>
			Nominal (opsional)
			<input type="number" min="0" step="0.01" bind:value={declaredAmount} />
		</label>
		{#if error}<p class="error" role="alert">{error}</p>{/if}
		<button type="submit" disabled={!file || submitting}>{submitting ? 'Mengirim...' : 'Kirim klaim'}</button>
	</form>
</main>

<style>
	.page { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
	form { display: grid; gap: 1rem; margin-top: 1.5rem; padding: 1.25rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
	label { display: grid; gap: .4rem; font-weight: 600; }
	input { padding: .6rem; }
	.error { color: #991b1b; }
</style>
