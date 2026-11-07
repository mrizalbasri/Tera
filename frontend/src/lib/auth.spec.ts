import { describe, it, expect, vi, beforeEach } from 'vitest';
import { login, logout, getSession, authFetch, setAuthDemoMode, setAuthToken, getAuthToken } from './auth';

describe('Native Auth Client', () => {
	beforeEach(() => {
		setAuthToken(null);
		setAuthDemoMode(false);
		vi.restoreAllMocks();
	});

	it('manages auth token in state and storage', () => {
		expect(getAuthToken()).toBeNull();
		setAuthToken('synthetic-test-jwt-token');
		expect(getAuthToken()).toBe('synthetic-test-jwt-token');
		setAuthToken(null);
		expect(getAuthToken()).toBeNull();
	});

	it('attaches authorization header in authFetch when token exists', async () => {
		setAuthToken('test-bearer-token');
		const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
		vi.stubGlobal('fetch', mockFetch);

		await authFetch('/api/claims');
		expect(mockFetch).toHaveBeenCalledTimes(1);
		const callArgs = mockFetch.mock.calls[0];
		expect(callArgs[0]).toBe('/api/claims');
		const headers = callArgs[1]?.headers as Headers;
		expect(headers.get('Authorization')).toBe('Bearer test-bearer-token');
	});

	it('returns mock user in demo mode without network request', async () => {
		const mockFetch = vi.fn();
		vi.stubGlobal('fetch', mockFetch);
		setAuthDemoMode(true);

		const session = await getSession();
		expect(session).toEqual({
			username: 'demo-reviewer',
			role: 'admin',
			demo_mode: true
		});
		expect(mockFetch).not.toHaveBeenCalled();
	});

	it('performs login call and stores token', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			new Response(JSON.stringify({ username: 'finance@tera.id', role: 'admin', token: 'jwt-returned-token' }), {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', mockFetch);

		const user = await login('finance@tera.id', 'password', 'admin');
		expect(user).toEqual({ username: 'finance@tera.id', role: 'admin' });
		expect(getAuthToken()).toBe('jwt-returned-token');
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/auth/login',
			expect.objectContaining({
				method: 'POST',
				credentials: 'include'
			})
		);
	});

	it('clears token on logout', async () => {
		setAuthToken('jwt-to-clear');
		const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
		vi.stubGlobal('fetch', mockFetch);

		await logout();
		expect(getAuthToken()).toBeNull();
	});

	it('throws service unavailable message when login returns 500+', async () => {
		const mockFetch = vi.fn().mockResolvedValue(new Response('Internal Error', { status: 503 }));
		vi.stubGlobal('fetch', mockFetch);

		await expect(login('finance@tera.id', 'password', 'admin')).rejects.toThrow(
			'Layanan login sedang tidak tersedia. Coba lagi sebentar.'
		);
	});

	it('throws server message or fallback when login returns 4xx', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			new Response(JSON.stringify({ message: 'Akun tidak ditemukan.' }), { status: 401 })
		);
		vi.stubGlobal('fetch', mockFetch);

		await expect(login('unknown', 'password')).rejects.toThrow('Akun tidak ditemukan.');
	});
});
