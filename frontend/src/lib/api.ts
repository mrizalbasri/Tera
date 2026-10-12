import { apiRequest as api } from './api/client';
import type { ClaimStatus as Status, Numeric } from './types/claim';

export type {
	ClaimStatus as Status, Claim, Receipt, FieldConfidence as Confidence,
	ExtractionResult as Extraction, Decision, Finding, Signal,
	ClaimDetailResponse as Detail, TimelineEntry as Timeline, Clarification,
	ReviewQueueItem as ReviewItem
} from './types/claim';

export { apiRequest as api } from './api/client';
export function post<T>(path: string, body?: unknown): Promise<T> {
	return api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
}
export const statusLabels: Record<Status, string> = {
	received: 'Siap diproses', processing: 'Dalam pemrosesan', needs_clarification: 'Perlu jawaban',
	escalated: 'Menunggu review', approved: 'Disetujui', rejected: 'Ditolak'
};
export function money(value: unknown, currency = 'IDR'): string {
	if (value === null || value === undefined || value === '') return 'Belum tersedia';
	const number = Number(value);
	return Number.isFinite(number) ? new Intl.NumberFormat('id-ID', { style: 'currency', currency, maximumFractionDigits: 2 }).format(number) : 'Belum tersedia';
}
export function dateTime(value: string | null): string {
	return value ? new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Jakarta' }).format(new Date(value)) : '—';
}
export function percent(value: Numeric | null): string {
	return value === null ? '—' : `${Math.round(Number(value) * 100)}%`;
}
export function message(error: unknown): string { return error instanceof Error ? error.message : 'Terjadi kesalahan. Coba lagi.'; }
