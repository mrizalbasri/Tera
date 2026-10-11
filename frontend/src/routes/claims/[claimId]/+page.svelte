<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	onMount(() => {
		const claimId = page.params.claimId;
		if (claimId) void goto(`/riwayat/${encodeURIComponent(claimId)}`);
	});
</script>

<svelte:head><title>Detail Klaim</title></svelte:head>
<p>Memuat detail klaim...</p>
