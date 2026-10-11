export type Status = 'received' | 'processing' | 'needs_clarification' | 'escalated' | 'approved' | 'rejected';
export interface Claim {
	id: string; employee_id: string; status: Status; submitted_at: string;
	currency: string; declared_amount: string | null; current_decision_id: string | null;
}
export interface Receipt {
	id: string; original_filename: string; quality_score: string | null; quality_findings: string[];
}
export interface Confidence { value: unknown; confidence: string }
export interface Extraction {
	id: string; receipt_id: string; processing_run_id: string | null;
	vendor: Confidence; receipt_date: Confidence; total: Confidence; currency: Confidence; category: Confidence;
	provider: string; provider_degraded: boolean; warnings: string[];
	line_items: { description: string; quantity: string; unit_price: string; total: string }[];
}
export interface Decision {
	id: string; processing_run_id: string; outcome: Status; explanation: string; reason_codes: string[];
	confidence: string | null; anomaly_score: string | null; created_by: string; created_at: string;
}
export interface Finding {
	processing_run_id: string; rule_id: string; passed: boolean; explanation: string; severity: string;
}
export interface Signal {
	id: string; processing_run_id: string; signal_type: string; explanation: string; score: string | null;
}
export interface Detail {
	claim: Claim; receipts: Receipt[]; extractions: Extraction[]; decisions: Decision[];
	validation_findings: Finding[]; policy_evaluations: Finding[]; signals: Signal[];
}
export interface Timeline {
	sequence: number; timestamp: string | null; step_name: string; status: string; summary: string;
	error_code: string | null; processing_run_id: string | null;
}
export interface Clarification { id: string; question: string; answer: string | null; status: string; code: string; fields: string[] }
export interface ReviewItem { review: { id: string }; claim: Claim; decision: Decision | null; signals: Signal[] }

const errorMessages: Record<string, string> = {
	duplicate_receipt: 'Nota yang sama sudah diajukan. Periksa riwayat pengajuan.',
	file_too_large: 'Ukuran nota melebihi batas server. Pilih file yang lebih kecil.',
	invalid_file: 'File nota tidak valid atau kosong. Pilih JPG, PNG, atau PDF yang sesuai.',
	unsupported_media_type: 'Format belum didukung. Gunakan JPG, PNG, atau PDF.',
	malformed_extraction: 'Hasil pembacaan nota tidak valid. Coba proses lagi atau gunakan nota yang lebih jelas.',
	policy_unavailable: 'Kebijakan belum tersedia. Coba lagi setelah layanan pulih.',
	invalid_state_transition: 'Status klaim sudah berubah. Muat ulang untuk melihat status terbaru.',
	not_found: 'Klaim tidak ditemukan.',
	provider_unavailable: 'Layanan pembaca nota belum tersedia. Coba lagi nanti.',
	provider_timeout: 'Pembacaan nota melewati batas waktu. Coba lagi.',
	upstream_unavailable: 'Backend belum dapat dihubungi. Pastikan layanan API berjalan.',
	invalid_claim: 'Permintaan tidak dapat diproses. Periksa isian dan status terbaru klaim.'
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try { response = await fetch(`/api${path}`, init); }
	catch { throw new Error('Koneksi terputus. Periksa jaringan lalu coba lagi.'); }
	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		throw new Error(errorMessages[body.code] ?? (response.status === 422
			? 'Periksa isian formulir. Ada nilai yang belum sesuai.'
			: 'Permintaan gagal. Muat ulang data lalu coba lagi.'));
	}
	return response.json() as Promise<T>;
}
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
export function percent(value: string | null): string {
	return value === null ? '—' : `${Math.round(Number(value) * 100)}%`;
}
export function message(error: unknown): string { return error instanceof Error ? error.message : 'Terjadi kesalahan. Coba lagi.'; }
