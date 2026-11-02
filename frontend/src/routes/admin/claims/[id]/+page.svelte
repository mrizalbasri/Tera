<script lang="ts">
	import ClaimEvidence from '../../../riwayat/[id]/+page.svelte';
	import { page } from '$app/state';
</script>

{#key page.params.id}<ClaimEvidence />{/key}
