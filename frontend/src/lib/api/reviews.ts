import { apiRequest } from './client';
import type { ReviewDecisionResponse, ReviewQueueItem, ReviewQueueResponse } from '$lib/types/claim';

export async function listReviews(): Promise<ReviewQueueResponse> {
	const items: ReviewQueueItem[] = [];
	const limit = 100;
	let offset = 0;
	let total: number;
	do {
		const response = await apiRequest<ReviewQueueResponse>(`/reviews?limit=${limit}&offset=${offset}`);
		total = response.total;
		if (response.items.length === 0 && offset < total) {
			throw new Error('Antrean review berubah saat dimuat. Silakan muat ulang.');
		}
		items.push(...response.items);
		offset += limit;
	} while (offset < total);
	return { items, total };
}

export async function decideReview(input: {
	claimId: string;
	action: 'approve' | 'reject';
	reason: string;
}): Promise<ReviewDecisionResponse> {
	return apiRequest<ReviewDecisionResponse>(
		`/reviews/${encodeURIComponent(input.claimId)}/decision`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				action: input.action,
				reason: input.reason
			})
		}
	);
}
