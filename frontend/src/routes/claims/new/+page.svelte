<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		void goto('/');
	});
</script>

<svelte:head><title>Ajukan Klaim</title></svelte:head>
<p>Memuat formulir pengajuan klaim...</p>
