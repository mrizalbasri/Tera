import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET, POST, PUT } from './[...path]/+server';

type ProxyEvent = Parameters<typeof GET>[0];

function event(path: string, request = new Request(`https://tera.test/api/${path}`), upstream = new Response('{}')) {
	const fetch = vi.fn<typeof globalThis.fetch>(async () => upstream);
	return {
		request,
		params: { path },
		url: new URL(request.url),
		fetch
	} as unknown as ProxyEvent & { fetch: typeof fetch };
}

afterEach(() => vi.restoreAllMocks());

describe('same-origin API proxy', () => {
	it('preserves rate-limit and tracing information for failed requests', async () => {
		const response = Response.json({ code: 'rate_limit_exceeded' }, {
			status: 429,
			headers: { 'Retry-After': '45', 'X-Request-ID': 'synthetic-request', 'X-Content-Type-Options': 'nosniff' }
		});
		const result = await GET(event('claims', undefined, response));
		expect(result.status).toBe(429);
		expect(result.headers.get('retry-after')).toBe('45');
		expect(result.headers.get('x-request-id')).toBe('synthetic-request');
		expect(result.headers.get('x-content-type-options')).toBe('nosniff');
		expect(result.headers.get('cache-control')).toBe('no-store');
		await expect(result.json()).resolves.toEqual({ code: 'rate_limit_exceeded' });
	});

	it.each(['notifications/id/read', 'policies/id/publish'])('forwards authenticated writes to %s with their body', async (path) => {
		const request = new Request(`https://tera.test/api/${path}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: 'Bearer synthetic', Origin: 'https://tera.test' },
			body: '{"revision":2}'
		});
		const input = event(path, request);
		const result = await POST(input);
		expect(result.status).toBe(200);
		const [target, options] = input.fetch.mock.calls[0];
		expect(String(target)).toContain(`/${path}`);
		expect(options?.method).toBe('POST');
		expect(new Headers(options?.headers).get('authorization')).toBe('Bearer synthetic');
		expect(new TextDecoder().decode(options?.body as ArrayBuffer)).toBe('{"revision":2}');
	});

	it('preserves PUT and query filters', async () => {
		const input = event('policies/id', new Request('https://tera.test/api/policies/id?version=2', { method: 'PUT', body: '{}' }));
		await PUT(input);
		const [target, options] = input.fetch.mock.calls[0];
		expect(String(target)).toContain('/policies/id?version=2');
		expect(options?.method).toBe('PUT');
	});

	it.each(['https://external.test', 'policies/../auth', 'unknown'])('rejects a path outside the allowlist: %s', async (path) => {
		const input = event(path);
		expect((await GET(input)).status).toBe(404);
		expect(input.fetch).not.toHaveBeenCalled();
	});

	it('rejects a write from another origin before contacting the backend', async () => {
		const input = event('policies', new Request('https://tera.test/api/policies', { method: 'POST', headers: { Origin: 'https://other.test' } }));
		expect((await POST(input)).status).toBe(403);
		expect(input.fetch).not.toHaveBeenCalled();
	});

	it('returns a safe error when the backend is unreachable', async () => {
		const input = event('notifications');
		input.fetch.mockRejectedValue(new Error('private connection details'));
		const response = await GET(input);
		expect(response.status).toBe(503);
		await expect(response.json()).resolves.toEqual({ code: 'upstream_unavailable' });
	});
});
