import { apiRequest } from './client';
import type { ReviewDecisionResponse, ReviewQueueItem, ReviewQueueResponse } from '$lib/types/claim';

/**
 * Identitas reviewer sementara sampai halaman login tersedia (FR-10:
 * identitas reviewer dikirim eksplisit dan berasal dari respons backend).
 */
export const CURRENT_REVIEWER_ID = 'reviewer-001';

export async function listReviews(): Promise<ReviewQueueResponse> {
	const items: ReviewQueueItem[] = [];
	const reviewIds = new Set<string>();
	const limit = 100;
	let offset = 0;
	let total: number | undefined;
	let snapshot: string | undefined;
	do {
		const versionQuery = snapshot === undefined ? '' : `&snapshot=${encodeURIComponent(snapshot)}`;
		const response = await apiRequest<ReviewQueueResponse>(`/reviews?limit=${limit}&offset=${offset}${versionQuery}`);
		if (snapshot !== undefined && response.snapshot !== snapshot) {
			throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
		}
		snapshot = response.snapshot;
		if (total !== undefined && response.total !== total) {
			throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
		}
		total = response.total;
		if (response.items.length === 0 && offset < total) {
			throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
		}
		for (const item of response.items) {
			if (reviewIds.has(item.review.id)) {
				throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
			}
			reviewIds.add(item.review.id);
		}
		items.push(...response.items);
		offset += limit;
	} while (offset < total);
	if (items.length !== total) {
		throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
	}
	return { items, total };
}

export async function decideReview(input: {
	claimId: string;
	action: 'approve' | 'reject';
	reason: string;
	reviewerReference?: string;
}): Promise<ReviewDecisionResponse> {
	return apiRequest<ReviewDecisionResponse>(
		`/reviews/${encodeURIComponent(input.claimId)}/decision`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				action: input.action,
				reason: input.reason,
				reviewer_reference: input.reviewerReference ?? CURRENT_REVIEWER_ID
			})
		}
	);
}
