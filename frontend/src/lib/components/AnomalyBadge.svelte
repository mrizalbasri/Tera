<script lang="ts">
	import Icon from './Icon.svelte';
	import type { Signal } from '$lib/types/claim';

	let {
		score = null,
		signal = null,
		size = 'md'
	}: {
		score?: number | string | null;
		signal?: Signal | null;
		size?: 'sm' | 'md' | 'lg';
	} = $props();

	const numericScore = $derived.by(() => {
		if (score != null) return Number(score);
		if (signal?.score != null) return Number(signal.score);
		return null;
	});

	const source = $derived(
		(signal?.evidence?.source as string) || (numericScore != null ? 'ml' : 'none')
	);

	const isHigh = $derived(
		(numericScore != null && numericScore >= 0.7) || signal?.severity === 'warning' || signal?.severity === 'blocking'
	);
	const isMedium = $derived(
		numericScore != null && numericScore >= 0.4 && numericScore < 0.7 && !isHigh
	);
	const isLow = $derived(numericScore != null && numericScore < 0.4);

	const percentage = $derived(
		numericScore != null ? Math.round(numericScore * 100) : null
	);

	const label = $derived.by(() => {
		if (source === 'neutral') return 'Riwayat baru (Netral)';
		if (percentage === null) return 'Tanpa skor ML';
		if (isHigh) return `Anomali Tinggi ${percentage}%`;
		if (isMedium) return `Risiko Sedang ${percentage}%`;
		return `Normal ${percentage}%`;
	});
</script>

{#if numericScore !== null || signal}
	<span
		class="anomaly-badge {size} {isHigh ? 'danger' : isMedium ? 'warning' : isLow ? 'success' : 'neutral'}"
		title={signal?.explanation || `Skor anomali model Isolation Forest: ${percentage}%`}
	>
		<span class="icon">
			<Icon name={isHigh ? 'alert' : isMedium ? 'clock' : 'check'} size={size === 'sm' ? 12 : 14} />
		</span>
		<strong class="label">{label}</strong>
		{#if signal?.detector_version}
			<span class="model-tag">ML</span>
		{/if}
	</span>
{/if}

<style>
	.anomaly-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-weight: 600;
		border-radius: 999px;
		white-space: nowrap;
		letter-spacing: -0.01em;
		transition: transform 0.1s ease;
	}

	.anomaly-badge.sm {
		padding: 2px 8px;
		font-size: 11px;
	}

	.anomaly-badge.md {
		padding: 4px 10px;
		font-size: 12px;
	}

	.anomaly-badge.lg {
		padding: 6px 14px;
		font-size: 13px;
	}

	.anomaly-badge.danger {
		background: var(--color-danger-soft, #fef2f2);
		color: var(--color-danger, #b42335);
		border: 1px solid var(--color-danger, #b42335);
	}

	.anomaly-badge.warning {
		background: var(--color-warning-soft, #fffbeb);
		color: var(--color-warning, #b45309);
		border: 1px solid var(--color-warning-border, #fde68a);
	}

	.anomaly-badge.success {
		background: var(--color-success-soft, #f0fdf4);
		color: var(--color-success, #15803d);
		border: 1px solid var(--color-success-border, #bbf7d0);
	}

	.anomaly-badge.neutral {
		background: var(--color-soft, #f8fafc);
		color: var(--color-text-muted, #64748b);
		border: 1px solid var(--color-border, #e2e8f0);
	}

	.icon {
		display: inline-flex;
		align-items: center;
	}

	.model-tag {
		font-size: 9px;
		font-weight: 700;
		text-transform: uppercase;
		padding: 1px 4px;
		background: rgba(0, 0, 0, 0.08);
		border-radius: 4px;
		letter-spacing: 0.5px;
	}
</style>
