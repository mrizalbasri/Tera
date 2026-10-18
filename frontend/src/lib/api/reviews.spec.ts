import { afterEach, describe, expect, it, vi } from 'vitest';
import { listReviews } from './reviews';

afterEach(() => vi.unstubAllGlobals());

describe('review queue pagination', () => {
	it('loads reviews beyond the first 100 so a later claim can be reviewed', async () => {
		const first = Array.from({ length: 100 }, (_, i) => ({ review: { id: `review-${i}` }, claim: { id: `claim-${i}` } }));
		const last = { review: { id: 'review-100' }, claim: { id: 'claim-100' } };
		const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
			const offset = new URL(String(input), 'http://localhost').searchParams.get('offset');
			return Response.json({ items: offset === '100' ? [last] : first, total: 101 });
		});
		vi.stubGlobal('fetch', fetchMock);
		const result = await listReviews();
		expect(result.items).toHaveLength(101);
		expect(result.items.at(-1)?.claim.id).toBe('claim-100');
		expect(fetchMock).toHaveBeenCalledTimes(2);
	});

	it('fails instead of showing an incomplete queue when a later page fails', async () => {
		const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ items: [{ review: { id: 'review-1' } }], total: 101 }))
			.mockResolvedValueOnce(Response.json({ message: 'Unavailable' }, { status: 503 }));
		vi.stubGlobal('fetch', fetchMock);
		await expect(listReviews()).rejects.toThrow();
	});
});
