<script lang="ts">
	import type { AgentStepView } from '$lib/types/ui';

	let { steps, title = 'Memproses nota...' }: { steps: AgentStepView[]; title?: string } = $props();

	/**
	 * FR-12: urutan mengikuti API, status running/succeeded/failed/skipped
	 * dibedakan lewat glyph + teks (bukan warna saja), dan daftar berupa
	 * <ol> agar terbaca layar pembaca.
	 */
</script>

<div class="steps-bubble">
	<div class="steps-header">
		<span class="steps-title">🤖 {title}</span>
	</div>
	<ol class="steps-list">
		{#each steps as step (step.label)}
			<li class="step-item {step.status}" aria-current={step.status === 'active' ? 'step' : undefined}>
				<div class="step-icon-wrap" aria-hidden="true">
					{#if step.status === 'done'}
						<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
					{:else if step.status === 'active'}
						<span class="spin">⟳</span>
					{:else if step.status === 'failed'}
						<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
					{:else if step.status === 'warn'}
						<span class="warn-glyph">!</span>
					{:else if step.status === 'skipped'}
						<span class="skip-glyph">–</span>
					{:else}
						<span class="step-dot"></span>
					{/if}
				</div>
				<div class="step-text">
					<span class="step-label">{step.label}</span>
					{#if step.detail && step.status !== 'pending'}
						<span class="step-detail">{step.detail}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
</div>

<style>
	.steps-bubble {
		padding: 1rem 1.1rem;
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(14px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		border-bottom-left-radius: 4px;
		box-shadow: 0 2px 12px rgba(26, 107, 92, 0.08);
	}

	.steps-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}

	.steps-title {
		font-size: 0.82rem;
		font-weight: 700;
		color: var(--color-text);
	}

	.steps-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
	}

	.step-item {
		display: flex;
		align-items: flex-start;
		gap: 0.65rem;
		padding: 0.5rem 0;
		position: relative;
		opacity: 0.45;
		transition: opacity 0.3s ease;
	}

	.step-item.done,
	.step-item.active,
	.step-item.failed,
	.step-item.warn,
	.step-item.skipped {
		opacity: 1;
	}

	.step-item:not(:last-child)::after {
		content: '';
		position: absolute;
		left: 13px;
		top: 32px;
		width: 1px;
		height: calc(100% - 8px);
		background: var(--color-border);
	}

	.step-item.done:not(:last-child)::after {
		background: var(--color-primary);
		opacity: 0.3;
	}

	.step-icon-wrap {
		width: 26px;
		height: 26px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		flex-shrink: 0;
		background: rgba(26, 107, 92, 0.06);
		border: 1.5px solid var(--color-border);
		transition: all 0.3s ease;
		color: var(--color-text-muted);
	}

	.step-item.done .step-icon-wrap {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: white;
	}

	.step-item.active .step-icon-wrap {
		background: rgba(245, 158, 11, 0.1);
		border-color: #f59e0b;
		color: #d97706;
	}

	.step-item.failed .step-icon-wrap {
		background: rgba(239, 68, 68, 0.1);
		border-color: #ef4444;
		color: #dc2626;
	}

	.step-item.warn .step-icon-wrap {
		background: rgba(245, 158, 11, 0.1);
		border-color: #f59e0b;
		color: #b45309;
		font-weight: 800;
	}

	.step-item.skipped .step-icon-wrap {
		background: rgba(100, 116, 139, 0.08);
		border-style: dashed;
		color: #64748b;
	}

	.step-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--color-border);
	}

	.spin {
		display: inline-block;
		animation: spinAnim 0.8s linear infinite;
		font-size: 0.95rem;
	}

	@keyframes spinAnim {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.step-text {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		padding-top: 0.25rem;
		min-width: 0;
	}

	.step-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.step-detail {
		font-size: 0.72rem;
		color: var(--color-text-muted);
		animation: fadeSlide 0.25s ease-out;
		line-height: 1.5;
	}

	@keyframes fadeSlide {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
