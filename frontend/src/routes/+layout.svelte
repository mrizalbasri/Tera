

<script lang="ts">
	import { page } from '$app/state';
	import '$lib/styles.css';
	import '$lib/tokens.css';
	import '$lib/workspace.css';
	let { children } = $props();
	let menuOpen = $state(false);
	let menuButton = $state<HTMLButtonElement>();
	function closeMenu(event: KeyboardEvent) {
		if (event.key === 'Escape' && menuOpen) {
			menuOpen = false;
			menuButton?.focus();
		}
	}
	const isLanding = $derived(page.url.pathname === '/');
	const menu = [
		{ href: '/pengajuan', label: 'Ajukan klaim' },
		{ href: '/riwayat', label: 'Riwayat' },
		{ href: '/reviews', label: 'Review' },
		{ href: '/reports', label: 'Laporan' },
		{ href: '/dashboard', label: 'Ringkasan' }
	];
	const currentPage = $derived(menu.find((item) => page.url.pathname.startsWith(item.href))?.label ?? 'Detail klaim');
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
		<nav id="workspace-nav" class:open={menuOpen} aria-label="Menu utama">
			{#each menu as item}
				<a href={item.href} onclick={() => (menuOpen = false)} aria-current={page.url.pathname.startsWith(item.href) ? 'page' : undefined} class:active={page.url.pathname.startsWith(item.href)}>{item.label}</a>
			{/each}
		</nav>
		<div class="workspace-return"><a href="/">Tentang Tera</a><span>Pengeluaran kerja, lebih tertata.</span></div>
	</aside>
	<main id="main-content" class="content" tabindex="-1">
		<div class="topbar"><span>Ruang kerja <span aria-hidden="true">/</span> <strong>{currentPage}</strong></span><span class="prototype-note">Prototipe</span></div>
		{@render children()}
	</main>
</div>
{/if}
