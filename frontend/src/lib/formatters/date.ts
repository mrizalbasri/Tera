const DATE_TIME = new Intl.DateTimeFormat('id-ID', {
	day: 'numeric',
	month: 'short',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit'
});

const DATE_ONLY = new Intl.DateTimeFormat('id-ID', {
	day: 'numeric',
	month: 'short',
	year: 'numeric'
});

export function formatDateTime(iso: string | null | undefined): string {
	if (!iso) return '—';
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? '—' : DATE_TIME.format(date);
}

export function formatDate(iso: string | null | undefined): string {
	if (!iso) return '—';
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? '—' : DATE_ONLY.format(date);
}

export function formatClock(): string {
	return new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}
