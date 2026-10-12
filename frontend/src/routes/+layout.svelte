<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import '$lib/styles.css';
	let { children } = $props();
	const menu = [
		{ href: '/', label: 'Pengajuan baru', number: '01' },
		{ href: '/riwayat', label: 'Riwayat klaim', number: '02' },
		{ href: '/review', label: 'Review klaim', number: '03' },
		{ href: '/dashboard', label: 'Analytics Dashboard', number: '04' }
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
				<a href={item.href} aria-current={page.url.pathname === item.href ? 'page' : undefined} class:active={page.url.pathname === item.href}><small>{item.number}</small>{item.label}<span aria-hidden="true">↗</span></a>
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
