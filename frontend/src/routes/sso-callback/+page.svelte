<script lang="ts">
	import { onMount } from 'svelte';
	import { getClerk } from '$lib/clerk';
	let error = $state('');
	onMount(() => {
		void getClerk().then((clerk) => clerk.handleRedirectCallback({
			signInUrl: '/login?flow=clerk', signUpUrl: '/login?flow=clerk',
			signInForceRedirectUrl: '/login', signUpForceRedirectUrl: '/login'
		})).catch(() => { error = 'Login Google belum dapat diselesaikan. Kembali ke halaman login dan coba lagi.'; });
	});
</script>
<svelte:head><title>Menyelesaikan login · Tera</title><meta name="robots" content="noindex" /></svelte:head>
<main id="main-content" class="callback" tabindex="-1">{#if error}<p role="alert">{error}</p><a href="/login">Kembali ke login</a>{:else}<p role="status">Menyelesaikan login Google...</p>{/if}</main>
<style>.callback { min-height: 100svh; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: var(--space-6); text-align: center; }</style>
