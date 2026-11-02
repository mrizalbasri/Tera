<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { modalFocus } from '$lib/actions/modalFocus';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import { getClaim, getClaimTimeline, listClaims, listClarifications } from '$lib/api/claims';
	import { ApiError } from '$lib/api/client';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatDate, formatDateTime } from '$lib/formatters/date';
	import { formatCurrency, formatConfidence, confidenceLevel, toNumber } from '$lib/formatters/currency';
	import { describeReasonCode } from '$lib/formatters/reasonCodes';
	import {
		describeTimelineStep,
		formatDuration,
		timelineGlyph,
		timelineTone
	} from '$lib/formatters/timeline';
	import type { Claim, ClaimDetailResponse, Clarification, TimelineEntry } from '$lib/types/claim';

	let id = $derived(page.params.id);
	const historyPath = $derived(page.data.financeWorkspace ? '/admin/claims' : '/riwayat');

	let detail = $state<ClaimDetailResponse | null>(null);
	let clarifications = $state<Clarification[]>([]);
	let timeline = $state<TimelineEntry[]>([]);
	let employeeHistory = $state<Claim[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let notFound = $state(false);
	let receiptRotation = $state(0);
	let isReceiptZoomed = $state(false);

	function rotateReceipt() {
		receiptRotation = (receiptRotation + 90) % 360;
	}

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
			const historyResponse = await listClaims(detail.claim.employee_id);
			employeeHistory = historyResponse.items
				.filter((item) => item.id !== detail?.claim.id)
				.sort((a, b) => b.submitted_at.localeCompare(a.submitted_at));
			// FR-15: konteks percakapan hanya dari respons API yang diotorisasi
			const clarificationResponse = await listClarifications(id as string);
			clarifications = clarificationResponse.items;
			// FR-12: urutan kerja agent dari endpoint timeline backend
			const timelineResponse = await getClaimTimeline(id as string);
			timeline = timelineResponse.items;
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
	const receipt = $derived(detail?.receipts.at(-1) ?? null);
	const extraction = $derived(detail?.extractions.at(-1) ?? null);
	const attempts = $derived(detail?.attempts ?? []);
	const validationFindings = $derived(detail?.validation_findings ?? []);
	const policyEvaluations = $derived(detail?.policy_evaluations ?? []);
	const signals = $derived(detail?.signals ?? []);
	// FR-08: keputusan resmi terbaru dari backend (tidak pernah dihitung di klien)
	const decision = $derived(detail?.decisions.at(-1) ?? null);

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
	<title>Detail klaim · Tera</title>
</svelte:head>

<section class="detail-page">
	<div class="page-header">
		<div class="back-link">
			<a href={historyPath}>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<line x1="19" y1="12" x2="5" y2="12"/>
					<polyline points="12 19 5 12 12 5"/>
				</svg>
				{page.data.financeWorkspace ? 'Kembali ke semua klaim' : 'Kembali ke klaim saya'}
			</a>
		</div>
		<div>
			<h1>Detail klaim {claim ? shortClaimRef(claim.id) : ''}</h1>
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
			<p>Klaim dengan referensi "{id}" tidak ditemukan atau tidak dapat diakses oleh akun ini. Buka kembali dari daftar klaim.</p>
			<a href={historyPath} class="primary-btn">Kembali ke daftar klaim</a>
		</div>
	{:else if loadError}
		<div class="state-panel error" role="alert">
			<h3>Gagal memuat detail</h3>
			<p>{loadError}</p>
			<button type="button" class="primary-btn" onclick={load}>Coba lagi</button>
		</div>
	{:else if claim}
		{#if timeline.some((entry) => entry.step_name === 'run.completed' && entry.status === 'failed') && !decision}
			<div class="notice" role="alert"><h2>Pemeriksaan belum selesai</h2><p>Ada kendala pada proses terakhir. Lihat jejak pemeriksaan untuk penyebabnya, lalu coba kembali dari halaman pengelolaan klaim.</p><a class="button secondary" href={`/claims/${claim.id}`}>Kelola klaim</a></div>
		{/if}
		{#if decision}<DecisionBanner {decision} />{/if}
		<div class="detail-grid">
			<!-- Kiri: Bukti Nota -->
			<div class="receipt-panel glass-panel">
				<div class="receipt-panel-header">
					<h3>Bukti Nota</h3>
					{#if receipt}
						<div class="receipt-toolbar">
							{#if receipt.media_type.startsWith('image/')}
							<button type="button" class="btn-tool" onclick={rotateReceipt} title="Putar 90°" aria-label="Putar gambar nota 90 derajat">
								<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
								</svg>
								<span>Putar</span>
							</button>
							<button type="button" class="btn-tool" onclick={() => (isReceiptZoomed = true)} title="Perbesar nota" aria-label="Perbesar gambar nota">
								<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
								</svg>
								<span>Perbesar</span>
							</button>
							{/if}
							<a href="/api/claims/{claim.id}/receipts/{receipt.id}/content" target="_blank" rel="noopener noreferrer" class="btn-tool" title="Buka berkas di tab baru">
								<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
									<polyline points="15 3 21 3 21 9"/>
									<line x1="10" y1="14" x2="21" y2="3"/>
								</svg>
								<span>Unduh / Tab Baru</span>
							</a>
						</div>
					{/if}
				</div>

				{#if receipt}
					<div class="receipt-display-frame">
						{#if receipt.media_type.startsWith('image/')}
							<div class="receipt-img-container" style="transform: rotate({receiptRotation}deg);">
								<button
									type="button"
									class="receipt-zoom-btn"
									onclick={() => (isReceiptZoomed = true)}
									aria-label="Perbesar pratinjau nota"
								>
									<img
										src="/api/claims/{claim.id}/receipts/{receipt.id}/content"
										alt="Bukti nota {receipt.original_filename}"
										class="receipt-active-img"
									/>
								</button>
							</div>
						{:else if receipt.media_type === 'application/pdf'}
							<div class="receipt-pdf-container">
								<iframe
									src="/api/claims/{claim.id}/receipts/{receipt.id}/content"
									title="Pratinjau PDF Nota"
									class="receipt-pdf-frame"
								></iframe>
								<a href="/api/claims/{claim.id}/receipts/{receipt.id}/content" target="_blank" rel="noopener noreferrer" class="primary-btn">
									Buka Dokumen PDF Penuh ↗
								</a>
							</div>
						{:else}
							<div class="receipt-placeholder" aria-hidden="true">
								<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
									<polyline points="14 2 14 8 20 8"/>
								</svg>
								<span>Berkas nota: {receipt.original_filename}</span>
							</div>
						{/if}
					</div>
				{:else}
					<div class="receipt-placeholder" aria-hidden="true">
						<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
							<polyline points="14 2 14 8 20 8"/>
						</svg>
						<span>Pratinjau nota belum tersedia</span>
					</div>
				{/if}
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
								{#each receipt.quality_findings as finding, i (`${finding}-${i}`)}
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
						<h3>Hasil pembacaan nota</h3>
						{#if extraction.provider.startsWith('mock')}<p class="scope-note">Hasil simulasi dari mode mock.</p>{/if}
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
									<p>{describeReasonCode(warning).label}</p>
								{/each}
							</div>
						{/if}
						{#if extraction.provider_degraded}
							<div class="warning-box degraded">
								<p>Hasil dari penyedia cadangan. Klaim ini memerlukan review.</p>
							</div>
						{/if}
						{#if extraction.line_items.length}
							<h4>Rincian Item</h4>
							<ul class="line-items">
								{#each extraction.line_items as item, i (`${item.description}-${i}`)}
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
						<h3>Percobaan pembacaan</h3>
						<div class="attempts-list">
							{#each attempts as attempt, i (`${attempt.attempt}-${attempt.created_at}-${i}`)}
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

				<div class="glass-panel">
					<h3>Validasi dan kebijakan</h3>
					<details open={validationFindings.some((finding) => !finding.passed) || policyEvaluations.some((evaluation) => !evaluation.passed)}>
						<summary>Lihat {validationFindings.length + policyEvaluations.length} hasil pemeriksaan</summary>
					{#if validationFindings.length === 0 && policyEvaluations.length === 0}
						<p class="scope-note">Belum ada hasil pemeriksaan kebijakan yang tercatat.</p>
					{:else}
						<div class="evidence-list">
							{#each validationFindings as finding (`validation-${finding.processing_run_id}-${finding.rule_id}`)}
								<div class="evidence-row {finding.passed ? 'passed' : finding.severity}">
									<div>
										<strong>{finding.rule_id}</strong>
										<p>{finding.explanation}</p>
										<small>
											Nilai aktual: {finding.actual == null ? '-' : String(finding.actual)}
											· Harapan: {finding.expected ?? '-'}
										</small>
									</div>
									<span>{finding.passed ? 'LULUS' : finding.severity.toUpperCase()}</span>
								</div>
							{/each}
							{#each policyEvaluations as evaluation (`policy-${evaluation.processing_run_id}-${evaluation.rule_id}`)}
								<div class="evidence-row {evaluation.passed ? 'passed' : evaluation.severity}">
									<div>
										<strong>{evaluation.rule_id}</strong>
										<p>{evaluation.explanation}</p>
										<small>
											Nilai: {evaluation.actual_value == null ? '-' : String(evaluation.actual_value)}
											· Batas: {evaluation.limit == null ? '-' : String(evaluation.limit)}
										</small>
									</div>
									<span>{evaluation.passed ? 'LULUS' : evaluation.severity.toUpperCase()}</span>
								</div>
							{/each}
						</div>
					{/if}
					</details>
				</div>

				<div class="glass-panel">
					<h3>Duplikat dan risiko anomali</h3>
					{#if signals.length === 0}
						<p class="scope-note">Belum ada temuan duplikat atau anomali yang tercatat.</p>
					{:else}
						<div class="evidence-list">
							{#each signals as signal (signal.id)}
								<div class="evidence-row {signal.severity}">
									<div>
										<strong>{signal.signal_type === 'duplicate' ? 'Duplikat' : 'Risiko anomali'} · {signal.severity}</strong>
										<p>{signal.explanation}</p>
										<small>
											{#if signal.score != null}Skor: {formatConfidence(signal.score)} · {/if}
											Confidence: {formatConfidence(signal.confidence)}
										</small>
									</div>
									<span>{signal.severity.toUpperCase()}</span>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				{#if timeline.length}
					<div class="glass-panel">
						<h3>Jejak pemeriksaan</h3>
						<p class="scope-note">Aktivitas tersimpan sesuai urutan proses.</p>
						<details><summary>Lihat {timeline.length} aktivitas</summary>
						<ol class="timeline-list">
							{#each timeline as entry (entry.sequence)}
								{@const tone = timelineTone(entry.status)}
								<li class="timeline-entry">
									<span class="timeline-glyph {tone}" aria-hidden="true">{timelineGlyph(tone)}</span>
									<div class="timeline-body">
										<div class="timeline-head">
											<strong>{describeTimelineStep(entry.step_name).label}</strong>
											<span class="timeline-status {tone}">{entry.status}</span>
										</div>
										<p class="timeline-summary">{entry.summary}</p>
										<div class="timeline-meta">
											<span>#{entry.sequence}</span>
											{#if entry.timestamp}<span>{formatDateTime(entry.timestamp)}</span>{/if}
											{#if formatDuration(entry.duration_ms)}<span>{formatDuration(entry.duration_ms)}</span>{/if}
											{#if entry.error_code}<span class="timeline-error">{describeReasonCode(entry.error_code).label}</span>{/if}
										</div>
									</div>
								</li>
							{/each}
						</ol>
						</details>
					</div>
				{/if}

				{#if clarifications.length}
					<div class="glass-panel">
						<h3>Riwayat klarifikasi</h3>
						<p class="scope-note">Pertanyaan dan jawaban yang tercatat pada klaim ini.</p>
						<ol class="clarification-list">
							{#each clarifications as item (item.id)}
								<li class="clarification-item">
									<div class="clarification-entry agent-entry">
										<span class="entry-author">Agent · {formatDateTime(item.created_at)}</span>
										<p>{item.question}</p>
									</div>
									{#if item.answer}
										<div class="clarification-entry user-entry">
											<span class="entry-author">Karyawan · {formatDateTime(item.answered_at)}</span>
											<p>{item.answer}</p>
										</div>
									{:else if item.status === 'open'}
										<div class="clarification-entry pending-entry">
											<span class="entry-author">Menunggu jawaban</span>
											{#if !page.data.financeWorkspace}<a href={`/claims/${claim.id}/clarification`}>Jawab klarifikasi</a>{:else}<span>Menunggu jawaban karyawan</span>{/if}
										</div>
									{/if}
								</li>
							{/each}
						</ol>
					</div>
				{/if}

				<div class="glass-panel">
					<h3>Klaim lain dari karyawan ini</h3>
					<p class="scope-note">
						Pengajuan sebelumnya sebagai konteks tambahan untuk pemeriksaan.
					</p>
					{#if employeeHistory.length}
						<ul class="history-list">
							{#each employeeHistory as item (item.id)}
								<li class="history-item">
									<a href={`${historyPath}/${item.id}`}>{shortClaimRef(item.id)}</a>
									<span>{formatDateTime(item.submitted_at)}</span>
									<StatusBadge status={item.status} size="sm" />
								</li>
							{/each}
						</ul>
					{:else}
						<p class="scope-note">Belum ada klaim historis lain untuk karyawan ini.</p>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if isReceiptZoomed && receipt?.media_type.startsWith('image/')}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="lightbox-overlay"
			use:modalFocus={{ onclose: () => (isReceiptZoomed = false) }}
			onclick={() => (isReceiptZoomed = false)}
			onkeydown={(e) => { if (e.key === 'Escape') isReceiptZoomed = false; }}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			aria-label="Pratinjau nota diperbesar"
		>
			<div class="lightbox-content" role="presentation" onclick={(e) => e.stopPropagation()}>
				<div class="lightbox-header">
					<strong>{receipt.original_filename}</strong>
					<button type="button" class="btn-close" onclick={() => (isReceiptZoomed = false)} aria-label="Tutup pratinjau">✕</button>
				</div>
				<div class="lightbox-body" style="transform: rotate({receiptRotation}deg);">
					<img src="/api/claims/{claim?.id}/receipts/{receipt.id}/content" alt={receipt.original_filename} />
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

	.receipt-panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.receipt-panel-header h3 {
		margin: 0;
	}

	.receipt-toolbar {
		display: flex;
		gap: 0.35rem;
		align-items: center;
	}

	.btn-tool {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.25rem 0.55rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface);
		color: var(--color-text);
		text-decoration: none;
		cursor: pointer;
		transition: background var(--dur-short) var(--ease-out);
		min-height: 28px;
	}

	.btn-tool:hover {
		background: var(--color-light);
		color: var(--color-primary);
	}

	.receipt-display-frame {
		width: 100%;
		min-height: 260px;
		max-height: 480px;
		overflow: hidden;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--color-soft);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		margin-bottom: 0.75rem;
		position: relative;
	}

	.receipt-img-container {
		max-width: 100%;
		max-height: 480px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: transform var(--dur-short) var(--ease-out);
	}

	.receipt-zoom-btn {
		background: none;
		border: none;
		padding: 0;
		cursor: zoom-in;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.receipt-active-img {
		max-width: 100%;
		max-height: 480px;
		object-fit: contain;
		cursor: zoom-in;
		border-radius: var(--radius-sm);
	}

	.receipt-pdf-container {
		width: 100%;
		height: 380px;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.receipt-pdf-frame {
		width: 100%;
		height: 320px;
		border: none;
		border-radius: var(--radius-sm);
	}

	/* Lightbox Modal */
	.lightbox-overlay {
		position: fixed;
		inset: 0;
		background: rgba(16, 46, 43, 0.85);
		backdrop-filter: blur(8px);
		-webkit-backdrop-filter: blur(8px);
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-4);
	}

	.lightbox-content {
		background: var(--color-surface);
		border-radius: var(--radius-md);
		border: 1px solid var(--color-border);
		max-width: min(850px, 95vw);
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		box-shadow: var(--shadow-md);
	}

	.lightbox-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
		font-size: var(--text-sm);
	}

	.lightbox-body {
		padding: var(--space-4);
		overflow: auto;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--color-soft);
		transition: transform var(--dur-short) var(--ease-out);
	}

	.lightbox-body img {
		max-width: 100%;
		max-height: 75vh;
		object-fit: contain;
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

	.warning-box.degraded {
		background: rgba(239, 68, 68, 0.07);
		border-color: rgba(239, 68, 68, 0.3);
	}

	.warning-box.degraded p {
		color: #b91c1c;
	}

	/* Timeline pemrosesan (FR-12) */
	.timeline-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
	}

	.timeline-entry {
		display: flex;
		gap: 0.7rem;
		padding: 0.55rem 0;
		position: relative;
	}

	.timeline-entry:not(:last-child)::after {
		content: '';
		position: absolute;
		left: 12px;
		top: 34px;
		width: 1px;
		height: calc(100% - 10px);
		background: rgba(26, 107, 92, 0.15);
	}

	.timeline-glyph {
		width: 26px;
		height: 26px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.72rem;
		font-weight: 800;
		flex-shrink: 0;
		position: relative;
		z-index: 1;
	}

	.timeline-glyph.success { background: rgba(34, 197, 94, 0.14); color: #16a34a; }
	.timeline-glyph.danger { background: rgba(239, 68, 68, 0.12); color: #dc2626; }
	.timeline-glyph.warn { background: rgba(245, 158, 11, 0.14); color: #b45309; }
	.timeline-glyph.info { background: rgba(59, 130, 246, 0.12); color: #1d4ed8; }
	.timeline-glyph.neutral { background: rgba(100, 116, 139, 0.1); color: #64748b; }

	.timeline-body {
		flex: 1;
		min-width: 0;
	}

	.timeline-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.timeline-head strong {
		font-size: 0.82rem;
		color: var(--color-text);
	}

	.timeline-status {
		font-size: 0.66rem;
		font-weight: 700;
		padding: 0.1rem 0.5rem;
		border-radius: 20px;
		font-family: monospace;
	}

	.timeline-status.success { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
	.timeline-status.danger { background: rgba(239, 68, 68, 0.1); color: #dc2626; }
	.timeline-status.warn { background: rgba(245, 158, 11, 0.12); color: #b45309; }
	.timeline-status.info { background: rgba(59, 130, 246, 0.1); color: #1d4ed8; }
	.timeline-status.neutral { background: rgba(100, 116, 139, 0.1); color: #64748b; }

	.timeline-summary {
		margin: 0.15rem 0 0;
		font-size: 0.76rem;
		color: var(--color-text-muted);
		line-height: 1.5;
	}

	.timeline-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.8rem;
		margin-top: 0.25rem;
		font-size: 0.68rem;
		color: var(--color-text-muted);
	}

	.timeline-error {
		color: #dc2626;
		font-weight: 600;
	}

	/* Clarification history (FR-15) */
	.scope-note {
		margin: -0.6rem 0 0.9rem;
		font-size: 0.7rem;
		color: var(--color-text-muted);
	}

	.history-list {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.history-item {
		display: grid;
		grid-template-columns: 1fr auto auto;
		align-items: center;
		gap: 0.75rem;
		padding-bottom: 0.6rem;
		border-bottom: 1px dashed rgba(26, 107, 92, 0.15);
		font-size: 0.78rem;
	}

	.history-item:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.history-item a {
		color: var(--color-primary);
		font-weight: 700;
		text-decoration: none;
	}

	.history-item > span {
		color: var(--color-text-muted);
	}

	.evidence-list {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}

	.evidence-row {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.75rem;
		border-radius: var(--radius-sm);
		background: rgba(245, 158, 11, 0.08);
		border-left: 3px solid #d97706;
	}

	.evidence-row.passed {
		background: rgba(34, 197, 94, 0.08);
		border-left-color: #16a34a;
	}

	.evidence-row.blocking {
		background: rgba(239, 68, 68, 0.08);
		border-left-color: #dc2626;
	}

	.evidence-row strong,
	.evidence-row span {
		font-size: 0.75rem;
		font-weight: 700;
	}

	.evidence-row span {
		flex-shrink: 0;
	}

	.evidence-row p,
	.evidence-row small {
		margin: 0.25rem 0 0;
		color: var(--color-text-muted);
		font-size: 0.74rem;
		line-height: 1.4;
	}

	.clarification-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.clarification-item {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		padding-bottom: 0.9rem;
		border-bottom: 1px dashed rgba(26, 107, 92, 0.15);
	}

	.clarification-item:last-child {
		padding-bottom: 0;
		border-bottom: none;
	}

	.clarification-entry {
		border-radius: var(--radius-sm);
		padding: 0.55rem 0.8rem;
		font-size: 0.8rem;
	}

	.clarification-entry p {
		margin: 0.15rem 0 0;
		line-height: 1.5;
	}

	.agent-entry {
		background: rgba(26, 107, 92, 0.06);
		border: 1px solid var(--color-border);
	}

	.user-entry {
		background: rgba(59, 130, 246, 0.07);
		border: 1px solid rgba(59, 130, 246, 0.2);
		margin-left: 1.25rem;
	}

	.pending-entry {
		background: rgba(245, 158, 11, 0.07);
		border: 1px dashed rgba(245, 158, 11, 0.4);
		margin-left: 1.25rem;
		color: #b45309;
	}

	.entry-author {
		display: block;
		font-size: 0.66rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
	}

	@media (max-width: 768px) {
		.detail-page {
			width: 100%;
			min-width: 0;
		}

		.detail-grid {
			grid-template-columns: minmax(0, 1fr);
		}

		.glass-panel {
			padding: 1rem;
			min-width: 0;
		}

		.info-row {
			align-items: flex-start;
			flex-direction: column;
			gap: 0.35rem;
		}

		.info-val,
		.field-value {
			text-align: left;
			justify-content: flex-start;
			max-width: 100%;
		}

		.mono {
			overflow-wrap: anywhere;
		}

		.evidence-row {
			flex-direction: column;
			gap: 0.5rem;
		}

		.timeline-meta {
			flex-wrap: wrap;
		}
	}
</style>
