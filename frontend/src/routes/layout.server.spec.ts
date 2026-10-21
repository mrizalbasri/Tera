import { describe, expect, it } from 'vitest';
import { load } from './+layout.server';

const session = { username: 'reviewer', role: 'admin' };
const layout = load as (input: { locals: { user: object; admin: object | null; demoMode: boolean }; url: URL }) => { financeWorkspace: boolean; admin: object | null };

describe('workspace presentation', () => {
	it.each(['/reviews', '/reviews/example', '/reports', '/dashboard', '/admin/claims', '/admin/claims/example'])('retains finance context at %s for verified admins', (path) => {
		expect(layout({ locals: { user: session, admin: session, demoMode: false }, url: new URL(path, 'http://localhost') }).financeWorkspace).toBe(true);
	});
	it.each(['/pengajuan', '/riwayat', '/riwayat/example', '/claims/example/clarification'])('keeps personal work separate at %s', (path) => {
		const result = layout({ locals: { user: session, admin: session, demoMode: true }, url: new URL(path, 'http://localhost') });
		expect(result.financeWorkspace).toBe(false);
		expect(result.admin).toEqual(session);
	});
	it('does not grant admin access through a workspace URL', () => {
		const result = layout({ locals: { user: { role: 'member' }, admin: null, demoMode: false }, url: new URL('http://localhost/admin/claims?role=admin') });
		expect(result.financeWorkspace).toBe(false);
		expect(result.admin).toBeNull();
	});
});
