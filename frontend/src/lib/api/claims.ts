import { apiRequest } from './client';
import { compressImageIfLarge } from '$lib/image';
import type {
	ClaimDetailResponse,
	Claim,
	ClaimListResponse,
	ClarificationListResponse,
	CreateClaimResponse,
	ProcessClaimResponse,
	ReplacementReceiptResponse,
	TimelineResponse
} from '$lib/types/claim';

/** Harus sinkron dengan batas backend: settings.max_receipt_size_bytes. */
export const MAX_RECEIPT_SIZE_BYTES = 10 * 1024 * 1024;

export const ALLOWED_RECEIPT_TYPES = ['image/jpeg', 'image/png', 'application/pdf'] as const;

export async function createClaim(input: {
	file: File;
	employeeId?: string;
	declaredAmount?: number | null;
	idempotencyKey?: string;
}): Promise<CreateClaimResponse> {
	const file = await compressImageIfLarge(input.file);
	const form = new FormData();
	if (input.employeeId) {
		form.append('employee_id', input.employeeId);
	}
	form.append('currency', 'IDR');
	if (input.declaredAmount != null) form.append('declared_amount', String(input.declaredAmount));
	form.append('files', file, file.name);

	const headers: Record<string, string> = {};
	if (input.idempotencyKey) headers['Idempotency-Key'] = input.idempotencyKey;

	return apiRequest<CreateClaimResponse>('/claims', {
		method: 'POST',
		body: form,
		headers
	});
}

export async function listClaims(employeeId?: string): Promise<ClaimListResponse> {
	const items: Claim[] = [];
	const ids = new Set<string>();
	const limit = 200;
	let total: number | undefined;
	let offset = 0;
	do {
		const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
		if (employeeId) params.set('employee_id', employeeId);
		const response = await apiRequest<ClaimListResponse>(`/claims?${params}`);
		if ((total !== undefined && response.total !== total) || (response.items.length === 0 && offset < response.total)) {
			throw new Error('Daftar klaim berubah saat dimuat. Silakan muat ulang.');
		}
		total = response.total;
		for (const claim of response.items) {
			if (ids.has(claim.id)) throw new Error('Daftar klaim berubah saat dimuat. Silakan muat ulang.');
			ids.add(claim.id);
		}
		items.push(...response.items);
		offset += limit;
	} while (offset < total);
	if (items.length !== total) throw new Error('Daftar klaim berubah saat dimuat. Silakan muat ulang.');
	return { items, total };
}

export async function getClaim(claimId: string): Promise<ClaimDetailResponse> {
	return apiRequest<ClaimDetailResponse>(`/claims/${encodeURIComponent(claimId)}`);
}

export async function processClaim(
	claimId: string,
	idempotencyKey?: string,
	resume = false
): Promise<ProcessClaimResponse> {
	const headers: Record<string, string> = {};
	if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
	const query = resume ? '?resume=true' : '';
	return apiRequest<ProcessClaimResponse>(`/claims/${encodeURIComponent(claimId)}/process${query}`, {
		method: 'POST',
		headers
	});
}

export async function replaceClaimReceipt(input: {
	claimId: string;
	file: File;
}): Promise<ReplacementReceiptResponse> {
	const file = await compressImageIfLarge(input.file);
	const form = new FormData();
	form.append('file', file, file.name);
	return apiRequest<ReplacementReceiptResponse>(
		`/claims/${encodeURIComponent(input.claimId)}/receipts`,
		{
			method: 'POST',
			body: form
		}
	);
}

export async function listClarifications(claimId: string): Promise<ClarificationListResponse> {
	return apiRequest<ClarificationListResponse>(
		`/claims/${encodeURIComponent(claimId)}/clarifications`
	);
}

/** FR-12: urutan kerja agent sesuai API, sudah redacted oleh backend. */
export async function getClaimTimeline(claimId: string): Promise<TimelineResponse> {
	return apiRequest<TimelineResponse>(`/claims/${encodeURIComponent(claimId)}/timeline`);
}

/**
 * FR-09: mengirim jawaban klarifikasi ke backend. Responsnya adalah hasil
 * pemrosesan lanjutan (termasuk keputusan baru bila ada).
 */
export async function answerClarification(input: {
	claimId: string;
	clarificationId: string;
	answer: string;
	answeredBy?: string;
	confirmedFields?: Record<string, string>;
}): Promise<ProcessClaimResponse> {
	const body: { answer: string; answered_by?: string; confirmed_fields?: Record<string, string> } = {
		answer: input.answer
	};
	if (input.confirmedFields) body.confirmed_fields = input.confirmedFields;
	if (input.answeredBy) {
		body.answered_by = input.answeredBy;
	}
	return apiRequest<ProcessClaimResponse>(
		`/claims/${encodeURIComponent(input.claimId)}/clarifications/${encodeURIComponent(
			input.clarificationId
		)}/answer`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		}
	);
}
