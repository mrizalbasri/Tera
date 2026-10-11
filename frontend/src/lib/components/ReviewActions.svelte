<script lang="ts">
	import { tick } from 'svelte';
	import { post, message } from '$lib/api';
	let { claimId, ondecided }: { claimId: string; ondecided: (id: string) => Promise<void> } = $props();
	let reviewer = $state('');
	let reason = $state('');
	let action = $state<'approve' | 'reject'>('approve');
	let confirming = $state(false);
	let busy = $state(false);
	let error = $state('');
	let completed = $state(false);
	let confirmationButton = $state<HTMLButtonElement>();
	let reviewButton = $state<HTMLButtonElement>();
	async function confirm(event: SubmitEvent) {
		event.preventDefault();
		if (!reviewer.trim() || !reason.trim()) return;
		confirming = true;
		await tick();
		confirmationButton?.focus();
	}
	async function cancel() {
		confirming = false;
		await tick();
		reviewButton?.focus();
	}
	async function decide() {
		if (busy || completed) return;
		const id = claimId;
		busy = true; error = '';
		try {
			await post(`/reviews/${id}/decision`, { action, reason: reason.trim(), reviewer_reference: reviewer.trim() });
			completed = true; confirming = false;
			await ondecided(id);
		} catch (err) { error = message(err); confirming = false; }
		finally { busy = false; }
	}
</script>
<section class="panel" id="review">
	<p class="eyebrow">Tindak lanjut reviewer</p><h2>Tinjau sebelum memutuskan</h2>
	<p class="muted">Periksa hasil pembacaan dan alasan eskalasi. Identitas reviewer dan alasan keputusan akan dicatat.</p>
	{#if error}<div class="notice" role="alert">{error} Muat ulang klaim untuk memeriksa keputusan yang mungkin sudah tersimpan.</div>{/if}
	{#if completed}<p class="notice success" role="status">Keputusan berhasil tersimpan.</p>
	{:else}
		<form onsubmit={confirm}>
			<fieldset disabled={busy || confirming} style="border:0;padding:0;margin:0;min-width:0">
				<div class="field"><label for="reviewer">Referensi reviewer</label><input id="reviewer" bind:value={reviewer} maxlength="100" required /></div>
				<div class="field"><label for="review-action">Keputusan</label><select id="review-action" bind:value={action}><option value="approve">Setujui klaim</option><option value="reject">Tolak klaim</option></select></div>
				<div class="field"><label for="reason">Alasan keputusan</label><textarea id="reason" bind:value={reason} maxlength="2000" required placeholder="Jelaskan pertimbangan berdasarkan bukti klaim."></textarea></div>
				<button bind:this={reviewButton} type="submit" disabled={!reviewer.trim() || !reason.trim()}>Periksa keputusan</button>
			</fieldset>
		</form>
		{#if confirming}<div class="confirmation" role="group" aria-label="Konfirmasi keputusan"><h3>{action === 'approve' ? 'Setujui' : 'Tolak'} klaim ini?</h3><p>Keputusan dan alasan akan disimpan sebagai bagian dari audit klaim.</p><div class="actions"><button bind:this={confirmationButton} class:danger={action === 'reject'} disabled={busy} onclick={decide}>{busy ? 'Menyimpan…' : 'Ya, simpan keputusan'}</button><button class="secondary" disabled={busy} onclick={cancel}>Kembali</button></div></div>{/if}
	{/if}
</section>
<style>.confirmation { padding: 20px; border: 1px solid #cbd9ba; border-radius: 12px; background: #f0f5e7; margin-top: 24px; } .confirmation p { font-size: 13px; }</style>
