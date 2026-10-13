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
		received: { label: 'Diterima', glyph: '📥', tone: 'neutral' },
		processing: { label: 'Diproses', glyph: '⟳', tone: 'info' },
		needs_clarification: { label: 'Perlu Klarifikasi', glyph: '❓', tone: 'warn' },
		escalated: { label: 'Perlu Review', glyph: '👤', tone: 'warn' },
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
		border-radius: 20px;
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
		background: rgba(100, 116, 139, 0.1);
		color: #475569;
		border-color: rgba(100, 116, 139, 0.2);
	}

	.status-badge.info, .status-badge.processing {
		background: rgba(59, 130, 246, 0.1);
		color: #1d4ed8;
		border-color: rgba(59, 130, 246, 0.2);
	}

	.status-badge.warn, .status-badge.needs_clarification, .status-badge.escalated {
		background: rgba(245, 158, 11, 0.12);
		color: #b45309;
		border-color: rgba(245, 158, 11, 0.25);
	}

	.status-badge.success, .status-badge.approved {
		background: rgba(34, 197, 94, 0.12);
		color: #16a34a;
		border-color: rgba(34, 197, 94, 0.25);
	}

	.status-badge.danger, .status-badge.rejected {
		background: rgba(239, 68, 68, 0.1);
		color: #dc2626;
		border-color: rgba(239, 68, 68, 0.2);
	}
</style>
