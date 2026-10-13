<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		void goto('/reviews');
	});
</script>

<svelte:head><title>Review Klaim</title></svelte:head>
<p>Mengalihkan ke /reviews...</p>
