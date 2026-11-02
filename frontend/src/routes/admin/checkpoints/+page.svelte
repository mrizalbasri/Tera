<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDateTime } from '$lib/formatters/date';
	import { formatCurrency } from '$lib/formatters/currency';
	import { showToast } from '$lib/stores/toast.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import {
		listCheckpoints,
		getCheckpoint,
		resumeCheckpoint,
		type CheckpointSummary,
		type CheckpointDetail
	} from '$lib/api/operations';

	let checkpoints = $state<CheckpointSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedStage = $state<string>('all');
	let inspectingClaimId = $state<string | null>(null);
	let detail = $state<CheckpointDetail | null>(null);
	let loadingDetail = $state(false);
	let resumingClaimId = $state<string | null>(null);

	const STAGES = [
		{ id: 'all', label: 'Semua Stage' },
		{ id: 'wait_review', label: 'Menunggu Review (wait_review)' },
		{ id: 'wait_clarification', label: 'Menunggu Klarifikasi (wait_clarification)' },
		{ id: 'extract', label: 'Ekstraksi (extract)' },
		{ id: '__end__', label: 'Selesai (__end__)' }
	];

	async function load() {
		loading = true;
		error = null;
		try {
			const stage = selectedStage === 'all' ? undefined : selectedStage;
			checkpoints = await listCheckpoints(stage);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Gagal memuat daftar checkpoint.';
		} finally {
			loading = false;
		}
	}

	async function inspect(claimId: string) {
		inspectingClaimId = claimId;
		loadingDetail = true;
		detail = null;
		try {
			detail = await getCheckpoint(claimId);
		} catch (cause) {
			showToast('Gagal memuat detail checkpoint.', 'error');
		} finally {
			loadingDetail = false;
		}
	}

	async function resume(claimId: string) {
		resumingClaimId = claimId;
		try {
			const res = await resumeCheckpoint(claimId);
			if (res.status === 'resumed') {
				showToast(`Klaim ${shortClaimRef(claimId)} berhasil dilanjutkan (status: ${res.outcome}).`, 'success');
			} else {
				showToast(`Klaim ${shortClaimRef(claimId)}: tidak ada task tertahan.`, 'info');
			}
			await load();
			if (inspectingClaimId === claimId) {
				await inspect(claimId);
			}
		} catch (cause) {
			showToast(cause instanceof Error ? cause.message : 'Gagal melanjutkan klaim.', 'error');
		} finally {
			resumingClaimId = null;
		}
	}

	onMount(load);
</script>

<svelte:head>
	<title>Observabilitas LangGraph Checkpoints · Tera</title>
</svelte:head>

<Toast />

<main class="checkpoints-page">
	<header class="header">
		<div>
			<div class="breadcrumb"><a href="/dashboard">Dashboard</a> / <span>Observabilitas Graph</span></div>
			<h1>Observabilitas LangGraph & Checkpoint</h1>
			<p class="subtitle">
				Inspeksi state persistent graph, titik interrupt/checkpoint LangGraph, dan alur eksekusi per-klaim secara deterministik.
			</p>
		</div>
		<div class="header-actions">
			<button class="btn-refresh" onclick={load} disabled={loading}>
				<Icon name="refresh" size={18} /> Segarkan State
			</button>
		</div>
	</header>

	<!-- Stage Filter Tabs -->
	<div class="filter-bar">
		<label for="stage-filter">Filter Stage Graph:</label>
		<select id="stage-filter" bind:value={selectedStage} onchange={load}>
			{#each STAGES as s}
				<option value={s.id}>{s.label}</option>
			{/each}
		</select>
	</div>

	<!-- Checkpoints Table -->
	<section class="table-container">
		{#if loading}
			<div class="state-box" role="status">
				<Icon name="refresh" size={24} /> Memuat snapshot checkpoint LangGraph...
			</div>
		{:else if error}
			<div class="state-box error" role="alert">
				<p>{error}</p>
				<button class="btn-retry" onclick={load}>Coba Lagi</button>
			</div>
		{:else if checkpoints.length === 0}
			<div class="state-box">
				<Icon name="check" size={32} />
				<p>Tidak ada checkpoint pada stage ini.</p>
			</div>
		{:else}
			<table class="data-table">
				<thead>
					<tr>
						<th>ID Klaim</th>
						<th>Karyawan</th>
						<th>Nominal</th>
						<th>Status Klaim</th>
						<th>Stage Graph</th>
						<th>Node Berikutnya</th>
						<th>Checkpoint Hash</th>
						<th>Aksi</th>
					</tr>
				</thead>
				<tbody>
					{#each checkpoints as cp (cp.claim_id)}
						<tr>
							<td>
								<strong>{shortClaimRef(cp.claim_id)}</strong>
							</td>
							<td>{cp.employee_id}</td>
							<td>{formatCurrency(cp.declared_amount, cp.currency)}</td>
							<td>
								<StatusBadge status={cp.status as any} size="sm" />
							</td>
							<td>
								<span class="stage-tag {cp.stage ?? 'unknown'}">
									{cp.stage ?? 'belum mulai'}
								</span>
							</td>
							<td>
								{#if cp.next_nodes.length}
									<span class="next-nodes">{cp.next_nodes.join(', ')}</span>
								{:else}
									<span class="terminal-tag">Selesai (END)</span>
								{/if}
							</td>
							<td>
								{#if cp.checkpoint_id}
									<code class="cp-hash" title={cp.checkpoint_id}>
										{cp.checkpoint_id.slice(0, 8)}…
									</code>
								{:else}
									<span class="muted">-</span>
								{/if}
							</td>
							<td>
								<div class="action-buttons">
									<button class="btn-inspect" onclick={() => inspect(cp.claim_id)}>
										<Icon name="eye" size={16} /> Inspeksi
									</button>
									{#if cp.stage === 'wait_review' || cp.stage === 'wait_clarification' || cp.status === 'processing'}
										<button
											class="btn-resume"
											onclick={() => resume(cp.claim_id)}
											disabled={resumingClaimId === cp.claim_id}
										>
											<Icon name="refresh" size={16} />
											{resumingClaimId === cp.claim_id ? 'Memproses...' : 'Lanjutkan'}
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>

	<!-- Inspection Modal -->
	{#if inspectingClaimId}
		<div class="modal-backdrop" role="presentation">
			<div class="modal-dialog" role="dialog" aria-modal="true" aria-label="Detail Checkpoint LangGraph">
				<div class="modal-header">
					<div>
						<span class="eyebrow">Observabilitas Graph Checkpoint</span>
						<h3>Klaim {shortClaimRef(inspectingClaimId)}</h3>
					</div>
					<button class="btn-close" aria-label="Tutup" onclick={() => (inspectingClaimId = null)}>
						<Icon name="close" size={20} />
					</button>
				</div>
				<div class="modal-body">
					{#if loadingDetail}
						<div class="state-box">
							<Icon name="refresh" size={24} /> Membaca snapshot graph dan riwayat checkpoint...
						</div>
					{:else if detail}
						<!-- Graph Topology Banner -->
						<div class="topology-box">
							<h4>Topologi StateGraph Klaim</h4>
							<div class="topology-nodes">
								<span class="top-node {detail.history.some(h => h.stage === 'extract') ? 'active' : ''}">extract</span>
								<span class="top-arrow">→</span>
								<span class="top-node {detail.history.some(h => h.stage === 'validate') ? 'active' : ''}">validate</span>
								<span class="top-arrow">→</span>
								<span class="top-node {detail.history.some(h => h.stage === 'evaluate_policy') ? 'active' : ''}">policy</span>
								<span class="top-arrow">→</span>
								<span class="top-node {detail.history.some(h => h.stage === 'detect_duplicates') ? 'active' : ''}">duplicates</span>
								<span class="top-arrow">→</span>
								<span class="top-node {detail.history.some(h => h.stage === 'score_anomaly') ? 'active' : ''}">anomaly (ML)</span>
								<span class="top-arrow">→</span>
								<span class="top-node {detail.history.some(h => h.stage === 'decide') ? 'active' : ''}">decide</span>
								<span class="top-arrow">→</span>
								<span class="top-node checkpoint {detail.stage?.startsWith('wait_') ? 'current' : ''}">
									{detail.stage ?? 'end'}
								</span>
							</div>
						</div>

						<!-- Snapshot State Details -->
						<div class="snapshot-grid">
							<div class="snap-card">
								<span class="snap-label">Status Klaim</span>
								<span class="snap-val"><StatusBadge status={detail.status as any} size="sm" /></span>
							</div>
							<div class="snap-card">
								<span class="snap-label">Stage Saat Ini</span>
								<span class="snap-val stage-tag {detail.stage ?? ''}">{detail.stage ?? 'selesai'}</span>
							</div>
							<div class="snap-card">
								<span class="snap-label">Checkpoint ID</span>
								<span class="snap-val"><code>{detail.checkpoint_id ?? 'None'}</code></span>
							</div>
							<div class="snap-card">
								<span class="snap-label">Node Berikutnya</span>
								<span class="snap-val">{detail.next_nodes.join(', ') || 'END'}</span>
							</div>
						</div>

						<!-- State Values JSON -->
						<div class="values-section">
							<h4>State Channel Values (StateGraph)</h4>
							<pre class="json-code">{JSON.stringify(detail.values, null, 2)}</pre>
						</div>

						<!-- History Timeline -->
						<div class="history-section">
							<h4>Riwayat Snapshot Checkpoint ({detail.history.length} langkah tersimpan)</h4>
							{#if detail.history.length === 0}
								<p class="muted">Belum ada snapshot checkpoint yang tersimpan.</p>
							{:else}
								<ol class="history-list">
									{#each detail.history as h, idx}
										<li class="history-item">
											<div class="history-badge">{detail.history.length - idx}</div>
											<div class="history-content">
												<div class="history-header">
													<strong class="stage-tag {h.stage ?? ''}">{h.stage ?? 'input'}</strong>
													<small class="muted">{h.created_at ? formatDateTime(h.created_at) : '-'}</small>
												</div>
												<div class="history-meta">
													<span>Next: <code>{h.next.join(', ') || 'END'}</code></span>
													<span>Checkpoint: <code>{h.checkpoint_id?.slice(0, 12)}…</code></span>
													{#if h.source}<span>Source: {h.source}</span>{/if}
													{#if h.step != null}<span>Step: #{h.step}</span>{/if}
												</div>
											</div>
										</li>
									{/each}
								</ol>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</main>

<style>
	.checkpoints-page {
		max-width: 1400px;
		margin: 0 auto;
		padding: 2rem 1.5rem;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1.5rem;
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid var(--color-border);
	}

	.breadcrumb {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		margin-bottom: 0.5rem;
	}

	.breadcrumb a {
		color: var(--color-primary-dark);
		text-decoration: none;
	}

	h1 {
		font-size: 1.8rem;
		margin: 0;
		color: var(--color-text-heading);
	}

	.subtitle {
		margin: 0.5rem 0 0;
		color: var(--color-text-muted);
		max-width: 750px;
	}

	.btn-refresh {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
	}

	.filter-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 1.5rem;
	}

	.filter-bar select {
		padding: 6px 12px;
		border-radius: 6px;
		border: 1px solid var(--color-border);
		font-family: inherit;
		background: white;
	}

	.table-container {
		background: white;
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow-x: auto;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		text-align: left;
		font-size: 0.9rem;
	}

	.data-table th, .data-table td {
		padding: 12px 16px;
		border-bottom: 1px solid var(--color-border);
	}

	.data-table th {
		background: #f8fafc;
		font-weight: 600;
		color: #475569;
	}

	.stage-tag {
		display: inline-block;
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 0.8rem;
		font-weight: 600;
		background: #e2e8f0;
		color: #334155;
	}

	.stage-tag.wait_review {
		background: #fef3c7;
		color: #92400e;
		border: 1px solid #fde68a;
	}

	.stage-tag.wait_clarification {
		background: #e0f2fe;
		color: #0369a1;
		border: 1px solid #bae6fd;
	}

	.stage-tag.__end__ {
		background: #ecfdf5;
		color: #065f46;
	}

	.terminal-tag {
		color: #10b981;
		font-weight: 600;
		font-size: 0.85rem;
	}

	.cp-hash {
		font-family: monospace;
		font-size: 0.85rem;
		background: #f1f5f9;
		padding: 2px 4px;
		border-radius: 4px;
	}

	.action-buttons {
		display: flex;
		gap: 8px;
	}

	.btn-inspect, .btn-resume {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		border-radius: 4px;
		font-size: 0.82rem;
		font-weight: 600;
		cursor: pointer;
		border: 1px solid var(--color-border);
		background: white;
	}

	.btn-resume {
		background: #f0fdf4;
		color: #166534;
		border-color: #bbf7d0;
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0,0,0,0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: 1rem;
	}

	.modal-dialog {
		background: white;
		border-radius: 12px;
		max-width: 850px;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--color-border);
	}

	.modal-header h3 {
		margin: 4px 0 0;
	}

	.btn-close {
		background: transparent;
		border: none;
		cursor: pointer;
	}

	.modal-body {
		padding: 1.5rem;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.topology-box {
		padding: 1rem;
		background: #f8fafc;
		border-radius: 8px;
		border: 1px solid #e2e8f0;
	}

	.topology-box h4 {
		margin: 0 0 0.75rem;
		font-size: 0.9rem;
		color: #475569;
	}

	.topology-nodes {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}

	.top-node {
		padding: 4px 10px;
		background: white;
		border: 1px solid #cbd5e1;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 600;
		color: #64748b;
	}

	.top-node.active {
		border-color: #0f766e;
		color: #0f766e;
		background: #f0fdfa;
	}

	.top-node.current {
		border-color: #f59e0b;
		color: #b45309;
		background: #fffbeb;
		box-shadow: 0 0 0 2px #fde68a;
	}

	.top-arrow {
		color: #94a3b8;
		font-weight: 700;
	}

	.snapshot-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 1rem;
	}

	.snap-card {
		padding: 0.75rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: 6px;
		background: #ffffff;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.snap-label {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		font-weight: 600;
	}

	.json-code {
		background: #1e293b;
		color: #f8fafc;
		padding: 1rem;
		border-radius: 6px;
		font-family: monospace;
		font-size: 0.82rem;
		overflow-x: auto;
		max-height: 180px;
	}

	.history-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.history-item {
		display: flex;
		gap: 12px;
		align-items: flex-start;
		padding: 10px 12px;
		background: #f8fafc;
		border-radius: 6px;
		border: 1px solid #e2e8f0;
	}

	.history-badge {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: #0f766e;
		color: white;
		font-size: 0.75rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.history-content {
		flex: 1;
	}

	.history-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 4px;
	}

	.history-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		font-size: 0.8rem;
		color: #64748b;
	}

	.state-box {
		padding: 2.5rem;
		text-align: center;
		color: var(--color-text-muted);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
	}
</style>
