

<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import AdminAccount from '$lib/components/AdminAccount.svelte';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';
	import { setAuthDemoMode } from '$lib/clerk';
	import '$lib/styles.css';
	import '$lib/tokens.css';
	import '$lib/workspace.css';
	let { children, data } = $props();
	untrack(() => setAuthDemoMode(data.demoMode));
	$effect(() => { setAuthDemoMode(data.demoMode); });
	let menuOpen = $state(false);
	let menuButton = $state<HTMLButtonElement>();
	let workspacePicker = $state<HTMLDetailsElement>();
	let workspaceSummary = $state<HTMLElement>();
	function closeMenu(event: KeyboardEvent) {
		if (event.key !== 'Escape') return;
		if (workspacePicker?.open) {
			workspacePicker.open = false;
			workspaceSummary?.focus();
			return;
		}
		if (menuOpen) {
			menuOpen = false;
			menuButton?.focus();
		}
	}
	const isLanding = $derived(['/', '/login', '/register', '/sso-callback'].includes(page.url.pathname));
	const menu = $derived(data.financeWorkspace ? [
		{ href: '/dashboard', label: 'Ringkasan' },
		{ href: '/reviews', label: 'Antrean review' },
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
	const groups = $derived(data.financeWorkspace ? [
		{ label: 'Operasional', items: menu.slice(0, 3) },
		{ label: 'Pengelolaan', items: menu.slice(3) }
	] : [
		{ label: 'Pengajuan', items: menu.filter(item => ['/pengajuan', '/riwayat'].includes(item.href)) },
		{ label: 'Akun', items: menu.filter(item => !['/pengajuan', '/riwayat'].includes(item.href)) }
	]);
	function isCurrent(href: string) { return page.url.pathname === href || page.url.pathname.startsWith(`${href}/`); }
	function closeNavigation() {
		menuOpen = false;
		if (workspacePicker) workspacePicker.open = false;
	}
	const currentPage = $derived(menu.find((item) => isCurrent(item.href))?.label ?? (page.url.pathname === '/dashboard' ? 'Ringkasan klaim saya' : 'Detail klaim'));
	const menuIcons: Record<string, IconName> = {
		'/reviews': 'review', '/dashboard': 'grid', '/admin/claims': 'receipt',
		'/reports': 'chart', '/admin/policies': 'shield', '/notifikasi': 'bell',
		'/pengajuan': 'plus', '/riwayat': 'receipt', '/login': 'user'
	};
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
				<button bind:this={menuButton} type="button" class="mobile-menu secondary" aria-expanded={menuOpen} aria-controls="workspace-navigation" onclick={() => (menuOpen = !menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} />{menuOpen ? 'Tutup menu' : 'Menu'}</button>
		</div>
			<div id="workspace-navigation" class="workspace-navigation" class:open={menuOpen}>
			{#if data.admin}
				<details class="workspace-picker" bind:this={workspacePicker}>
					<summary bind:this={workspaceSummary}><span class="workspace-avatar"><Icon name={data.financeWorkspace ? 'shield' : 'user'} /></span><span class="workspace-name"><small>Ruang kerja</small><strong>{data.financeWorkspace ? 'Admin / Finance' : 'Karyawan'}</strong></span><span class="picker-chevron"><Icon name="chevron-down" size={16} /></span></summary>
					<div class="workspace-picker-options"><a href="/reviews" onclick={closeNavigation} aria-current={data.financeWorkspace ? 'true' : undefined}><Icon name="shield" size={18} />Admin / Finance{#if data.financeWorkspace}<Icon name="check" size={16} />{/if}</a><a href="/pengajuan" data-sveltekit-reload onclick={closeNavigation} aria-current={!data.financeWorkspace ? 'true' : undefined}><Icon name="user" size={18} />Karyawan{#if !data.financeWorkspace}<Icon name="check" size={16} />{/if}</a></div>
				</details>
			{:else}<div class="workspace-member"><span class="workspace-avatar"><Icon name="user" /></span><span class="workspace-name"><small>Ruang kerja</small><strong>Karyawan</strong></span></div>{/if}
			<nav id="workspace-nav" aria-label="Menu utama">
				{#each groups as group (group.label)}
					<div class="nav-group"><p class="nav-group-label">{group.label}</p>
						{#each group.items as item (item.href)}
							<a href={item.href} data-sveltekit-reload={item.href === '/pengajuan'} onclick={closeNavigation} aria-current={isCurrent(item.href) ? 'page' : undefined} class:active={isCurrent(item.href)}><span class="nav-icon"><Icon name={menuIcons[item.href] ?? 'receipt'} size={19} /></span><span class="nav-label">{item.label}</span>{#if isCurrent(item.href)}<span class="nav-current" aria-hidden="true"></span>{/if}</a>
						{/each}
					</div>
				{/each}
			</nav>
		</div>
		<div class="workspace-return">
			{#if data.user && !data.demoMode}<AdminAccount />{:else if !data.user}<a href="/login">Masuk ke akun</a>{/if}
				<a href="/"><Icon name="home" size={18} />Tentang Tera</a>
		</div>
	</aside>
	<main id="main-content" class="content" tabindex="-1">
			<div class="topbar"><span>{data.financeWorkspace ? 'Panel admin' : 'Ruang karyawan'} <span aria-hidden="true">/</span> <strong>{currentPage}</strong></span><div class="topbar-actions"><a class="notification-link" href="/notifikasi" aria-label="Buka notifikasi"><Icon name="bell" /></a><div class="workspace-mobile-account">{#if data.user && !data.demoMode}<AdminAccount />{:else if !data.user}<a href="/login">Masuk</a>{/if}</div></div></div>
		{@render children()}
	</main>
</div>
{/if}
