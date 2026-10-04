<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
<<<<<<< HEAD

	let { children } = $props();
=======
	import { page } from '$app/state';

	let { children } = $props();

	const menu = [
		{ href: '/', label: 'Beranda' },
		{ href: '/riwayat', label: 'Riwayat' }
	];
>>>>>>> origin/main
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<<<<<<< HEAD
{@render children()}
=======
<div class="app">
	<aside class="sidebar">
		<div class="brand">
			<strong>Tera</strong>
			<small>Pembaca nota otomatis</small>
		</div>

		<nav aria-label="Menu utama">
			{#each menu as item (item.href)}
				<a href={item.href} class:active={page.url.pathname === item.href}>
					{item.label}
				</a>
			{/each}
		</nav>
	</aside>

	<main class="content">
		{@render children()}
	</main>
</div>

<style>
	:global(body) {
		margin: 0;
		min-width: 320px;
		background: #f6f7f2;
		color: #172018;
		font-family:
			Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI',
			sans-serif;
	}

	.app {
		display: flex;
		min-height: 100vh;
	}

	.sidebar {
		box-sizing: border-box;
		width: 230px;
		padding: 1.25rem 1rem;
		background: #ffffff;
		border-right: 1px solid #dfe5dc;
	}

	.brand {
		display: flex;
		flex-direction: column;
		margin-bottom: 1.5rem;
	}

	.brand strong {
		font-size: 1.25rem;
	}

	.brand small {
		color: #5b665c;
	}

	nav {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	nav a {
		padding: 0.65rem 0.8rem;
		border-radius: 8px;
		color: #3a463b;
		text-decoration: none;
	}

	nav a:hover {
		background: #f1f5ef;
	}

	nav a.active {
		background: #eaf2e7;
		color: #36593b;
		font-weight: 600;
	}

	.content {
		flex: 1;
		padding: 1.5rem 2rem;
	}

	@media (max-width: 640px) {
		.app {
			flex-direction: column;
		}

		.sidebar {
			width: auto;
			border-right: none;
			border-bottom: 1px solid #dfe5dc;
		}

		nav {
			flex-direction: row;
		}

		.content {
			padding: 1rem;
		}
	}
</style>
>>>>>>> origin/main
