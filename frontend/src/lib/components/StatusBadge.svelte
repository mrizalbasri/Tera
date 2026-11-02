<script lang="ts">
	import type { ClaimStatus } from '$lib/types/claim';

	let { status, size = 'md' }: { status: ClaimStatus; size?: 'sm' | 'md' } = $props();

	/**
	 * FR-08: status tidak dikomunikasikan lewat warna saja — setiap status
	 * punya teks dan ikon/glyph yang berbeda.
	 */
	const PRESENTATION: Record<
		ClaimStatus,
		{ label: string; glyph: string; tone: 'neutral' | 'info' | 'warn' | 'success' | 'danger' }
	> = {
		received: { label: 'Diterima', glyph: '○', tone: 'neutral' },
		processing: { label: 'Sedang diperiksa', glyph: '⟳', tone: 'info' },
		needs_clarification: { label: 'Perlu klarifikasi', glyph: '?', tone: 'warn' },
		escalated: { label: 'Menunggu reviewer', glyph: '!', tone: 'warn' },
		approved: { label: 'Disetujui', glyph: '✓', tone: 'success' },
		rejected: { label: 'Ditolak', glyph: '✕', tone: 'danger' }
	};

	const view = $derived(PRESENTATION[status] ?? PRESENTATION.received);
</script>

<span class="status-badge badge {status} {view.tone} {size}">
	<span class="glyph" aria-hidden="true">{view.glyph}</span>
	{view.label}
</span>

<style>
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.25rem 0.7rem;
		border-radius: var(--radius-sm);
		font-weight: 600;
		white-space: nowrap;
		border: 1px solid transparent;
	}

	.status-badge.sm {
		font-size: 0.7rem;
		padding: 0.2rem 0.6rem;
	}

	.status-badge.md {
		font-size: 0.75rem;
	}

	.glyph {
		font-size: 0.72rem;
		line-height: 1;
	}

	.status-badge.neutral, .status-badge.received {
		background: var(--color-soft);
		color: var(--color-text-muted);
		border-color: var(--color-border);
	}

	.status-badge.info, .status-badge.processing {
		background: var(--color-light);
		color: var(--color-primary-dark);
		border-color: var(--color-border);
	}

	.status-badge.warn, .status-badge.needs_clarification, .status-badge.escalated {
		background: var(--color-warning-soft);
		color: var(--color-warning);
		border-color: var(--color-warning-soft);
	}

	.status-badge.success, .status-badge.approved {
		background: var(--color-success-soft);
		color: var(--color-success);
		border-color: var(--color-success-border);
	}

	.status-badge.danger, .status-badge.rejected {
		background: var(--color-danger-soft);
		color: var(--color-danger);
		border-color: var(--color-danger-soft);
	}
</style>
