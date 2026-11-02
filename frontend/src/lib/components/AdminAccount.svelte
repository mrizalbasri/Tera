<script lang="ts">
	import { onMount } from 'svelte';
	import { getSession, logout } from '$lib/auth';
	let label = $state('Akun kerja');
	let busy = $state(false);
	let error = $state('');

	onMount(() => {
		let disposed = false;
		void getSession().then((session) => {
			if (!disposed && session) {
				label = `${session.username} (${session.role === 'admin' ? 'Reviewer' : 'Karyawan'})`;
			}
		});
		return () => { disposed = true; };
	});

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

<div class="admin-account">
	<span>{label}</span>
	<button type="button" class="secondary" onclick={handleLogout} disabled={busy}>
		{busy ? 'Keluar...' : 'Keluar'}
	</button>
	{#if error}<p role="alert">{error}</p>{/if}
</div>

<style>
	.admin-account { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: var(--space-3); }
	span { overflow-wrap: anywhere; }
	p { width: 100%; color: var(--color-danger); margin: 0; }
</style>
