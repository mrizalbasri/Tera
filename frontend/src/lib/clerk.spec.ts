import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => ({ load: vi.fn(), getToken: vi.fn(), create: vi.fn() }));
vi.mock('@clerk/clerk-js', () => ({
	Clerk: class {
		session = { getToken: sdk.getToken };
		load = sdk.load;
		constructor(key: string) { sdk.create(key); }
	}
}));

beforeEach(() => {
	vi.resetModules();
	vi.clearAllMocks();
	vi.stubEnv('VITE_CLERK_PUBLISHABLE_KEY', `pk_test_${btoa('synthetic.clerk.accounts.dev$')}`);
	vi.stubGlobal('window', { __internal_ClerkUICtor: class {} });
	sdk.load.mockResolvedValue(undefined);
	sdk.getToken.mockResolvedValue('synthetic-session-token');
	vi.stubGlobal('fetch', vi.fn(async () => new Response('{}')));
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('Clerk transport', () => {
	it('skips Clerk in demo mode and restores it when demo ends', async () => {
		const { authFetch, setAuthDemoMode } = await import('./clerk');
		setAuthDemoMode(true);
		await authFetch('/api/reviews');
		await authFetch('/api/reports/claims.csv');
		await authFetch('/api/claims');
		await authFetch('/api/notifications');
		await authFetch('/api/policies');
		expect(sdk.create).not.toHaveBeenCalled();
		expect(sdk.getToken).not.toHaveBeenCalled();
		setAuthDemoMode(false);
		await authFetch('/api/reviews');
		expect(sdk.getToken).toHaveBeenCalledOnce();
	});
	it('attaches a fresh token to protected requests and preserves request data', async () => {
		const { authFetch } = await import('./clerk');
		await authFetch('/api/reviews/id/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"action":"approve"}' });
		const [, init] = vi.mocked(fetch).mock.calls[0];
		expect(new Headers(init?.headers).get('authorization')).toBe('Bearer synthetic-session-token');
		expect(new Headers(init?.headers).get('content-type')).toBe('application/json');
		expect(init?.body).toBe('{"action":"approve"}');
		sdk.getToken.mockResolvedValue('refreshed-token');
		await authFetch('/api/claims?employee_id=other');
		expect(new Headers(vi.mocked(fetch).mock.calls[1][1]?.headers).get('authorization')).toBe('Bearer refreshed-token');
		expect(sdk.create).toHaveBeenCalledTimes(1);
	});

	it.each(['/api/notifications?limit=50', '/api/notifications/id/read', '/api/policies', '/api/policies/id/publish'])('refreshes authentication for workspace request %s', async (path) => {
		const { authFetch } = await import('./clerk');
		await authFetch(path);
		expect(new Headers(vi.mocked(fetch).mock.calls[0][1]?.headers).get('authorization')).toBe('Bearer synthetic-session-token');
		sdk.getToken.mockResolvedValue('renewed-workspace-token');
		await authFetch(path);
		expect(new Headers(vi.mocked(fetch).mock.calls[1][1]?.headers).get('authorization')).toBe('Bearer renewed-workspace-token');
	});

	it('does not initialize Clerk or transmit tokens to public or external paths', async () => {
		const { authFetch } = await import('./clerk');
		await authFetch('/api/health');
		await authFetch('https://external.example/api/reviews');
		await authFetch('https://external.example/api/policies');
		await authFetch('/api/policies-public');
		expect(sdk.create).not.toHaveBeenCalled();
		expect(fetch).toHaveBeenCalledWith('/api/health', undefined);
	});

	it('rejects missing configuration and allows retry after configuration is restored', async () => {
		const { getClerk } = await import('./clerk');
		vi.stubEnv('VITE_CLERK_PUBLISHABLE_KEY', '');
		await expect(getClerk()).rejects.toThrow('belum dikonfigurasi');
		vi.stubEnv('VITE_CLERK_PUBLISHABLE_KEY', `pk_test_${btoa('synthetic.clerk.accounts.dev$')}`);
		await expect(getClerk()).resolves.toBeDefined();
	});

	it('rejects malformed keys before trying to load remote scripts', async () => {
		vi.stubEnv('VITE_CLERK_PUBLISHABLE_KEY', 'pk_test_invalid!');
		const { getClerk } = await import('./clerk');
		await expect(getClerk()).rejects.toThrow('tidak valid');
		expect(sdk.create).not.toHaveBeenCalled();
	});

	it('does not load browser SDK while rendering on the server', async () => {
		vi.stubGlobal('window', undefined);
		const { authFetch, getClerk } = await import('./clerk');
		expect(() => getClerk()).toThrow('browser');
		await authFetch('/api/reports/claims.csv');
		await authFetch('/api/claims');
		expect(sdk.create).not.toHaveBeenCalled();
	});
});
