<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import { getClaim } from '$lib/api/claims';
	import { ApiError } from '$lib/api/client';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDate, formatDateTime } from '$lib/formatters/date';
	import { formatCurrency, formatConfidence, confidenceLevel, toNumber } from '$lib/formatters/currency';
	import { describeReasonCode } from '$lib/formatters/reasonCodes';
	import type { ClaimDetailResponse } from '$lib/types/claim';

	let id = $derived(page.params.id);

	let detail = $state<ClaimDetailResponse | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let notFound = $state(false);

	async function load() {
		loading = true;
		loadError = null;
		notFound = false;
		detail = null;

		// FR-11: id yang tidak berbentuk UUID diperlakukan sebagai tidak ditemukan
		const isUuid =
			/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id ?? '');
		if (!isUuid) {
			notFound = true;
			loading = false;
			return;
		}

		try {
			detail = await getClaim(id as string);
		} catch (error) {
			if (error instanceof ApiError && (error.status === 404 || error.code === 'not_found')) {
				notFound = true;
			} else {
				loadError = error instanceof ApiError ? error.message : 'Terjadi kesalahan tak terduga.';
			}
		} finally {
			loading = false;
		}
	}

	onMount(load);

	const claim = $derived(detail?.claim ?? null);
	const receipt = $derived(detail?.receipts[0] ?? null);
	const extraction = $derived(detail?.extractions.at(-1) ?? null);
	const attempts = $derived(detail?.attempts ?? []);

	const fields = $derived(
		extraction
			? [
					{ label: 'Vendor', value: extraction.vendor.value as number | string, confidence: extraction.vendor.confidence },
					{ label: 'Tanggal Nota', value: extraction.receipt_date.value as number | string, confidence: extraction.receipt_date.confidence, isDate: true },
					{ label: 'Total', value: extraction.total.value as number | string, confidence: extraction.total.confidence, isCurrency: true },
					{ label: 'Kategori', value: extraction.category.value as number | string, confidence: extraction.category.confidence }
				]
			: []
	);
</script>

<svelte:head>
	<title>Detail Klaim | Tera Expense Agent</title>
</svelte:head>

<section class="detail-page">
	<div class="page-header">
		<div class="back-link">
			<a href="/riwayat">
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<line x1="19" y1="12" x2="5" y2="12"/>
					<polyline points="12 19 5 12 12 5"/>
				</svg>
				Kembali ke Riwayat
			</a>
		</div>
		<div>
			<h1>Detail Klaim {claim ? shortClaimRef(claim.id) : ''}</h1>
		</div>
	</div>

	{#if loading}
		<div class="state-panel" role="status">
			<span class="spin" aria-hidden="true">⟳</span> Memuat detail...
		</div>
	{:else if notFound}
		<div class="state-panel" role="status">
			<span class="notfound-glyph" aria-hidden="true">🔍</span>
			<h3>Klaim tidak ditemukan</h3>
			<p>Klaim dengan referensi "{id}" tidak ada atau bukan milikmu. Periksa kembali tautan, atau buka dari halaman riwayat.</p>
			<a href="/riwayat" class="primary-btn">Lihat Riwayat Klaim</a>
		</div>
	{:else if loadError}
		<div class="state-panel error" role="alert">
			<h3>Gagal memuat detail</h3>
			<p>{loadError}</p>
			<button type="button" class="primary-btn" onclick={load}>Coba lagi</button>
		</div>
	{:else if claim}
		<div class="detail-grid">
			<!-- Kiri: Bukti Nota -->
			<div class="receipt-panel glass-panel">
				<h3>Bukti Nota</h3>
				<div class="receipt-placeholder" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
						<polyline points="14 2 14 8 20 8"/>
					</svg>
					<span>Gambar nota tidak ditampilkan oleh API</span>
				</div>
				{#if receipt}
					<div class="receipt-meta">
						<div class="info-row">
							<span class="info-label">Nama file</span>
							<span class="info-val">{receipt.original_filename}</span>
						</div>
						<div class="info-row">
							<span class="info-label">Tipe</span>
							<span class="info-val">{receipt.media_type}</span>
						</div>
						<div class="info-row">
							<span class="info-label">Skor kualitas</span>
							<span class="info-val">{formatConfidence(receipt.quality_score)}</span>
						</div>
						{#if receipt.quality_findings.length}
							<div class="quality-findings">
								{#each receipt.quality_findings as finding (finding)}
									<span class="finding-chip">{describeReasonCode(finding).label}</span>
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Kanan: Info & Log Agent -->
			<div class="info-panel">
				<div class="glass-panel summary-info">
					<div class="info-row">
						<span class="info-label">Status</span>
						<StatusBadge status={claim.status} size="sm" />
					</div>
					<div class="info-row">
						<span class="info-label">Diajukan</span>
						<span class="info-val">{formatDateTime(claim.submitted_at)}</span>
					</div>
					<div class="info-row">
						<span class="info-label">ID Klaim</span>
						<span class="info-val mono">{claim.id}</span>
					</div>
					<div class="info-row total-row">
						<span class="info-label">Nominal</span>
						<span class="info-val amount">{formatCurrency(claim.declared_amount, claim.currency)}</span>
					</div>
				</div>

				{#if extraction}
					<div class="glass-panel">
						<h3>Hasil Ekstraksi (FR-02)</h3>
						<div class="extraction-list">
							{#each fields as item (item.label)}
								{@const level = confidenceLevel(item.confidence)}
								<div class="info-row">
									<span class="info-label">{item.label}</span>
									<span class="info-val field-value">
										{item.isCurrency
											? formatCurrency(item.value)
											: item.isDate
												? formatDate(String(item.value))
												: String(item.value)}
										<span class="confidence-pill {level}">
											<span class="level-glyph" aria-hidden="true">{level === 'high' ? '●' : level === 'medium' ? '◐' : '○'}</span>
											{formatConfidence(item.confidence)}
										</span>
									</span>
								</div>
							{/each}
						</div>
						{#if extraction.warnings.length}
							<div class="warning-box">
								{#each extraction.warnings as warning (warning)}
									<p>⚠️ {describeReasonCode(warning).label}</p>
								{/each}
							</div>
						{/if}
						{#if extraction.line_items.length}
							<h4>Rincian Item</h4>
							<ul class="line-items">
								{#each extraction.line_items as item (item.description)}
									<li>
										<span>{item.description} × {toNumber(item.quantity) ?? item.quantity}</span>
										<strong>{formatCurrency(item.total, extraction.currency.value as string)}</strong>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				{/if}

				{#if attempts.length}
					<div class="glass-panel">
						<h3>Percobaan Ekstraksi (FR-03)</h3>
						<div class="attempts-list">
							{#each attempts as attempt (attempt.attempt)}
								<div class="attempt-row {attempt.error_code ? 'failed' : 'ok'}">
									<span class="attempt-num">Percobaan {attempt.attempt}</span>
									{#if attempt.error_code}
										<span class="attempt-status fail">{describeReasonCode(attempt.error_code).label}</span>
									{:else}
										<span class="attempt-status ok-glyph">Berhasil</span>
									{/if}
									{#if attempt.preprocessing.length}
										<span class="attempt-pre">{attempt.preprocessing.join(', ')}</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<div class="glass-panel agent-log">
					<div class="log-header">
						<div class="agent-avatar-mini" aria-hidden="true">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<rect x="3" y="11" width="18" height="10" rx="2"/>
								<circle cx="12" cy="5" r="2"/>
								<path d="M12 7v4"/>
								<circle cx="8.5" cy="15" r="1.5"/>
								<circle cx="15.5" cy="15" r="1.5"/>
							</svg>
						</div>
						<h3>Keputusan Agent (FR-08)</h3>
					</div>
					<DecisionBanner
						decision={null}
						waitingNote="Backend belum mengirim keputusan untuk klaim ini. Keputusan resmi hanya berasal dari backend dan akan tampil di sini."
					/>
				</div>
			</div>
		</div>
	{/if}
</section>

<style>
	.detail-page {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		max-width: 960px;
	}

	.page-header {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.back-link a {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-primary);
		text-decoration: none;
		transition: opacity var(--transition);
	}
	.back-link a:hover { opacity: 0.7; }

	h1 {
		font-size: 1.5rem;
		font-weight: 800;
		margin: 0;
		color: var(--color-text);
	}

	.state-panel {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		gap: 0.4rem;
		padding: 4rem 2rem;
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		color: var(--color-text-muted);
		font-weight: 500;
	}

	.state-panel.error { border: 1px solid rgba(239, 68, 68, 0.25); }

	.state-panel h3 {
		margin: 0;
		font-size: 1.1rem;
		color: var(--color-text);
	}

	.state-panel p {
		margin: 0 0 0.75rem;
		max-width: 440px;
		line-height: 1.5;
		font-weight: 400;
	}

	.notfound-glyph { font-size: 2rem; }

	.spin {
		display: inline-block;
		animation: spinAnim 0.8s linear infinite;
		font-size: 1.2rem;
		color: var(--color-primary);
	}
	@keyframes spinAnim {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.detail-grid {
		display: grid;
		grid-template-columns: 1fr 1.3fr;
		gap: 1.25rem;
		align-items: start;
	}

	.glass-panel {
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: 0 2px 16px rgba(26, 107, 92, 0.07);
		padding: 1.5rem;
	}

	.glass-panel h3 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		color: var(--color-text);
	}

	.glass-panel h4 {
		margin: 1rem 0 0.5rem;
		font-size: 0.85rem;
		color: var(--color-text);
	}

	/* Kiri: Bukti Nota */
	.receipt-panel {
		display: flex;
		flex-direction: column;
	}

	.receipt-placeholder {
		width: 100%;
		aspect-ratio: 3 / 4;
		border-radius: var(--radius-sm);
		border: 1px dashed var(--color-border);
		background: rgba(26, 107, 92, 0.03);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: var(--color-text-muted);
		font-size: 0.75rem;
		text-align: center;
		padding: 1rem;
		margin-bottom: 0.75rem;
	}

	.receipt-meta {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.quality-findings {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.finding-chip {
		font-size: 0.68rem;
		font-weight: 600;
		color: #b45309;
		background: rgba(245, 158, 11, 0.12);
		padding: 0.2rem 0.55rem;
		border-radius: 20px;
	}

	/* Kanan: Info */
	.info-panel {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.summary-info,
	.extraction-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px dashed rgba(26, 107, 92, 0.15);
	}
	.info-row:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.info-label {
		font-size: 0.8rem;
		color: var(--color-text-muted);
		font-weight: 500;
		flex-shrink: 0;
	}

	.info-val {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		text-align: right;
		word-break: break-word;
	}

	.mono {
		font-family: monospace;
		font-size: 0.72rem;
		color: var(--color-text-muted);
	}

	.total-row {
		padding-top: 0.25rem;
	}
	.amount {
		font-size: 1.1rem;
		color: var(--color-primary);
		font-weight: 800;
	}

	.field-value {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		justify-content: flex-end;
	}

	.confidence-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.68rem;
		font-weight: 700;
		padding: 0.1rem 0.5rem;
		border-radius: 20px;
	}

	.confidence-pill.high { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
	.confidence-pill.medium { background: rgba(245, 158, 11, 0.12); color: #b45309; }
	.confidence-pill.low { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

	.level-glyph { font-size: 0.6rem; }

	.warning-box {
		margin-top: 0.75rem;
		padding: 0.6rem 0.8rem;
		background: rgba(245, 158, 11, 0.08);
		border: 1px solid rgba(245, 158, 11, 0.25);
		border-radius: var(--radius-sm);
	}

	.warning-box p {
		margin: 0;
		font-size: 0.75rem;
		color: #b45309;
		font-weight: 600;
	}

	.line-items {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.line-items li {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		font-size: 0.8rem;
		color: var(--color-text);
	}

	.line-items strong {
		font-weight: 700;
		white-space: nowrap;
	}

	/* Attempts */
	.attempts-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.attempt-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
		padding: 0.55rem 0.75rem;
		border-radius: var(--radius-sm);
		background: rgba(26, 107, 92, 0.04);
		font-size: 0.78rem;
	}

	.attempt-row.failed {
		background: rgba(239, 68, 68, 0.06);
	}

	.attempt-num {
		font-weight: 700;
		color: var(--color-text);
	}

	.attempt-status.ok-glyph { color: #16a34a; font-weight: 600; }
	.attempt-status.fail { color: #dc2626; font-weight: 600; }

	.attempt-pre {
		font-size: 0.7rem;
		color: var(--color-text-muted);
	}

	/* Agent Log */
	.log-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1.25rem;
	}
	.log-header h3 { margin: 0; }

	.agent-avatar-mini {
		width: 28px;
		height: 28px;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.3);
	}

	.primary-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		background: var(--color-primary);
		color: white;
		font: inherit;
		font-size: 0.85rem;
		font-weight: 600;
		text-decoration: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition);
	}

	.primary-btn:hover {
		background: var(--color-primary-light);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(26, 107, 92, 0.2);
	}

	@media (max-width: 768px) {
		.detail-grid { grid-template-columns: 1fr; }
	}
</style>
