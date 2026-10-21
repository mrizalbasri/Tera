import { afterEach, describe, expect, it, vi } from 'vitest';
import { listClaims, processClaim, replaceClaimReceipt } from './claims';

afterEach(() => vi.unstubAllGlobals());

describe('claim submission APIs', () => {
	it('sends an idempotency key when processing a claim', async () => {
		const fetchMock = vi.fn(async () => Response.json({ claim: { id: 'claim-1' } }));
		vi.stubGlobal('fetch', fetchMock);
		await processClaim('claim-1', 'process-key-1');
		expect(fetchMock).toHaveBeenCalledWith('/api/claims/claim-1/process', expect.objectContaining({
			method: 'POST', headers: { 'Idempotency-Key': 'process-key-1' }
		}));
	});
	it('uploads a replacement receipt without creating a new claim request', async () => {
		const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
			expect(init?.body).toBeInstanceOf(FormData);
			expect((init?.body as FormData).get('file')).toBeInstanceOf(File);
			return Response.json({ claim: { id: 'claim-1' }, receipt: { id: 'receipt-2', claim_id: 'claim-1' } }, { status: 201 });
		});
		vi.stubGlobal('fetch', fetchMock);
		await replaceClaimReceipt({ claimId: 'claim-1', file: new File([new Uint8Array([1, 2, 3])], 'clearer.pdf', { type: 'application/pdf' }) });
		expect(fetchMock).toHaveBeenCalledWith('/api/claims/claim-1/receipts', expect.objectContaining({ method: 'POST' }));
	});
});

describe('complete claim overview', () => {
	it('loads older claims beyond the first page and keeps the employee filter', async () => {
		const first = Array.from({ length: 200 }, (_, i) => ({ id: `claim-${i}` }));
		const fetchMock = vi.fn()
			.mockResolvedValueOnce(Response.json({ items: first, total: 201 }))
			.mockResolvedValueOnce(Response.json({ items: [{ id: 'claim-200' }], total: 201 }));
		vi.stubGlobal('fetch', fetchMock);
		const result = await listClaims('user+test');
		expect(result.items).toHaveLength(201);
		const params = new URL(String(fetchMock.mock.calls[1][0]), 'http://localhost').searchParams;
		expect(params.get('offset')).toBe('200');
		expect(params.get('employee_id')).toBe('user+test');
	});
	it('rejects a changed count instead of showing incorrect dashboard metrics', async () => {
		vi.stubGlobal('fetch', vi.fn()
			.mockResolvedValueOnce(Response.json({ items: Array.from({ length: 200 }, (_, i) => ({ id: `${i}` })), total: 201 }))
			.mockResolvedValueOnce(Response.json({ items: [], total: 200 })));
		await expect(listClaims()).rejects.toThrow('Daftar klaim berubah');
	});
	it('rejects duplicate page entries instead of counting a claim twice', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ items: [{ id: 'one' }, { id: 'one' }], total: 2 })));
		await expect(listClaims()).rejects.toThrow('Daftar klaim berubah');
	});
	it('returns an honest empty overview', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ items: [], total: 0 })));
		await expect(listClaims()).resolves.toEqual({ items: [], total: 0 });
	});
});
