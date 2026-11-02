<script lang="ts">
	import { formatFileSize } from '$lib/formatters/currency';

	let {
		fileName,
		sizeBytes,
		removable = false,
		disabled = false,
		onremove
	}: {
		fileName: string;
		sizeBytes?: number;
		removable?: boolean;
		disabled?: boolean;
		onremove?: () => void;
	} = $props();
</script>

<div class="file-attach">
	<div class="file-icon" aria-hidden="true">
		<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
			<polyline points="14 2 14 8 20 8" />
		</svg>
	</div>
	<div class="file-meta">
		<strong>{fileName}</strong>
		{#if sizeBytes != null}
			<span class="file-size">{formatFileSize(sizeBytes)}</span>
		{/if}
	</div>
	{#if removable && onremove}
		<button
			type="button"
			class="remove-btn"
			onclick={onremove}
			{disabled}
			aria-label="Hapus file {fileName}"
			title="Hapus file"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
				<line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
			</svg>
		</button>
	{/if}
</div>

<style>
	.file-attach {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		min-width: 0;
	}

	.file-icon {
		width: 38px;
		height: 38px;
		background: rgba(26, 107, 92, 0.1);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--color-primary);
		flex-shrink: 0;
	}

	.file-meta {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.file-meta strong {
		display: block;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 220px;
	}

	.file-size {
		font-size: 0.72rem;
		color: var(--color-text-muted);
	}

	.remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border-radius: 50%;
		border: 1px solid var(--color-border);
		background: rgba(255, 255, 255, 0.9);
		color: var(--color-text-muted);
		cursor: pointer;
		transition: all var(--transition);
		flex-shrink: 0;
	}

	.remove-btn:hover {
		background: #fef2f2;
		border-color: #f87171;
		color: #b91c1c;
	}

	.remove-btn:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
</style>
