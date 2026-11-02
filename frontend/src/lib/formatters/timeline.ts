/** Formatter langkah timeline dari GET /claims/{id}/timeline (FR-12). */

export interface TimelineStepInfo {
	label: string;
}

const STEP_NAMES: Record<string, TimelineStepInfo> = {
	'claim.received': { label: 'Klaim diterima' },
	extraction: { label: 'Ekstraksi nota (OCR)' },
	extraction_attempt: { label: 'Percobaan ekstraksi' },
	validation: { label: 'Validasi deterministik' },
	policy: { label: 'Evaluasi kebijakan' },
	decision: { label: 'Keputusan agent' },
	clarification: { label: 'Klarifikasi dibuka' },
	'clarification.answered': { label: 'Klarifikasi dijawab' },
	'run.started': { label: 'Run pemrosesan dimulai' },
	'run.completed': { label: 'Run pemrosesan selesai' },
	'review.opened': { label: 'Dieruskan ke reviewer' },
	'review.decided': { label: 'Reviewer memutuskan' }
};

export function describeTimelineStep(stepName: string): TimelineStepInfo {
	const known = STEP_NAMES[stepName];
	if (known) return known;
	// step_name audit.<event_type> — humanize tanpa mengarang arti
	const humanized = stepName
		.replace(/^audit\./, 'Audit: ')
		.split(/[_\s.]+/)
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
	return { label: humanized || stepName };
}

export type TimelineTone = 'success' | 'danger' | 'warn' | 'info' | 'neutral';

/** Status tidak dikomunikasikan lewat warna saja — tone selalu dengan glyph. */
export function timelineTone(status: string): TimelineTone {
	if (['succeeded', 'completed', 'answered', 'approved', 'decided'].includes(status)) return 'success';
	if (['failed', 'rejected'].includes(status)) return 'danger';
	if (['needs_clarification', 'open', 'escalated'].includes(status)) return 'warn';
	if (['running', 'queued', 'processing'].includes(status)) return 'info';
	return 'neutral';
}

export function timelineGlyph(tone: TimelineTone): string {
	switch (tone) {
		case 'success':
			return '✓';
		case 'danger':
			return '✕';
		case 'warn':
			return '?';
		case 'info':
			return '⟳';
		default:
			return '·';
	}
}

export function formatDuration(ms: number | null | undefined): string | null {
	if (ms == null || ms < 0) return null;
	if (ms < 1000) return `${ms} ms`;
	return `${(ms / 1000).toFixed(1)} dtk`;
}
