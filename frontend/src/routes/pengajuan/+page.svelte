<script lang="ts">
	import ClaimChat from '$lib/components/ClaimChat.svelte';
	let { data } = $props();
</script>

<ClaimChat demoMode={data.demoMode} />
