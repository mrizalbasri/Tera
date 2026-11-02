<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { authFetch, getClerk } from '$lib/clerk';
	import AdminAccount from '$lib/components/AdminAccount.svelte';
	import EmailPasswordSignIn from '$lib/components/EmailPasswordSignIn.svelte';
	import AuthStory from '$lib/components/AuthStory.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { Clerk } from '@clerk/clerk-js';
	let container: HTMLDivElement;
	let clerk = $state.raw<Clerk>();
	let busy = $state(true);
	let error = $state('');
	let pendingAccess = $state(false);
	let managedFlow = $state(false);
	let managedMounted = false;
	let managedKind = $state<'signin' | 'signup'>('signin');
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
			} else {
				const flow = new URL(window.location.href).searchParams.get('flow');
				if (flow === 'signup') await showManagedFlow('signup');
				else if (clerk.session?.currentTask || flow === 'clerk') await showManagedFlow('signin');
			}
		} catch (cause) {
			if (!disposed) error = cause instanceof Error ? cause.message : 'Login belum dapat dimuat. Coba lagi.';
		} finally { if (!disposed) busy = false; }
	}

	function unmountManagedFlow() {
		if (!clerk || !managedMounted) return;
		if (managedKind === 'signup') clerk.unmountSignUp(container);
		else clerk.unmountSignIn(container);
		managedMounted = false;
	}

	const appearance: NonNullable<Parameters<Clerk['mountSignIn']>[1]>['appearance'] = {
		variables: {
			colorPrimary: '#0f766e', colorBackground: '#ffffff', colorForeground: '#102e2b',
			colorMutedForeground: '#596d69', colorInput: '#f7faf9', colorBorder: '#afc6bf',
			fontFamily: '"Plus Jakarta Sans", "Segoe UI", sans-serif', borderRadius: '10px', fontSize: '14px'
		},
		options: { socialButtonsVariant: 'blockButton' },
		elements: {
			rootBox: { width: '100%' },
			cardBox: { width: '100%', boxShadow: 'none', border: '0', borderRadius: '16px' },
			card: { padding: '32px 28px' },
			headerTitle: { fontSize: '28px', letterSpacing: '-0.04em', fontWeight: '700' },
			formButtonPrimary: { minHeight: '48px', backgroundImage: 'none', boxShadow: 'none' },
			socialButtonsBlockButton: { minHeight: '48px', boxShadow: 'none' },
			formFieldInput: { minHeight: '48px' }
		}
	};

	async function showManagedFlow(kind: 'signin' | 'signup' = 'signin') {
		if (!clerk) return;
		unmountManagedFlow();
		managedKind = kind;
		const managedUrl = new URL(window.location.href);
		managedUrl.searchParams.set('flow', kind === 'signup' ? 'signup' : 'clerk');
		replaceState(managedUrl, {});
		managedFlow = true;
		await tick();
		if (disposed) return;
		if (kind === 'signup') clerk.mountSignUp(container, {
			routing: 'hash', signInUrl: '/login', forceRedirectUrl: '/login', appearance
		});
		else clerk.mountSignIn(container, {
			routing: 'hash', signUpUrl: '/login?flow=signup', forceRedirectUrl: '/login',
			signUpForceRedirectUrl: '/login', withSignUp: true, appearance
		});
		managedMounted = true;
	}

	function showPasswordForm() {
		unmountManagedFlow();
		managedKind = 'signin';
		managedFlow = false;
		replaceState('/login', {});
	}

	onMount(() => {
		void initialize();
		return () => { disposed = true; unmountManagedFlow(); };
	});
</script>

<svelte:head><title>{managedKind === 'signup' ? 'Daftar' : 'Masuk'} · Tera</title><meta name="robots" content="noindex" /></svelte:head>

<main id="main-content" class="login-page" tabindex="-1">
	<AuthStory />
	<section class="login-form-area" aria-label="Akses akun Tera">
		<div class="login-content">
			<div class="auth-topline"><a href="/" class="login-back"><Icon name="home" size={16} />Beranda</a><span>AKUN KERJA TERA</span></div>
			<div class="auth-tabs" role="group" aria-label="Masuk atau daftar"><a href="/login" data-sveltekit-reload aria-current={managedKind === 'signin' ? 'page' : undefined}>Masuk</a><a href="/login?flow=signup" data-sveltekit-reload aria-current={managedKind === 'signup' ? 'page' : undefined}>Daftar akun</a></div>
			<div class="auth-panel">
				{#if busy}<div class="login-state" role="status"><Icon name="clock" /><h2>Menyiapkan ruang kerjamu</h2><p>Menghubungkan layanan akun…</p></div>{/if}
				{#if error}<div class="login-state" role="alert"><Icon name="alert" /><h2>Login belum dapat dilanjutkan</h2><p>{error}</p><button onclick={initialize} disabled={busy}><Icon name="refresh" size={18} />Coba lagi</button>{#if clerk?.session}<AdminAccount />{/if}</div>{/if}
				{#if pendingAccess}<div class="login-state"><h2>Akunmu sudah terhubung.</h2><p>Akun ini belum mendapat akses admin. Hubungi pengelola Tera untuk mengaktifkan akses.</p><button onclick={initialize} disabled={busy}>Periksa akses kembali</button><AdminAccount /></div>{/if}
				{#if !busy && !error && !pendingAccess && !managedFlow}<EmailPasswordSignIn onverification={() => showManagedFlow('signin')} />{/if}
				<div bind:this={container} class:concealed={!managedFlow || busy || !!error || pendingAccess}></div>
				{#if managedFlow && managedKind === 'signin' && !busy && !pendingAccess && !clerk?.session}<button class="return-password" onclick={showPasswordForm}>Kembali ke email dan password</button>{/if}
			</div>
			<p class="login-help"><Icon name="shield" size={16} /><span>Akses pemeriksaan dan laporan mengikuti peran akunmu.</span></p>
		</div>
		<noscript>Aktifkan JavaScript untuk login atau mendaftar ke Tera.</noscript>
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
	.auth-tabs { display: flex; gap: 4px; padding: 5px; background: var(--color-soft); border: 1px solid var(--color-border); border-radius: 12px; margin-bottom: 24px; }
	.auth-tabs a { display: flex; justify-content: center; align-items: center; flex: 1; min-height: 44px; text-decoration: none; color: var(--color-text-muted); font-size: 14px; font-weight: 600; border-radius: 8px; transition: background var(--dur-short), color var(--dur-short); }
	.auth-tabs a:hover { color: var(--color-primary-dark); background: var(--color-light); }
	.auth-tabs a[aria-current] { background: var(--color-surface); color: var(--color-ink); box-shadow: var(--shadow-card); }
	.auth-panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 20px; box-shadow: var(--shadow-md); overflow: clip; }
	.login-help { display: flex; justify-content: center; align-items: flex-start; gap: 8px; color: var(--color-text-muted); font-size: 11px; margin: 24px 0 0; text-align: center; }
	.login-help :global(svg) { flex-shrink: 0; margin-top: 2px; }
	.login-state { padding: 40px 28px; }
	.login-state h2 { font-size: 22px; margin: 16px 0 12px; }
	.login-state p { color: var(--color-text-muted); font-size: 14px; }
	.concealed { display: none; }
	.return-password { display: flex; margin: 0 auto 16px; background: transparent; color: var(--color-primary); border: 0; font-size: 12px; white-space: normal; }
	.return-password:hover { background: var(--color-light); }
	@media (max-width: 760px) { .login-page { display: flex; flex-direction: column; } .login-form-area { padding: 24px 20px 40px; } .auth-topline { margin-bottom: 12px; } }
</style>
