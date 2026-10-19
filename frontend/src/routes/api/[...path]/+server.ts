import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const proxy: RequestHandler = async ({ request, params, url, fetch }) => {
	const path = params.path ?? '';
	// Limit forwarding to the existing claim/review/report API, never arbitrary URLs.
	if (!/^(claims|reviews|reports|health|auth)(\/|$)/.test(path) || path.split('/').some(part => part === '.' || part === '..')) {
		return new Response(null, { status: 404 });
	}
	const target = new URL(`${path}${url.search}`, `${(env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')}/`);
	const headers = new Headers();
	if (request.method !== 'GET' && request.headers.get('origin') && request.headers.get('origin') !== url.origin) {
		return Response.json({ code: 'invalid_origin' }, { status: 403 });
	}
	for (const name of ['content-type', 'idempotency-key', 'cookie', 'origin', 'authorization']) {
		const value = request.headers.get(name);
		if (value) headers.set(name, value);
	}
	try {
		const upstream = await fetch(target, {
			method: request.method, headers, redirect: 'error',
			body: request.method === 'GET' ? undefined : await request.arrayBuffer()
		});
		const responseHeaders = new Headers({
			'Content-Type': upstream.headers.get('content-type') || 'application/json',
			'Cache-Control': 'no-store'
		});
		for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('Set-Cookie', cookie);
		return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
	} catch {
		return Response.json({ code: 'upstream_unavailable' }, { status: 503 });
	}
};
export const GET = proxy;
export const POST = proxy;
