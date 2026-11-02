<script lang="ts">
	import { getClerk } from '$lib/clerk';
	import Icon from './Icon.svelte';
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
	<header><span class="form-kicker">SELAMAT DATANG KEMBALI</span><h2 id="sign-in-heading">Masuk ke ruang kerjamu.</h2><p>Lanjutkan pengajuan dan pemeriksaan klaim di Tera.</p></header>
	<button class="google-button secondary" type="button" onclick={google} disabled={!!busy}><img src="https://img.clerk.com/static/google.png" width="20" height="20" alt="" referrerpolicy="no-referrer" />{busy === 'google' ? 'Membuka Google...' : 'Lanjutkan dengan Google'}</button>
	<div class="divider"><span>atau masuk dengan email</span></div>
	<form onsubmit={submit} aria-busy={busy === 'password'}>
		{#if error}<p id="sign-in-error" class="sign-in-error" role="alert">{error}</p>{/if}
		<div class="field"><label for="login-email">Email kerja</label><div class="email-field"><Icon name="user" size={18} /><input id="login-email" name="email" type="email" autocomplete="username" bind:value={email} required disabled={!!busy} aria-describedby={error ? 'sign-in-error' : undefined} placeholder="nama@perusahaan.com" /></div></div>
		<div class="field"><label for="login-password">Password</label><div class="password-field"><Icon name="shield" size={18} /><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autocomplete="current-password" placeholder="Masukkan password" bind:value={password} required disabled={!!busy} /><button class="password-toggle" type="button" aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'} aria-controls="login-password" aria-pressed={showPassword} onclick={() => (showPassword = !showPassword)} disabled={!!busy}><Icon name="eye" size={18} /><span class="toggle-label">{showPassword ? 'Sembunyikan' : 'Tampilkan'}</span></button></div></div>
		<button class="submit-button" type="submit" disabled={!!busy}><Icon name={busy === 'password' ? 'clock' : 'user'} size={18} />{busy === 'password' ? 'Memeriksa akun...' : 'Masuk ke Tera'}</button>
	</form>
	<button class="recovery-link" type="button" onclick={onverification} disabled={!!busy}>Gunakan kode email atau pulihkan akun</button>
<p class="register-note">Belum punya akun? <a href="/login?flow=signup" data-sveltekit-reload>Daftar sekarang</a></p>
</section>

<style>
	.sign-in-card { padding: 32px 28px 24px; background: var(--color-surface); }
	header { text-align: left; margin-bottom: var(--space-6); }
	.form-kicker { display: block; font-size: 10px; letter-spacing: 1.2px; color: var(--color-primary); font-weight: 700; margin-bottom: 12px; }
	h2 { font-size: 28px; line-height: 1.25; letter-spacing: -.03em; margin: 0 0 var(--space-2); }
	header p { line-height: 1.8; color: var(--color-text-muted); font-size: var(--text-xs); margin: 0; }
	.google-button, .submit-button { width: 100%; min-height: 48px; }
	.google-button { white-space: normal; gap: var(--space-3); font-size: var(--text-sm); border-color: var(--color-text-muted); }
	.divider { display: flex; align-items: center; gap: var(--space-3); margin-block: var(--space-6); color: var(--color-text-muted); font-size: var(--text-xs); }
	.divider::before, .divider::after { content: ''; height: 1px; flex: 1; background: var(--color-border); }
	.field { margin-bottom: var(--space-5); }
	input { min-height: 48px; border-color: var(--color-text-muted); }
	.email-field, .password-field { transition: border-color var(--dur-short) var(--ease-out), background-color var(--dur-short) var(--ease-out); }
	.email-field:hover:not(:has(input:disabled)), .password-field:hover:not(:has(input:disabled)) { border-color: var(--color-primary); background-color: var(--color-soft); }
	.email-field:focus-within, .password-field:focus-within { border-color: var(--color-primary); background-color: var(--color-surface); outline: 3px solid var(--color-focus); outline-offset: 3px; }
	.email-field, .password-field { display: flex; padding-left: 14px; gap: 4px; color: var(--color-text-muted); align-items: center; border: 1px solid var(--color-border-strong); background: var(--color-soft); border-radius: var(--radius-sm); }
	.email-field input, .password-field input { flex: 1; min-width: 0; border: 0; background: transparent; }
	.email-field input:focus-visible, .password-toggle:focus-visible { outline: none; }
	.password-toggle { min-width: 44px; min-height: 48px; padding-inline: var(--space-2); background: transparent; color: var(--color-primary); border: 0; border-radius: 0 calc(var(--radius-sm) - 1px) calc(var(--radius-sm) - 1px) 0; font-size: var(--text-xs); }
	.password-toggle:hover { background: var(--color-light); }
	.password-toggle:focus-visible { background: var(--color-light); text-decoration: underline; text-underline-offset: 4px; }
	.password-toggle:active { transform: none; }
	.recovery-link { display: flex; margin: var(--space-3) auto 0; padding: var(--space-2) 0; min-height: 44px; background: transparent; border: 0; color: var(--color-primary); font-size: var(--text-xs); white-space: normal; text-decoration: underline; text-underline-offset: 4px; }
	.recovery-link:hover { background: transparent; color: var(--color-primary-dark); }
	.sign-in-error { color: var(--color-danger); background: var(--color-danger-soft); padding: var(--space-3); border-left: 3px solid var(--color-danger); font-size: var(--text-sm); }
	.toggle-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
	.register-note { margin: 20px 0 0; padding-top: 20px; border-top: 1px solid var(--color-border); text-align: center; color: var(--color-text-muted); font-size: 12px; }
	.register-note a { font-weight: 700; display: inline-flex; align-items: center; min-height: 44px; }
	@media (max-width: 374px) { .sign-in-card { padding-inline: var(--space-4); } }
</style>
