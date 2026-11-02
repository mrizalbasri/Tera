<script lang="ts">
	import { onMount } from 'svelte';
	import { getClerk } from '$lib/clerk';
	let label = $state('Akun kerja');
	let busy = $state(false);
	let error = $state('');
	onMount(() => {
		let disposed = false;
		void getClerk().then((clerk) => {
			if (!disposed) label = clerk.user?.fullName || clerk.user?.primaryEmailAddress?.emailAddress || 'Akun kerja';
		}).catch(() => {});
		return () => { disposed = true; };
	});
	async function logout() {
		busy = true;
		error = '';
		try { await (await getClerk()).signOut({ redirectUrl: '/login' }); }
		catch { error = 'Belum berhasil keluar. Coba lagi.'; busy = false; }
	}
</script>

<div class="admin-account"><span>{label}</span><button type="button" class="secondary" onclick={logout} disabled={busy}>{busy ? 'Keluar...' : 'Keluar'}</button>{#if error}<p role="alert">{error}</p>{/if}</div>

<style>
	.admin-account { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: var(--space-3); }
	span { overflow-wrap: anywhere; }
	p { width: 100%; color: var(--color-danger); margin: 0; }
</style>
