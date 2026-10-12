import { apiRequest } from './client';
import type { ReviewDecisionResponse, ReviewQueueResponse } from '$lib/types/claim';

/**
 * Identitas reviewer sementara sampai halaman login tersedia (FR-10:
 * identitas reviewer dikirim eksplisit dan berasal dari respons backend).
 */
export const CURRENT_REVIEWER_ID = 'reviewer-001';

export async function listReviews(): Promise<ReviewQueueResponse> {
	return apiRequest<ReviewQueueResponse>('/reviews');
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
