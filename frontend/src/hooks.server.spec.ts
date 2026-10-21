import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { RequestEvent } from '@sveltejs/kit';
import { handle } from './hooks.server';

vi.mock('$lib/server/admin', () => ({
	adminCookie: '__session',
	backendUrl: () => 'http://backend.test',
	isAdminPath: (path: string) => /^\/(reviews?|reports)(\/|$)/.test(path),
	isEmployeePath: (path: string) => /^\/(dashboard|pengajuan|riwayat|claims)(\/|$)/.test(path)
}));

const resolve = vi.fn(async () => new Response('workspace'));
beforeEach(() => vi.clearAllMocks());

function request(path: string, session: object | null, status = 200) {
	return {
		url: new URL(path, 'http://frontend.test'),
		cookies: { get: () => undefined },
		locals: {},
		fetch: vi.fn(async () => Response.json(session, { status: session ? status : 401 }))
	} as unknown as RequestEvent;
}

describe('workspace access', () => {
	it.each(['/dashboard', '/pengajuan', '/riwayat', '/claims/example', '/reviews', '/reports'])('redirects anonymous visitors at %s', async (path) => {
		await expect(handle({ event: request(path, null), resolve })).rejects.toMatchObject({ status: 303, location: '/login' });
		expect(resolve).not.toHaveBeenCalled();
	});
	it('allows a member into employee pages and blocks admin pages', async () => {
		const member = { username: 'user_alice', role: 'member' };
		const event = request('/riwayat', member);
		const response = await handle({ event, resolve });
		expect(event.locals.user).toEqual(member);
		expect(event.locals.admin).toBeNull();
		expect(response.headers.get('cache-control')).toBe('no-store');
		await expect(handle({ event: request('/reviews', member), resolve })).rejects.toMatchObject({ status: 403 });
	});
	it('keeps the demo open and redirects the disabled login page', async () => {
		const demo = { username: 'demo-reviewer', role: 'admin', demo_mode: true };
		const event = request('/pengajuan', demo);
		expect((await handle({ event, resolve })).status).toBe(200);
		expect(event.locals.demoMode).toBe(true);
		await expect(handle({ event: request('/login', demo), resolve })).rejects.toMatchObject({ status: 303, location: '/reviews' });
	});
	it('fails closed when session verification is unavailable', async () => {
		await expect(handle({ event: request('/riwayat', {}, 503), resolve })).rejects.toMatchObject({ status: 503 });
	});
});
