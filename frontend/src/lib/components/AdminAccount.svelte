<script lang="ts">
	import { onMount } from 'svelte';
	import { getSession, logout } from '$lib/auth';
	import Icon from '$lib/components/Icon.svelte';
	let { compact = false }: { compact?: boolean } = $props();
	let name = $state('Akun kerja');
	let role = $state('');
	let busy = $state(false);
	let error = $state('');
	let menu = $state<HTMLDetailsElement>();
	const initial = $derived(name.trim().charAt(0).toUpperCase() || '?');

	onMount(() => {
		let disposed = false;
		void getSession().then((session) => {
			if (!disposed && session) {
				name = session.username;
				role = session.role === 'admin' ? 'Reviewer' : 'Karyawan';
			}
		});
		return () => { disposed = true; };
	});

	function dismiss(event: Event) {
		if (!menu?.open) return;
		if (event instanceof KeyboardEvent ? event.key === 'Escape' : !(event.target instanceof Node && menu.contains(event.target))) menu.open = false;
	}

	async function handleLogout() {
		busy = true;
		error = '';
		try {
			await logout();
		} catch {
			error = 'Belum berhasil keluar. Coba lagi.';
			busy = false;
		}
	}
</script>

<svelte:window onpointerdown={dismiss} onkeydown={dismiss} />

<details class="account" class:compact bind:this={menu}>
	<summary aria-label={compact ? `Akun ${name}` : undefined}>
		<span class="avatar" aria-hidden="true">{initial}</span>
		{#if !compact}<span class="identity"><strong>{name}</strong>{#if role}<small>{role}</small>{/if}</span><Icon name="chevron-down" size={16} />{/if}
	</summary>
	<div class="account-menu">
		{#if compact}<p class="menu-identity"><strong>{name}</strong>{#if role}<small>{role}</small>{/if}</p>{/if}
		<a href="/"><Icon name="home" size={18} />Tentang Tera</a>
		<button type="button" class="logout" onclick={handleLogout} disabled={busy}><Icon name="logout" size={18} />{busy ? 'Keluar…' : 'Keluar'}</button>
		{#if error}<p class="error" role="alert">{error}</p>{/if}
	</div>
</details>

<style>
	.account { position: relative; }
	summary { display: flex; align-items: center; gap: 10px; min-height: 52px; padding: 8px; border-radius: 12px; cursor: pointer; list-style: none; color: var(--color-ink); transition: background var(--dur-short); }
	summary::-webkit-details-marker { display: none; }
	summary:hover, .account[open] summary { background: var(--color-sidebar-hover, var(--color-soft)); }
	summary :global(svg) { color: var(--color-text-muted); transition: transform var(--dur-short); }
	.account[open] summary :global(svg) { transform: rotate(180deg); }
	.avatar { display: grid; place-items: center; flex-shrink: 0; width: 34px; height: 34px; border-radius: 50%; background: var(--color-primary-dark); color: var(--color-inverse); font-size: 13px; font-weight: 700; }
	.identity { flex: 1; min-width: 0; }
	.identity strong, .identity small, .menu-identity strong, .menu-identity small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.identity strong, .menu-identity strong { font-size: 12px; font-weight: 600; }
	.identity small, .menu-identity small { margin-top: 2px; font-size: 11px; color: var(--color-text-muted); }
	@keyframes menu-pop { from { opacity: 0; transform: translate3d(0, 6px, 0) scale(.98); } to { opacity: 1; transform: translate3d(0, 0, 0) scale(1); } }
	.account-menu { position: absolute; z-index: 30; left: 0; right: 0; bottom: calc(100% + 8px); display: grid; gap: 2px; padding: 6px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; box-shadow: 0 12px 32px rgb(0 45 40 / .14); animation: menu-pop 180ms var(--ease-out) both; }
	.compact .account-menu { left: auto; right: 0; bottom: auto; top: calc(100% + 8px); width: 220px; }
	.compact summary { padding: 4px; min-height: 44px; }
	.menu-identity { margin: 0 0 4px; padding: 8px 10px 10px; border-bottom: 1px solid var(--color-border); }
	.account-menu a, .account-menu button { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 44px; padding: 10px; border: 0; border-radius: 8px; background: transparent; color: var(--color-ink); font-size: 13px; font-weight: 500; text-decoration: none; }
	.account-menu a:hover { background: var(--color-soft); color: var(--color-primary-dark); }
	.account-menu .logout { color: var(--color-danger); }
	.account-menu .logout:hover:not(:disabled) { background: var(--color-danger-soft, var(--color-soft)); }
	.error { margin: 4px 10px; color: var(--color-danger); font-size: 12px; }
</style>
