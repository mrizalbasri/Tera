<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	onMount(() => {
		const claimId = page.params.claimId;
		if (claimId) void goto(`/riwayat/${encodeURIComponent(claimId)}?clarification=1`);
	});
</script>

<svelte:head><title>Klarifikasi Klaim</title></svelte:head>
<p>Memuat klarifikasi klaim...</p>
