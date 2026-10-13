import { afterEach, describe, expect, it, vi } from 'vitest';
import { processClaim, replaceClaimReceipt } from './claims';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('claim submission APIs', () => {
	it('sends an idempotency key when processing a claim', async () => {
		const fetchMock = vi.fn(
			async (_input: RequestInfo | URL, init?: RequestInit) =>
				new Response(JSON.stringify({ claim: { id: 'claim-1' } }), {
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				})
		);
		vi.stubGlobal('fetch', fetchMock);

		await processClaim('claim-1', 'process-key-1');

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/claims/claim-1/process',
			expect.objectContaining({
				method: 'POST',
				headers: { 'Idempotency-Key': 'process-key-1' }
			})
		);
	});

	it('uploads a replacement receipt without creating a new claim request', async () => {
		const fetchMock = vi.fn(
			async (_input: RequestInfo | URL, init?: RequestInit) => {
				expect(init?.body).toBeInstanceOf(FormData);
				expect((init?.body as FormData).get('file')).toBeInstanceOf(File);
				return new Response(
					JSON.stringify({
						claim: { id: 'claim-1' },
						receipt: { id: 'receipt-2', claim_id: 'claim-1' }
					}),
					{ status: 201, headers: { 'Content-Type': 'application/json' } }
				);
			}
		);
		vi.stubGlobal('fetch', fetchMock);

		await replaceClaimReceipt({
			claimId: 'claim-1',
			file: new File([new Uint8Array([1, 2, 3])], 'clearer.pdf', {
				type: 'application/pdf'
			})
		});

		expect(fetchMock).toHaveBeenCalledWith(
			'/api/claims/claim-1/receipts',
			expect.objectContaining({ method: 'POST' })
		);
	});
});
