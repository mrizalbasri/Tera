import { apiRequest } from './client';
import type {
	ClaimDetailResponse,
	ClaimListResponse,
	ClarificationListResponse,
	CreateClaimResponse,
	ProcessClaimResponse,
	ReplacementReceiptResponse,
	TimelineResponse
} from '$lib/types/claim';

/**
 * Identitas contoh untuk mode demo. Saat login aktif, backend memakai ID akun Clerk.
 */
export const CURRENT_EMPLOYEE_ID = 'salesman-001';

/** Harus sinkron dengan batas backend: settings.max_receipt_size_bytes. */
export const MAX_RECEIPT_SIZE_BYTES = 10 * 1024 * 1024;

export const ALLOWED_RECEIPT_TYPES = ['image/jpeg', 'image/png', 'application/pdf'] as const;

export async function createClaim(input: {
	file: File;
	employeeId?: string;
	declaredAmount?: number | null;
	idempotencyKey?: string;
}): Promise<CreateClaimResponse> {
	const form = new FormData();
	form.append('employee_id', input.employeeId ?? CURRENT_EMPLOYEE_ID);
	form.append('currency', 'IDR');
	if (input.declaredAmount != null) form.append('declared_amount', String(input.declaredAmount));
	form.append('files', input.file, input.file.name);

	const headers: Record<string, string> = {};
	if (input.idempotencyKey) headers['Idempotency-Key'] = input.idempotencyKey;

	return apiRequest<CreateClaimResponse>('/claims', {
		method: 'POST',
		body: form,
		headers
	});
}

export async function listClaims(employeeId?: string): Promise<ClaimListResponse> {
	const query = employeeId ? `?employee_id=${encodeURIComponent(employeeId)}` : '';
	return apiRequest<ClaimListResponse>(`/claims${query}`);
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
	const form = new FormData();
	form.append('file', input.file, input.file.name);
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
}): Promise<ProcessClaimResponse> {
	return apiRequest<ProcessClaimResponse>(
		`/claims/${encodeURIComponent(input.claimId)}/clarifications/${encodeURIComponent(
			input.clarificationId
		)}/answer`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				answer: input.answer,
				answered_by: input.answeredBy ?? CURRENT_EMPLOYEE_ID
			})
		}
	);
}
