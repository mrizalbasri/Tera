<script lang="ts">
	import { toast } from '$lib/stores/toast.svelte';
</script>

{#if toast.visible}
	<div class="toast {toast.type}" role="status">
		{#if toast.type === 'error'}
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
				<circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
			</svg>
		{:else if toast.type === 'success'}
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
			</svg>
		{:else}
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
				<circle cx="12" cy="12" r="10" /><line x1="12" y1="10" x2="12" y2="16" /><line x1="12" y1="7" x2="12.01" y2="7" />
			</svg>
		{/if}
		<span>{toast.message}</span>
	</div>
{/if}

<style>
	.toast {
		position: fixed;
		top: 1.5rem;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		border-radius: var(--radius-sm);
		font-weight: 600;
		font-size: 0.85rem;
		z-index: 1000;
		box-shadow: var(--shadow-md);
		animation: toastSlide 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}

	.toast.error {
		background: #fef2f2;
		border: 1px solid #f87171;
		color: #b91c1c;
	}

	.toast.success {
		background: #f0fdf4;
		border: 1px solid #4ade80;
		color: #15803d;
	}

	.toast.info {
		background: #eff6ff;
		border: 1px solid #93c5fd;
		color: #1d4ed8;
	}

	@keyframes toastSlide {
		from {
			top: -2rem;
			opacity: 0;
		}
		to {
			top: 1.5rem;
			opacity: 1;
		}
	}
</style>
