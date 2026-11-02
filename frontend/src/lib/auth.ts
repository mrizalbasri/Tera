/**
 * Native auth client for Tera.
 * Self-contained session management with HTTP-only cookies and local Bearer fallback.
 */

let demoMode = false;
let authToken: string | null = null;

if (typeof window !== 'undefined') {
	try {
		authToken = localStorage.getItem('tera_auth_token');
	} catch {
		authToken = null;
	}
}

export function setAuthDemoMode(mode: boolean): void {
	demoMode = Boolean(mode);
}

export function setAuthToken(token: string | null): void {
	authToken = token;
	if (typeof window !== 'undefined') {
		try {
			if (token) {
				localStorage.setItem('tera_auth_token', token);
			} else {
				localStorage.removeItem('tera_auth_token');
			}
		} catch {
			// localStorage might be unavailable or restricted
		}
	}
}

export function getAuthToken(): string | null {
	return authToken;
}

export interface UserSession {
	username: string;
	role: 'admin' | 'member';
	demo_mode?: boolean;
}

export async function login(username: string, password = '', role = 'member'): Promise<UserSession> {
	const response = await fetch('/api/auth/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username: username.trim(), password, role }),
		credentials: 'include'
	});
	if (!response.ok) {
		const err = await response.json().catch(() => ({}));
		throw new Error(err.message || 'Gagal login. Periksa kembali nama akun.');
	}
	const data = await response.json();
	setAuthToken(data.token);
	return { username: data.username, role: data.role as 'admin' | 'member' };
}

export async function logout(): Promise<void> {
	setAuthToken(null);
	try {
		await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
	} catch {
		// Ignore network failure on logout
	}
	if (typeof window !== 'undefined') {
		window.location.replace('/login');
	}
}

export async function getSession(): Promise<UserSession | null> {
	if (demoMode) {
		return { username: 'demo-reviewer', role: 'admin', demo_mode: true };
	}
	try {
		const response = await authFetch('/api/auth/session');
		if (!response.ok) return null;
		return (await response.json()) as UserSession;
	} catch {
		return null;
	}
}

export async function authFetch(path: string, init?: RequestInit): Promise<Response> {
	if (!authToken) {
		return fetch(path, init);
	}
	const headers = new Headers(init?.headers);
	if (!headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${authToken}`);
	}
	return fetch(path, {
		...init,
		headers
	});
}
