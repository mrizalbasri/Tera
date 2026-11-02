import { describe, expect, it, vi } from 'vitest';
import { passwordError, signInWithPassword } from './password-sign-in';

function client(status: string, createdSessionId: string | null = null) {
	return { client: { signIn: { create: vi.fn().mockResolvedValue({ status, createdSessionId }) } }, setActive: vi.fn().mockResolvedValue(undefined) };
}

describe('email and password sign-in', () => {
	it('submits both fields together and activates only a completed session', async () => {
		const clerk = client('complete', 'sess_synthetic');
		await expect(signInWithPassword(clerk, ' user@example.test ', 'synthetic-password')).resolves.toBe('complete');
		expect(clerk.client.signIn.create).toHaveBeenCalledWith({ strategy: 'password', identifier: 'user@example.test', password: 'synthetic-password' });
		expect(clerk.setActive).toHaveBeenCalledWith(expect.objectContaining({ session: 'sess_synthetic', navigate: expect.any(Function) }));
	});

	it.each(['needs_second_factor', 'needs_client_trust', 'needs_new_password', 'needs_first_factor'])('does not activate a session while %s remains', async (status) => {
		const clerk = client(status);
		await expect(signInWithPassword(clerk, 'user@example.test', 'synthetic')).resolves.toBe('verification_required');
		expect(clerk.setActive).not.toHaveBeenCalled();
	});

	it('does not activate a session when the password is rejected', async () => {
		const clerk = client('needs_first_factor');
		clerk.client.signIn.create.mockRejectedValue({ errors: [{ code: 'form_password_incorrect' }] });
		await expect(signInWithPassword(clerk, 'user@example.test', 'wrong')).rejects.toBeDefined();
		expect(clerk.setActive).not.toHaveBeenCalled();
	});

	it('rejects a completed attempt without a session', async () => {
		const clerk = client('complete');
		await expect(signInWithPassword(clerk, 'user@example.test', 'synthetic')).rejects.toThrow('Sesi belum tersedia');
		expect(clerk.setActive).not.toHaveBeenCalled();
	});

	it('uses the same error for unknown accounts and wrong passwords', () => {
		expect(passwordError({ errors: [{ code: 'form_identifier_not_found' }] })).toBe(passwordError({ errors: [{ code: 'form_password_incorrect' }] }));
		expect(passwordError({ errors: [{ code: 'strategy_for_user_invalid' }] })).toContain('Google atau kode email');
		expect(passwordError(new Error('private technical detail'))).not.toContain('private technical detail');
	});
});
