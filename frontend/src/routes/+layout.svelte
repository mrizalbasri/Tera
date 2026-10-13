

<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import '$lib/styles.css';
	let { children } = $props();
	const menu = [
		{ href: '/', label: 'Pengajuan & Chat', number: '01' },
		{ href: '/riwayat', label: 'Riwayat klaim', number: '02' },
		{ href: '/reviews', label: 'Review klaim', number: '03' },
		{ href: '/reports', label: 'Laporan klaim', number: '04' },
		{ href: '/dashboard', label: 'Analytics Dashboard', number: '05' }
	];
</script>
<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<a class="skip-link" href="#main-content">Lewati ke konten</a>
<div class="app-shell">
	<aside class="sidebar">
		<a href="/" class="brand" aria-label="Tera, beranda"><img src="/logo.webp" alt="" /><strong>tera<span>expense companion</span></strong></a>
		<p class="nav-caption">RUANG KERJA</p>
		<nav aria-label="Menu utama">
			{#each menu as item}
				<a href={item.href} aria-current={page.url.pathname === item.href ? 'page' : undefined} class:active={page.url.pathname === item.href || (item.href !== '/' && page.url.pathname.startsWith(item.href))}><small>{item.number}</small>{item.label}<span aria-hidden="true">↗</span></a>
			{/each}
		</nav>
		<div class="sidebar-note"><span aria-hidden="true">✳</span><p>Lebih sedikit administrasi.<br /><strong>Lebih banyak waktu bekerja.</strong></p></div>
		<small class="sidebar-footer">TERA · EXPENSE WORKSPACE</small>
	</aside>
	<main id="main-content" class="content" tabindex="-1">
		<div class="topbar"><span>Catat pengeluaran. Lanjutkan pekerjaan.</span><span class="workspace-tag">Workspace prototipe</span></div>
		{@render children()}
	</main>
</div>

<style>
	:global(:root) {
		--color-primary: #1a6b5c;
		--color-primary-dark: #0f4d42;
		--color-primary-light: #2a8a74;
		--color-accent: #2ecca8;
		--color-bg-gradient: linear-gradient(135deg, #e0f2ee 0%, #d4edea 40%, #e8f4f8 100%);
		--color-surface: rgba(255, 255, 255, 0.75);
		--color-border: rgba(26, 107, 92, 0.12);
		--color-text: #0d2b26;
		--color-text-muted: #4a7b73;
		--shadow-md: 0 4px 20px rgba(26, 107, 92, 0.1);
		--radius-sm: 8px;
		--radius-md: 14px;
		--radius-lg: 20px;
		--transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	}
</style>
