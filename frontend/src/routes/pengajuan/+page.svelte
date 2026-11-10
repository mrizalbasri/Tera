<script lang="ts">
	import ClaimChat from '$lib/components/ClaimChat.svelte';
	import { onMount } from 'svelte';
	import { listClaims } from '$lib/api/claims';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import type { Claim } from '$lib/types/claim';
	let activeClaims = $state<Claim[]>([]);
	let recoveryError = $state('');
	onMount(async () => {
		try {
			const response = await listClaims();
			activeClaims = response.items.filter((claim) => ['received', 'processing', 'needs_clarification'].includes(claim.status));
		} catch {
			recoveryError = 'Pengajuan sebelumnya belum dapat dimuat. Periksa Klaim saya sebelum mengunggah ulang.';
		}
	});
</script>

{#if recoveryError}<p role="status">{recoveryError} <a href="/riwayat">Buka Klaim saya</a></p>{/if}
{#if activeClaims.length}
	<details class="saved-claims" open>
		<summary>{activeClaims.length} pengajuan belum selesai — tetap tersimpan</summary>
		<p>Pindah halaman tidak menghapus klaim. Lanjutkan pengajuan berikut tanpa mengunggah ulang.</p>
		{#each activeClaims as claim (claim.id)}
			<a href={`/claims/${encodeURIComponent(claim.id)}`}><span>Lanjutkan {shortClaimRef(claim.id)}</span><StatusBadge status={claim.status} size="sm" /></a>
		{/each}
	</details>
{/if}
<ClaimChat />

<style>
	.saved-claims { padding: 16px; margin-bottom: 16px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-surface); }
	summary { font-weight: 600; cursor: pointer; }
	p { color: var(--color-text-muted); font-size: 13px; }
	a { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding-block: 10px; }
</style>
