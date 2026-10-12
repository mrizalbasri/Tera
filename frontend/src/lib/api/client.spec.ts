import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest } from './client';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('apiRequest', () => {
	it('mengembalikan JSON saat respons sukses', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }))
		);
		await expect(apiRequest('/health')).resolves.toEqual({ ok: true });
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
});
