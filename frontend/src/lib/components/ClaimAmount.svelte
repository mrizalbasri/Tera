<script lang="ts">
	import type { Claim } from '$lib/types/claim';
	import { formatCurrency } from '$lib/formatters/currency';
	let { claim }: { claim: Claim } = $props();
	const labels = { final: 'Nominal final', extraction: 'Hasil pembacaan nota', declared: 'Pengajuan · belum diverifikasi', unavailable: 'Perlu konfirmasi nominal' };
</script>

<span class="claim-value">
	<strong>{claim.amount?.value == null ? 'Belum tersedia' : formatCurrency(claim.amount.value, claim.currency)}</strong>
	<small>{labels[claim.amount?.source ?? 'unavailable']}</small>
	{#if claim.amount?.conflict}<small class="conflict">Berbeda dengan nominal pengajuan</small>{/if}
</span>

<style>
	.claim-value { display: inline-grid; gap: 4px; min-width: 0; white-space: normal; overflow-wrap: anywhere; }
	strong { font-weight: 600; font-variant-numeric: tabular-nums; }
	small { color: var(--color-text-muted); font-size: 11px; line-height: 1.5; }
	.conflict { color: var(--color-warning); }
</style>
