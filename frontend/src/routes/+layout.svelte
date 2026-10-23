

<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import AdminAccount from '$lib/components/AdminAccount.svelte';
	import { setAuthDemoMode } from '$lib/clerk';
	import '$lib/styles.css';
	import '$lib/tokens.css';
	import '$lib/workspace.css';
	let { children, data } = $props();
	untrack(() => setAuthDemoMode(data.demoMode));
	$effect(() => { setAuthDemoMode(data.demoMode); });
	let menuOpen = $state(false);
	let menuButton = $state<HTMLButtonElement>();
	function closeMenu(event: KeyboardEvent) {
		if (event.key === 'Escape' && menuOpen) {
			menuOpen = false;
			menuButton?.focus();
		}
	}
	const isLanding = $derived(['/', '/login', '/sso-callback'].includes(page.url.pathname));
	const menu = $derived(data.financeWorkspace ? [
		{ href: '/reviews', label: 'Antrean review' },
		{ href: '/dashboard', label: 'Ringkasan' },
		{ href: '/admin/claims', label: 'Semua klaim' },
		{ href: '/reports', label: 'Laporan' },
		{ href: '/admin/policies', label: 'Kebijakan' },
		{ href: '/notifikasi', label: 'Notifikasi' }
	] : [
		{ href: '/pengajuan', label: 'Pengajuan baru' },
		{ href: '/riwayat', label: 'Klaim saya' },
		{ href: '/notifikasi', label: 'Notifikasi' },
		...(!data.user ? [{ href: '/login', label: 'Masuk' }] : [])
	]);
	const currentPage = $derived(menu.find((item) => page.url.pathname.startsWith(item.href))?.label ?? (page.url.pathname === '/dashboard' ? 'Ringkasan klaim saya' : 'Detail klaim'));
</script>
<svelte:window onkeydown={closeMenu} />
<svelte:head><link rel="icon" type="image/webp" href="/logo.webp" /><meta name="theme-color" content="#0f766e" /></svelte:head>
<a class="skip-link" href="#main-content">Lewati ke konten</a>
{#if isLanding}
	{@render children()}
{:else}
<div class="app-shell">
	<aside class="sidebar">
		<div class="workspace-brand-row">
			<a href="/" class="brand" aria-label="Tera, beranda"><img src="/logo.webp" alt="" width="36" height="36" /><strong>Tera</strong></a>
			<button bind:this={menuButton} type="button" class="mobile-menu secondary" aria-expanded={menuOpen} aria-controls="workspace-nav" onclick={() => (menuOpen = !menuOpen)}>{menuOpen ? 'Tutup menu' : 'Menu'}</button>
		</div>
			<div class="workspace-identity"><span>{data.financeWorkspace ? 'ADMIN · FINANCE / REVIEWER' : 'KARYAWAN'}</span><strong>{data.financeWorkspace ? 'Meja pemeriksaan' : 'Ruang pengajuan'}</strong><p>{data.financeWorkspace ? 'Tangani pengecualian. Telusuri setiap keputusan.' : 'Kirim nota. Pantau hasil. Lengkapi jika diminta.'}</p></div>
			<nav id="workspace-nav" class:open={menuOpen} aria-label="Menu utama">
			{#each menu as item}
				<a href={item.href} data-sveltekit-reload={item.href === '/pengajuan'} onclick={() => (menuOpen = false)} aria-current={page.url.pathname.startsWith(item.href) ? 'page' : undefined} class:active={page.url.pathname.startsWith(item.href)}>
					<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
							{#if item.href === '/dashboard'}<rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
							{:else if item.href === '/pengajuan'}<path d="M12 5v14M5 12h14" />
						{:else if item.href === '/riwayat'}<rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h4" />
						{:else if item.href === '/reviews'}<path d="m8 12 3 3 5-6" /><rect x="3" y="3" width="18" height="18" rx="3" />
						{:else if item.href === '/notifikasi'}<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
						{:else if item.href === '/admin/policies'}<path d="M5 3h14v18H5zM9 8h6M9 12h6M9 16h4" />
						{:else}<path d="M5 20V10M12 20V4M19 20v-7" />{/if}
					</svg>
					{item.label}
				</a>
			{/each}
		</nav>
		<div class="workspace-return">
			{#if data.demoMode}<span class="workspace-mode">Mode demo</span>{:else if data.user}<AdminAccount />{:else}<a href="/login">Masuk ke akun</a>{/if}
			<a href="/">Tentang Tera <span aria-hidden="true">↗</span></a>
		</div>
	</aside>
	<main id="main-content" class="content" tabindex="-1">
			<div class="topbar"><span>{data.financeWorkspace ? 'Panel admin' : 'Ruang karyawan'} <span aria-hidden="true">/</span> <strong>{currentPage}</strong></span><div class="workspace-mobile-account">{#if data.demoMode}Mode demo{:else if data.user}<AdminAccount />{:else}<a href="/login">Masuk</a>{/if}</div></div>
			{#if data.admin}<div class="workspace-switch"><div><strong>{data.demoMode ? 'Coba dua ruang kerja' : 'Ruang kerja aktif'}</strong><span>{data.demoMode ? 'Karyawan mengajukan nota. Admin/finance menangani kasus yang perlu review. Data demo bersifat sementara.' : 'Akun ini memiliki akses finance dan dapat membuka ruang pengajuan pribadi.'}</span></div><div class="workspace-options" aria-label="Pilih ruang kerja"><a href="/pengajuan" aria-current={!data.financeWorkspace ? 'true' : undefined}>{data.demoMode ? 'Demo Karyawan' : 'Karyawan'}</a><a href="/reviews" aria-current={data.financeWorkspace ? 'true' : undefined}>{data.demoMode ? 'Demo Admin' : 'Admin / Finance'}</a></div></div>{/if}
		{@render children()}
	</main>
</div>
{/if}
