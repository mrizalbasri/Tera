<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { authFetch, getClerk } from '$lib/clerk';
	import AdminAccount from '$lib/components/AdminAccount.svelte';
	import EmailPasswordSignIn from '$lib/components/EmailPasswordSignIn.svelte';
	import type { Clerk } from '@clerk/clerk-js';
	let container: HTMLDivElement;
	let clerk = $state.raw<Clerk>();
	let busy = $state(true);
	let error = $state('');
	let pendingAccess = $state(false);
	let managedFlow = $state(false);
	let managedMounted = false;
	let disposed = false;

	async function initialize() {
		busy = true;
		error = '';
		pendingAccess = false;
		try {
			clerk = await getClerk();
			if (disposed) return;
			if (clerk.session && !clerk.session.currentTask) {
				const response = await authFetch('/api/auth/session');
				if (!response.ok) throw new Error(response.status === 401 ? 'Sesi tidak valid. Keluar lalu masuk kembali.' : 'Akses akun belum dapat diperiksa. Coba lagi.');
				const session = await response.json();
				window.location.replace(session.role === 'admin' ? '/reviews' : '/pengajuan');
				return;
			} else if (clerk.session?.currentTask || new URL(window.location.href).searchParams.get('flow') === 'clerk') {
				await showManagedFlow();
			}
		} catch (cause) {
			if (!disposed) error = cause instanceof Error ? cause.message : 'Login belum dapat dimuat. Coba lagi.';
		} finally { if (!disposed) busy = false; }
	}

	async function showManagedFlow() {
		if (!clerk) return;
		const managedUrl = new URL(window.location.href);
		managedUrl.searchParams.set('flow', 'clerk');
		replaceState(managedUrl, {});
		managedFlow = true;
		await tick();
		if (disposed) return;
		if (managedMounted) clerk.unmountSignIn(container);
		clerk.mountSignIn(container, {
			routing: 'hash',
			forceRedirectUrl: '/login',
			signUpForceRedirectUrl: '/login',
			withSignUp: true,
			appearance: {
				variables: {
					colorPrimary: '#0f766e', colorBackground: '#ffffff', colorText: '#102e2b',
					colorTextSecondary: '#596d69', fontFamily: '"Plus Jakarta Sans", "Segoe UI", sans-serif', borderRadius: '8px'
				},
				options: { socialButtonsVariant: 'blockButton' },
				elements: {
					rootBox: { width: '100%' },
					cardBox: { width: '100%', boxShadow: 'none', border: '1px solid #dce7e3', borderRadius: '12px' },
					card: { padding: '24px 20px' },
					headerTitle: { fontSize: '24px', letterSpacing: '-0.03em' },
					formButtonPrimary: { minHeight: '44px', backgroundImage: 'none', boxShadow: 'none' },
					socialButtonsBlockButton: { minHeight: '44px', boxShadow: 'none' },
					formFieldInput: { minHeight: '44px' }
				}
			}
		});
		managedMounted = true;
	}

	function showPasswordForm() {
		if (clerk && managedMounted) clerk.unmountSignIn(container);
		managedMounted = false;
		managedFlow = false;
		replaceState('/login', {});
	}

	onMount(() => {
		void initialize();
		return () => { disposed = true; if (clerk && managedMounted) clerk.unmountSignIn(container); };
	});
</script>

<svelte:head><title>Masuk · Tera</title><meta name="robots" content="noindex" /></svelte:head>

<main id="main-content" class="login-page" tabindex="-1">
	<section class="login-story" aria-labelledby="story-title">
		<a class="login-brand" href="/" aria-label="Tera, beranda"><img src="/logo.webp" width="40" height="40" alt="" /><span>Tera</span></a>
		<div class="story-copy"><p class="context">Ruang kerja finance</p><h1 id="story-title">Dari nota,<br />ke keputusan<br />yang jelas.</h1><p>Tinjau pengajuan dan bukti pengeluaran.<br />Catat keputusan dalam satu alur.</p><ol><li><span>01</span> Periksa pengajuan</li><li><span>02</span> Tinjau bukti dan temuan</li><li><span>03</span> Catat keputusan</li></ol></div>
		<p class="story-note">Pengeluaran kerja, lebih tertata.</p>
	</section>
	<section class="login-form-area" aria-label="Login Tera">
		<div class="login-content">
			<p class="login-intro">Gunakan akun kerja untuk masuk ke Tera.</p>
			{#if busy}<p class="login-state" role="status">Menyiapkan login...</p>{/if}
			{#if error}<div class="login-state" role="alert"><h2>Login belum dapat dilanjutkan</h2><p>{error}</p><button onclick={initialize} disabled={busy}>Coba lagi</button>{#if clerk?.session}<AdminAccount />{/if}</div>{/if}
			{#if pendingAccess}<div class="login-state"><h2>Akunmu sudah terhubung.</h2><p>Akun ini belum mendapat akses admin. Hubungi pengelola Tera untuk mengaktifkan akses.</p><button onclick={initialize} disabled={busy}>Periksa akses kembali</button><AdminAccount /></div>{/if}
			{#if !busy && !error && !pendingAccess && !managedFlow}<EmailPasswordSignIn onverification={showManagedFlow} />{/if}
			<div bind:this={container} class:concealed={!managedFlow || busy || !!error || pendingAccess}></div>
			{#if managedFlow && !busy && !pendingAccess && !clerk?.session}<button class="return-password" onclick={showPasswordForm}>Kembali ke email dan password</button>{/if}
			<p class="login-help">Akses review dan laporan hanya untuk admin yang ditunjuk.</p>
			<a class="login-back" href="/">Kembali ke beranda</a>
		</div>
		<noscript>Aktifkan JavaScript untuk login dengan Google atau email melalui Clerk.</noscript>
	</section>
</main>

<style>
	.login-page { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); min-height: 100svh; }
	.login-story { display: flex; flex-direction: column; padding: clamp(32px, 5vw, 72px); background: var(--color-light); border-right: 1px solid var(--color-border); }
	.login-brand { display: inline-flex; align-items: center; align-self: flex-start; gap: var(--space-3); text-decoration: none; color: var(--color-ink); font-weight: 750; font-size: 28px; }
	.story-copy { margin-block: auto; padding-block: var(--space-16); }
	.context { color: var(--color-primary-dark); font-weight: 600; margin: 0 0 var(--space-6); }
	h1 { font-family: var(--font-display); font-size: clamp(36px, 4.5vw, 64px); font-weight: 650; letter-spacing: -.05em; line-height: 1.08; }
	.story-copy > p:not(.context) { color: var(--color-text-muted); margin-top: var(--space-6); }
	ol { padding: 0; margin: var(--space-10) 0 0; list-style: none; max-width: 360px; }
	li { padding-block: var(--space-4); border-top: 1px solid var(--color-border-strong); display: flex; gap: var(--space-5); }
	li span { color: var(--color-primary-dark); font-variant-numeric: tabular-nums; }
	.story-note { margin: 0; color: var(--color-text-muted); font-size: var(--text-xs); }
	.login-form-area { display: flex; align-items: center; justify-content: center; padding: var(--space-12) var(--space-6); background: var(--color-paper); }
	.login-content { width: 100%; max-width: 400px; }
	.login-intro { color: var(--color-text-muted); margin: 0 0 var(--space-5); text-align: center; }
	.login-help { color: var(--color-text-muted); font-size: var(--text-xs); text-align: center; margin: var(--space-6) 0 var(--space-3); }
	.login-back { display: flex; justify-content: center; align-items: center; min-height: 44px; color: var(--color-primary); font-size: var(--text-sm); }
	.login-state { padding: var(--space-6); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
	.login-state h2 { font-size: var(--text-lg); }
	.login-state p { color: var(--color-text-muted); }
	.concealed { display: none; }
	.return-password { display: flex; margin: var(--space-3) auto 0; background: transparent; color: var(--color-primary); border: 0; font-size: var(--text-xs); white-space: normal; }
	.return-password:hover { background: var(--color-light); }
	@media (max-width: 760px) {
		.login-page { display: flex; flex-direction: column; }
		.login-story { background: var(--color-paper); border: 0; padding: var(--space-6); align-items: center; }
		.login-brand { align-self: center; }
		.story-copy, .story-note { display: none; }
		.login-form-area { flex: 1; align-items: flex-start; padding: var(--space-4) var(--space-4) var(--space-8); }
	}
</style>
