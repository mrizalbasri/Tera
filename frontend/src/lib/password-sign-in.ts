import type { Clerk } from '@clerk/clerk-js';

type PasswordClient = Pick<Clerk, 'setActive'> & {
	client: { signIn: { create(params: { strategy: 'password'; identifier: string; password: string }): Promise<{ status: string | null; createdSessionId: string | null }> } } | undefined;
};

export async function signInWithPassword(clerk: PasswordClient, email: string, password: string): Promise<'complete' | 'verification_required'> {
	if (!clerk.client) throw new Error('Clerk belum siap.');
	const attempt = await clerk.client.signIn.create({ strategy: 'password', identifier: email.trim(), password });
	if (attempt.status !== 'complete') return 'verification_required';
	if (!attempt.createdSessionId) throw new Error('Sesi belum tersedia.');
	await clerk.setActive({
		session: attempt.createdSessionId,
		navigate: async ({ decorateUrl }) => { window.location.assign(decorateUrl('/login')); }
	});
	return 'complete';
}

export function passwordError(cause: unknown): string {
	const code = typeof cause === 'object' && cause !== null && 'errors' in cause && Array.isArray(cause.errors)
		? cause.errors[0]?.code : undefined;
	if (code === 'form_password_incorrect' || code === 'form_identifier_not_found') return 'Email atau password tidak sesuai. Periksa kembali isianmu.';
	if (code === 'strategy_for_user_invalid' || code === 'form_password_not_found') return 'Akun ini belum bisa masuk dengan password. Gunakan Google atau kode email.';
	if (code === 'form_password_pwned') return 'Password perlu diperbarui. Gunakan pemulihan akun di bawah.';
	if (code === 'too_many_requests') return 'Terlalu banyak percobaan. Tunggu sebentar sebelum mencoba lagi.';
	return 'Belum berhasil masuk. Periksa koneksi dan coba lagi, atau gunakan kode email.';
}
