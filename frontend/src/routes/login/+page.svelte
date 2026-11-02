<script lang="ts">
	import { onMount } from 'svelte';
	import { login, getSession } from '$lib/auth';
	import AuthStory from '$lib/components/AuthStory.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let username = $state('');
	let password = $state('');
	let role = $state<'member' | 'admin'>('admin');
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
			const session = await login(username.trim(), password, role);
			window.location.replace(session.role === 'admin' ? '/reviews' : '/pengajuan');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Login gagal. Coba lagi.';
			busy = false;
		}
	}

	async function quickLogin(targetUser: string, targetRole: 'member' | 'admin') {
		if (busy) return;
		username = targetUser;
		role = targetRole;
		busy = true;
		error = '';
		try {
			const session = await login(targetUser, 'demo123', targetRole);
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
						<p>Pilih peran cepat untuk demo atau masukkan akun Anda.</p>
					</header>

					{#if error}
						<div class="sign-in-error" role="alert">
							<Icon name="alert" size={18} />
							<span>{error}</span>
						</div>
					{/if}

					<!-- Persona Quick Login for GTNIC Judges and Reviewers -->
					<div class="persona-section">
						<span class="persona-label">AKSES CEPAT PERAN</span>
						<div class="persona-buttons">
							<button
								type="button"
								class="persona-btn finance"
								onclick={() => quickLogin('finance@tera.id', 'admin')}
								disabled={busy}
							>
								<Icon name="shield" size={18} />
								<div class="btn-text">
									<strong>Reviewer / Finance</strong>
									<small>finance@tera.id · Akses antrean & review</small>
								</div>
							</button>

							<button
								type="button"
								class="persona-btn employee"
								onclick={() => quickLogin('karyawan@tera.id', 'member')}
								disabled={busy}
							>
								<Icon name="user" size={18} />
								<div class="btn-text">
									<strong>Karyawan</strong>
									<small>karyawan@tera.id · Ajukan klaim nota</small>
								</div>
							</button>
						</div>
					</div>

					<div class="divider">
						<span>atau masuk manual</span>
					</div>

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
									type="password"
									autocomplete="current-password"
									bind:value={password}
									disabled={busy}
									placeholder="Password"
								/>
							</div>
						</div>

						<div class="role-selector">
							<label class="role-option">
								<input type="radio" name="role" value="admin" bind:group={role} disabled={busy} />
								<span>Tim Finance / Reviewer</span>
							</label>
							<label class="role-option">
								<input type="radio" name="role" value="member" bind:group={role} disabled={busy} />
								<span>Karyawan</span>
							</label>
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
				<span>Akses pemeriksaan dan persetujuan klaim otomatis terlindungi.</span>
			</p>
		</div>
	</section>
</main>

<style>
	.login-page { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); min-height: 100svh; }
	.login-form-area { display: flex; align-items: center; justify-content: center; padding: 40px clamp(24px, 4vw, 64px); background: var(--color-paper); }
	.login-content { width: 100%; max-width: 440px; }
	.auth-topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
	.auth-topline > span { font-size: 10px; font-weight: 600; letter-spacing: 1.2px; color: var(--color-text-muted); }
	.login-back { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: var(--color-text-muted); font-size: 12px; text-decoration: none; }
	.login-back:hover { color: var(--color-primary); }
	.auth-panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 20px; box-shadow: var(--shadow-md); overflow: clip; }
	.login-card { padding: 32px 28px; }
	header { margin-bottom: 24px; }
	.form-kicker { display: block; font-size: 10px; letter-spacing: 1.2px; color: var(--color-primary); font-weight: 700; margin-bottom: 8px; }
	h2 { font-size: 26px; line-height: 1.25; letter-spacing: -.03em; margin: 0 0 8px; }
	header p { color: var(--color-text-muted); font-size: 13px; margin: 0; line-height: 1.6; }
	.sign-in-error { display: flex; align-items: center; gap: 10px; color: var(--color-danger); background: var(--color-danger-soft); padding: 12px 14px; border-left: 3px solid var(--color-danger); border-radius: 6px; font-size: 13px; margin-bottom: 20px; }
	.persona-section { margin-bottom: 20px; }
	.persona-label { display: block; font-size: 10px; font-weight: 700; letter-spacing: 1px; color: var(--color-text-muted); margin-bottom: 10px; }
	.persona-buttons { display: flex; flex-direction: column; gap: 10px; }
	.persona-btn { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-soft); cursor: pointer; text-align: left; transition: all 0.15s ease; color: var(--color-ink); }
	.persona-btn:hover:not(:disabled) { border-color: var(--color-primary); background: var(--color-light); transform: translateY(-1px); }
	.persona-btn.finance { border-left: 4px solid var(--color-primary); }
	.persona-btn.employee { border-left: 4px solid var(--color-info, #2563eb); }
	.btn-text strong { display: block; font-size: 13px; font-weight: 600; color: var(--color-ink); }
	.btn-text small { display: block; font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }
	.divider { display: flex; align-items: center; gap: 12px; margin-block: 20px; color: var(--color-text-muted); font-size: 12px; }
	.divider::before, .divider::after { content: ''; height: 1px; flex: 1; background: var(--color-border); }
	.field { margin-bottom: 16px; }
	.field label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--color-ink); }
	.input-wrap { display: flex; align-items: center; gap: 10px; padding: 0 14px; border: 1px solid var(--color-border-strong); background: var(--color-soft); border-radius: 8px; transition: border-color 0.15s ease; }
	.input-wrap:focus-within { border-color: var(--color-primary); background: var(--color-surface); outline: 2px solid var(--color-primary); outline-offset: 1px; }
	.input-wrap input { flex: 1; border: 0; background: transparent; min-height: 44px; font-size: 14px; outline: none; }
	.role-selector { display: flex; gap: 16px; margin: 16px 0 24px; padding: 10px 14px; background: var(--color-soft); border-radius: 8px; border: 1px solid var(--color-border); }
	.role-option { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }
	.role-option input { cursor: pointer; accent-color: var(--color-primary); }
	.submit-button { width: 100%; min-height: 48px; border-radius: 8px; font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 10px; background: var(--color-primary); color: var(--color-inverse); border: none; cursor: pointer; transition: background 0.15s ease; }
	.submit-button:hover:not(:disabled) { background: var(--color-primary-dark); }
	.login-help { display: flex; justify-content: center; align-items: center; gap: 8px; color: var(--color-text-muted); font-size: 11px; margin: 24px 0 0; text-align: center; }
	@media (max-width: 760px) { .login-page { display: flex; flex-direction: column; } .login-form-area { padding: 24px 20px 40px; } .auth-topline { margin-bottom: 12px; } }
</style>
