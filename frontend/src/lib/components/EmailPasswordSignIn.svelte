<script lang="ts">
	import { getClerk } from '$lib/clerk';
	import { passwordError, signInWithPassword } from '$lib/password-sign-in';
	let { onverification }: { onverification: () => Promise<void> } = $props();
	let email = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let busy = $state<'password' | 'google' | null>(null);
	let error = $state('');

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (busy) return;
		busy = 'password'; error = '';
		try {
			const result = await signInWithPassword(await getClerk(), email, password);
			password = '';
			if (result === 'verification_required') await onverification();
		} catch (cause) { error = passwordError(cause); }
		finally { busy = null; }
	}
	async function google() {
		if (busy) return;
		busy = 'google'; error = '';
		try {
			const clerk = await getClerk();
			if (!clerk.client) throw new Error('Clerk belum siap.');
			await clerk.client.signIn.authenticateWithRedirect({ strategy: 'oauth_google', redirectUrl: '/sso-callback', redirectUrlComplete: '/login' });
		} catch { error = 'Login Google belum dapat dibuka. Coba lagi.'; busy = null; }
	}
</script>

<section class="sign-in-card" aria-labelledby="sign-in-heading">
	<header><img src="/logo.webp" width="40" height="40" alt="" /><h2 id="sign-in-heading">Masuk ke Tera</h2><p>Gunakan akun kerjamu untuk melanjutkan.</p></header>
	<button class="google-button secondary" type="button" onclick={google} disabled={!!busy}><img src="https://img.clerk.com/static/google.png" width="20" height="20" alt="" referrerpolicy="no-referrer" />{busy === 'google' ? 'Membuka Google...' : 'Lanjutkan dengan Google'}</button>
	<div class="divider"><span>atau masuk dengan email</span></div>
	<form onsubmit={submit} aria-busy={busy === 'password'}>
		{#if error}<p id="sign-in-error" class="sign-in-error" role="alert">{error}</p>{/if}
		<div class="field"><label for="login-email">Email kerja</label><input id="login-email" name="email" type="email" autocomplete="username" bind:value={email} required disabled={!!busy} aria-describedby={error ? 'sign-in-error' : undefined} /></div>
		<div class="field"><label for="login-password">Password</label><div class="password-field"><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autocomplete="current-password" bind:value={password} required disabled={!!busy} /><button class="password-toggle" type="button" aria-controls="login-password" aria-pressed={showPassword} onclick={() => (showPassword = !showPassword)} disabled={!!busy}>{showPassword ? 'Sembunyikan' : 'Tampilkan'}</button></div></div>
		<button class="submit-button" type="submit" disabled={!!busy}>{busy === 'password' ? 'Memeriksa akun...' : 'Masuk ke Tera'}</button>
	</form>
	<button class="recovery-link" type="button" onclick={onverification} disabled={!!busy}>Gunakan kode email atau pulihkan akun</button>
</section>

<style>
	.sign-in-card { padding: var(--space-8) var(--space-6) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
	header { text-align: center; margin-bottom: var(--space-6); }
	header img { display: block; margin: 0 auto var(--space-4); }
	h2 { font-size: var(--text-xl); letter-spacing: -.03em; margin: 0 0 var(--space-2); }
	header p { color: var(--color-text-muted); font-size: var(--text-xs); margin: 0; }
	.google-button, .submit-button { width: 100%; min-height: 48px; }
	.google-button { white-space: normal; gap: var(--space-3); font-size: var(--text-sm); border-color: var(--color-text-muted); }
	.divider { display: flex; align-items: center; gap: var(--space-3); margin-block: var(--space-6); color: var(--color-text-muted); font-size: var(--text-xs); }
	.divider::before, .divider::after { content: ''; height: 1px; flex: 1; background: var(--color-border); }
	.field { margin-bottom: var(--space-5); }
	input { min-height: 48px; border-color: var(--color-text-muted); }
	.field > input, .password-field { transition: border-color var(--dur-short) var(--ease-out), background-color var(--dur-short) var(--ease-out); }
	.field > input:hover:not(:disabled), .password-field:hover:not(:has(input:disabled)) { border-color: var(--color-primary); background-color: var(--color-soft); }
	.field > input:focus-visible, .password-field:focus-within { border-color: var(--color-primary); background-color: var(--color-surface); outline: 3px solid var(--color-focus); outline-offset: 3px; }
	.password-field { display: flex; align-items: stretch; border: 1px solid var(--color-text-muted); border-radius: var(--radius-sm); }
	.password-field input { flex: 1; min-width: 0; border: 0; background: transparent; }
	.password-field input:focus-visible, .password-toggle:focus-visible { outline: none; }
	.password-toggle { min-width: 88px; padding-inline: var(--space-2); background: transparent; color: var(--color-primary); border: 0; border-radius: 0 calc(var(--radius-sm) - 1px) calc(var(--radius-sm) - 1px) 0; font-size: var(--text-xs); }
	.password-toggle:hover { background: var(--color-light); }
	.password-toggle:focus-visible { background: var(--color-light); text-decoration: underline; text-underline-offset: 4px; }
	.password-toggle:active { transform: none; }
	.recovery-link { display: flex; margin: var(--space-3) auto 0; padding: var(--space-2) 0; min-height: 44px; background: transparent; border: 0; color: var(--color-primary); font-size: var(--text-xs); white-space: normal; text-decoration: underline; text-underline-offset: 4px; }
	.recovery-link:hover { background: transparent; color: var(--color-primary-dark); }
	.sign-in-error { color: var(--color-danger); background: var(--color-danger-soft); padding: var(--space-3); border-left: 3px solid var(--color-danger); font-size: var(--text-sm); }
	@media (max-width: 374px) { .sign-in-card { padding-inline: var(--space-4); } }
</style>
