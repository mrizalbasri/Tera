<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';

	let { children } = $props();

	const menu = [
		{
			href: '/',
			label: 'Beranda',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`
		},
		{
			href: '/riwayat',
			label: 'Riwayat',
			icon: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
		}
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="app">
	<aside class="sidebar">
		<div class="brand">
			<div class="brand-logo">
				<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M9 14 4 9l5-5"/>
					<path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>
				</svg>
			</div>
			<div class="brand-text">
				<strong>Tera</strong>
				<small>Expense Agent</small>
			</div>
		</div>

		<div class="divider"></div>

		<nav aria-label="Menu utama">
			{#each menu as item (item.href)}
				<a href={item.href} class:active={page.url.pathname === item.href}>
					<span class="nav-icon">{@html item.icon}</span>
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>

		<div class="sidebar-footer">
			<div class="user-avatar">S</div>
			<div class="user-info">
				<span class="user-name">Salesman</span>
				<span class="user-role">Karyawan Lapangan</span>
			</div>
		</div>
	</aside>

	<main class="content">
		{@render children()}
	</main>
</div>

<style>
	/* ─── Design Tokens ─── */
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

	:global(*, *::before, *::after) { box-sizing: border-box; }

	:global(body) {
		margin: 0;
		min-width: 320px;
		background: var(--color-bg-gradient);
		background-attachment: fixed;
		color: var(--color-text);
		font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
		font-size: 14px;
		line-height: 1.6;
		-webkit-font-smoothing: antialiased;
	}

	:global(h1, h2, h3, h4) { font-weight: 700; letter-spacing: -0.02em; }

	.app { display: flex; min-height: 100vh; }

	/* Sidebar */
	.sidebar {
		box-sizing: border-box;
		width: 240px;
		min-height: 100vh;
		padding: 1.25rem 1rem;
		background: rgba(255, 255, 255, 0.82);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		gap: 0;
		box-shadow: 2px 0 20px rgba(26, 107, 92, 0.06);
		position: sticky;
		top: 0;
		height: 100vh;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0.25rem 0.4rem;
		margin-bottom: 0.5rem;
	}

	.brand-logo {
		width: 40px;
		height: 40px;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border-radius: var(--radius-sm);
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		box-shadow: 0 2px 10px rgba(26, 107, 92, 0.3);
		flex-shrink: 0;
	}

	.brand-text {
		display: flex;
		flex-direction: column;
		line-height: 1.2;
	}

	.brand-text strong {
		font-size: 1.15rem;
		font-weight: 800;
		color: var(--color-primary-dark);
		letter-spacing: -0.03em;
	}

	.brand-text small {
		font-size: 0.68rem;
		font-weight: 500;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.divider {
		height: 1px;
		background: var(--color-border);
		margin: 0.75rem 0;
	}

	nav {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		flex: 1;
	}

	nav a {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.65rem 0.8rem;
		border-radius: var(--radius-sm);
		color: var(--color-text-muted);
		text-decoration: none;
		font-weight: 500;
		font-size: 0.875rem;
		transition: all var(--transition);
		position: relative;
	}

	nav a:hover {
		background: rgba(26, 107, 92, 0.07);
		color: var(--color-primary);
	}

	nav a.active {
		background: linear-gradient(135deg, rgba(26, 107, 92, 0.12) 0%, rgba(46, 204, 168, 0.1) 100%);
		color: var(--color-primary);
		font-weight: 600;
	}

	nav a.active::before {
		content: '';
		position: absolute;
		left: 0;
		top: 20%;
		height: 60%;
		width: 3px;
		background: var(--color-primary);
		border-radius: 0 3px 3px 0;
	}

	.nav-icon {
		display: flex;
		align-items: center;
		opacity: 0.75;
	}

	nav a.active .nav-icon,
	nav a:hover .nav-icon { opacity: 1; }

	.sidebar-footer {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0.75rem 0.4rem;
		margin-top: auto;
		border-top: 1px solid var(--color-border);
	}

	.user-avatar {
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
		color: white;
		font-size: 0.8rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.user-info { display: flex; flex-direction: column; line-height: 1.25; }
	.user-name { font-size: 0.8rem; font-weight: 600; color: var(--color-text); }
	.user-role { font-size: 0.7rem; color: var(--color-text-muted); }

	.content { flex: 1; padding: 1.75rem 2rem; min-width: 0; }

	@media (max-width: 680px) {
		.app { flex-direction: column; }
		.sidebar {
			width: 100%;
			height: auto;
			min-height: auto;
			position: static;
			padding: 0.75rem 1rem;
			border-right: none;
			border-bottom: 1px solid var(--color-border);
		}
		.sidebar-footer { display: none; }
		nav { flex-direction: row; flex: none; }
		nav a.active::before { display: none; }
		.content { padding: 1rem; }
	}
</style>