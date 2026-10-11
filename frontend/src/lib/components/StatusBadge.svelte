<script lang="ts">
	import { statusLabels, type Status } from '$lib/api';
	let { status }: { status: Status } = $props();
</script>
<span class="badge {status}"><span aria-hidden="true">●</span> {statusLabels[status] ?? status}</span>
<style>
	.badge { display: inline-flex; align-items: center; gap: .4rem; border-radius: 30px; padding: .4rem .7rem; background: #edf0ec; color: #465448; font-size: .78rem; font-weight: 650; white-space: nowrap; }
	.approved { background: #e1f2e5; color: #245435; }
	.rejected { background: #fbe9e4; color: #903c2b; }
	.needs_clarification, .escalated { background: #fff0ce; color: #765510; }
	.processing { background: #e4edf8; color: #31567b; }
</style>
