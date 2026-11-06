<script lang="ts">
	import { onMount } from 'svelte';
	import { login, getSession } from '$lib/auth';
	import AuthStory from '$lib/components/AuthStory.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let username = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let busy = $state(false);
	let error = $state('');

	async function checkExistingSession() {
		try {
			const session = await getSession();
			if (session) {
				window.location.replace(session.role === 'admin' ? '/reviews' : '/pengajuan');
			}
		} catch {
			// ignore
		}
	}

	onMount(() => {
		void checkExistingSession();
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (busy || !username.trim()) return;
		busy = true;
		error = '';
		try {
			// Peran ditentukan backend dari akun; nilai 'member' hanya default aman.
			const session = await login(username.trim(), password, 'member');
			window.location.replace(session.role === 'admin' ? '/reviews' : '/pengajuan');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Login gagal. Coba lagi.';
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Masuk · Tera</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main id="main-content" class="login-page" tabindex="-1">
	<AuthStory />
	<section class="login-form-area" aria-label="Akses akun Tera">
		<div class="login-content">
			<div class="auth-topline">
				<a href="/" class="login-back"><Icon name="home" size={16} />Beranda</a>
				<span>AKUN KERJA TERA</span>
			</div>

			<div class="auth-panel">
				<div class="login-card">
					<header>
						<span class="form-kicker">SELAMAT DATANG</span>
						<h2>Masuk ke ruang kerjamu.</h2>
						<p>Gunakan akun kerja yang terdaftar di perusahaanmu.</p>
					</header>

					{#if error}
						<div class="sign-in-error" role="alert">
							<Icon name="alert" size={18} />
							<span>{error}</span>
						</div>
					{/if}

					<form onsubmit={handleSubmit} aria-busy={busy}>
						<div class="field">
							<label for="login-username">Email atau Username</label>
							<div class="input-wrap">
								<Icon name="user" size={18} />
								<input
									id="login-username"
									name="username"
									type="text"
									autocomplete="username"
									bind:value={username}
									required
									disabled={busy}
									placeholder="nama@perusahaan.com"
								/>
							</div>
						</div>

						<div class="field">
							<label for="login-password">Password</label>
							<div class="input-wrap">
								<Icon name="shield" size={18} />
								<input
									id="login-password"
									name="password"
									type={showPassword ? 'text' : 'password'}
									autocomplete="current-password"
									bind:value={password}
									disabled={busy}
									placeholder="Password"
								/>
								<button
									class="password-toggle"
									type="button"
									aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'}
									aria-pressed={showPassword}
									aria-controls="login-password"
									disabled={busy}
									onclick={() => { showPassword = !showPassword; }}
								>
									<Icon name={showPassword ? 'eye-off' : 'eye'} size={18} />
								</button>
							</div>
						</div>

						<button class="submit-button" type="submit" disabled={busy || !username.trim()}>
							<Icon name={busy ? 'clock' : 'check'} size={18} />
							<span>{busy ? 'Menghubungkan...' : 'Masuk ke Tera'}</span>
						</button>
					</form>
				</div>
			</div>

			<p class="login-help">
				<Icon name="shield" size={16} />
				<span>Sesi terenkripsi · akses sesuai peran · setiap keputusan tercatat</span>
			</p>
		</div>
	</section>
</main>

<style>
	.login-page { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); min-height: 100svh; }
	.login-form-area { display: flex; align-items: center; justify-content: center; padding: 24px clamp(20px, 3.5vw, 48px); background: var(--color-paper); overflow-y: auto; }
	.login-content { width: 100%; max-width: 448px; margin: auto; }
	.auth-topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
	.auth-topline > span { font-size: 10px; font-weight: 600; letter-spacing: 1.2px; color: var(--color-text-muted); }
	.login-back { display: inline-flex; align-items: center; gap: 8px; min-height: 36px; color: var(--color-text-muted); font-size: 12px; text-decoration: none; transition: color var(--dur-short) ease; }
	.login-back:hover { color: var(--color-primary); }
	.auth-panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 16px; box-shadow: var(--shadow-md); overflow: clip; }
	.login-card { padding: 28px 28px 24px; }
	header { margin-bottom: 20px; }
	.form-kicker { display: block; font-size: 10px; letter-spacing: 1.4px; color: var(--color-primary); font-weight: 700; margin-bottom: 8px; }
	h2 { font-size: 24px; line-height: 1.22; letter-spacing: -.03em; margin: 0 0 6px; }
	header p { color: var(--color-text-muted); font-size: 12.5px; margin: 0; line-height: 1.55; }
	.sign-in-error { display: flex; align-items: center; gap: 10px; color: var(--color-danger); background: var(--color-danger-soft); padding: 10px 12px; border: 1px solid var(--color-danger); border-radius: 6px; font-size: 12px; margin-bottom: 16px; }
	.field { margin-bottom: 14px; }
	.field label { display: block; font-size: 11.5px; font-weight: 600; margin-bottom: 6px; color: var(--color-ink); }
	.input-wrap { position: relative; display: flex; align-items: center; overflow: clip; border: 1px solid var(--color-border-strong); background: var(--color-soft); border-radius: 10px; transition: border-color var(--dur-short) ease, background var(--dur-short) ease, box-shadow var(--dur-short) ease; }
	.input-wrap > :global(svg) { position: absolute; left: 12px; z-index: 1; pointer-events: none; color: var(--color-text-muted); flex-shrink: 0; }
	.input-wrap:focus-within { border-color: var(--color-primary); background: var(--color-surface); box-shadow: 0 0 0 3px var(--color-action-shadow); }
	.login-page .input-wrap input { flex: 1; min-width: 0; width: 100%; border: 0; border-radius: 9px; padding: 0 12px 0 38px; background: transparent; min-height: 44px; font-size: 13.5px; outline: none; box-shadow: none; }
	.login-page .input-wrap:has(.password-toggle) input { padding-right: 44px; }
	.login-page .input-wrap input:-webkit-autofill, .login-page .input-wrap input:-webkit-autofill:hover { -webkit-box-shadow: 0 0 0 1000px var(--color-soft) inset !important; box-shadow: 0 0 0 1000px var(--color-soft) inset !important; -webkit-text-fill-color: var(--color-ink) !important; caret-color: var(--color-ink); }
	.login-page .input-wrap:focus-within input:-webkit-autofill, .login-page .input-wrap:focus-within input:-webkit-autofill:focus { -webkit-box-shadow: 0 0 0 1000px var(--color-surface) inset !important; box-shadow: 0 0 0 1000px var(--color-surface) inset !important; -webkit-text-fill-color: var(--color-ink) !important; }
	.login-page .password-toggle { position: absolute; right: 0; z-index: 1; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; width: 44px; height: 44px; padding: 0; border: 0; border-radius: 8px; background: transparent; color: var(--color-text-muted); cursor: pointer; box-shadow: none; }
	.login-page .password-toggle:hover:not(:disabled) { color: var(--color-primary); background: var(--color-action-shadow); }
	.login-page .password-toggle:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -4px; }
	.login-page .password-toggle:disabled { cursor: default; opacity: .5; }
	.submit-button { width: 100%; min-height: 46px; margin-top: 4px; border-radius: 10px; font-size: 13.5px; font-weight: 650; display: flex; align-items: center; justify-content: center; gap: 8px; background: var(--color-primary-dark); color: var(--color-inverse); border: none; cursor: pointer; transition: background var(--dur-short) ease, transform var(--dur-short) var(--ease-out), box-shadow var(--dur-short) ease; box-shadow: 0 8px 20px var(--color-action-shadow); }
	.submit-button:hover:not(:disabled) { background: var(--color-primary); transform: translateY(-1px); }
	.submit-button:active:not(:disabled) { transform: translateY(0); }
	.submit-button:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
	.login-help { display: flex; justify-content: center; align-items: center; gap: 8px; color: var(--color-text-muted); font-size: 11px; margin: 18px 0 0; text-align: center; }
	@media (max-width: 760px) { .login-page { display: flex; flex-direction: column; } .login-form-area { padding: 20px 16px 32px; } .auth-topline { margin-bottom: 12px; } .login-card { padding: 22px 20px 20px; } }
	@media (max-width: 760px) and (max-height: 740px) {
		.login-form-area { padding-block: 12px 20px; }
		.login-card { padding: 16px 20px; }
		header { margin-bottom: 14px; }
		.login-help { margin-top: 12px; }
	}
</style>
