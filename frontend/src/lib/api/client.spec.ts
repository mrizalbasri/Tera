import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest } from './client';
import { api, post } from '../api';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('apiRequest', () => {
	it('mengembalikan JSON saat respons sukses', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }))
		);
		await expect(apiRequest('/claims')).resolves.toEqual({ ok: true });
		expect(fetch).toHaveBeenCalledWith('/api/claims', undefined);
	});

	it('workspace dan dashboard memakai transport proxy yang sama', async () => {
		const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ items: [] })));
		vi.stubGlobal('fetch', fetchMock);
		await api('/claims?employee_id=EMP-001');
		await post('/reviews/claim-001/decision', { action: 'approve', reason: 'verified' });
		expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/claims?employee_id=EMP-001');
		expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/reviews/claim-001/decision');
		expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'approve', reason: 'verified' })
		});
	});

	it('menormalkan error backend menjadi ApiError dengan pesan pengguna', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(
				async () =>
					new Response(
						JSON.stringify({
							code: 'file_too_large',
							message: 'Receipt exceeds the maximum allowed size.',
							details: { max_bytes: 10485760 }
						}),
						{ status: 413 }
					)
			)
		);
		const error = await apiRequest('/claims').catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		const apiError = error as ApiError;
		expect(apiError.status).toBe(413);
		expect(apiError.code).toBe('file_too_large');
		expect(apiError.message).toBe('Ukuran file melebihi batas maksimal 10 MB.');
		expect(apiError.details).toEqual({ max_bytes: 10485760 });
	});

	it('menormalkan respons error non-JSON (mis. 404 bawaan framework)', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => new Response('Internal Server Error', { status: 500 }))
		);
		const error = await apiRequest('/claims/x').catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		const apiError = error as ApiError;
		expect(apiError.code).toBe('http_500');
		expect(apiError.message).toContain('500');
	});

	it('kegagalan jaringan menjadi ApiError network_error, bukan sukses palsu', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => {
				throw new TypeError('Failed to fetch');
			})
		);
		const error = await apiRequest('/claims').catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		const apiError = error as ApiError;
		expect(apiError.code).toBe('network_error');
		expect(apiError.status).toBe(0);
	});

	it('pesan upstream yang tidak dikenal tidak ditampilkan mentah ke workspace', async () => {
		vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
			code: 'unexpected_provider_failure', message: 'private-provider-payload', detail: 'private-details'
		}), { status: 502 })));
		const error = await api('/claims').catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		expect((error as ApiError).message).toBe('Permintaan gagal (HTTP 502).');
	});
});
