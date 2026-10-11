<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	onMount(() => {
		const claimId = page.params.claimId;
		if (claimId) void goto(`/reviews?claim=${encodeURIComponent(claimId)}`);
	});
</script>

<svelte:head><title>Review Klaim</title></svelte:head>
<p>Memuat detail review...</p>
