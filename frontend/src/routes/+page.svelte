<script lang="ts">
	import { goto } from '$app/navigation';
	import Toast from '$lib/components/Toast.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import AgentSteps from '$lib/components/AgentSteps.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import FileAttachment from '$lib/components/FileAttachment.svelte';
	import {
		answerClarification,
		createClaim,
		listClarifications,
		MAX_RECEIPT_SIZE_BYTES,
		ALLOWED_RECEIPT_TYPES,
		processClaim,
		replaceClaimReceipt
	} from '$lib/api/claims';
	import { showToast } from '$lib/stores/toast.svelte';
	import { shortClaimRef } from '$lib/formatters/claim';
	import { formatClock, formatDate } from '$lib/formatters/date';
	import { formatCurrency, formatConfidence } from '$lib/formatters/currency';
	import { describeReasonCode } from '$lib/formatters/reasonCodes';
	import { createSubmissionKeyManager } from '$lib/claimSubmission';
	import type { AgentStepView } from '$lib/types/ui';
	import type { ClaimStatus, Decision, ProcessClaimResponse } from '$lib/types/claim';

	type ChatAction = {
		label: string;
		kind: 'retry-upload' | 'retry-process' | 'retake' | 'detail';
		href?: string;
	};

	type Message = {
		id: number;
		from: 'agent' | 'user';
		text?: string;
		file?: { name: string; size: number };
		removable?: boolean;
		timestamp?: string;
		typing?: boolean;
		steps?: AgentStepView[];
		stepsTitle?: string;
		claimRef?: string;
		claimId?: string;
		claimStatus?: ClaimStatus;
		decision?: Decision | null;
		decisionPending?: boolean;
		actions?: ChatAction[];
		isError?: boolean;
	};

	let messages = $state<Message[]>([
		{
			id: 1,
			from: 'agent',
			text: 'Halo! 👋 Kirimkan foto nota transaksimu, dan biarkan Tera memproses klaimnya secara otomatis.',
			timestamp: formatClock()
		}
	]);
	let draft = $state('');
	let fileInput: HTMLInputElement | undefined;
	let nextId = 2;
	let messagesEl: HTMLDivElement | undefined;

	// FR-01: file terpilih dipertahankan selama permintaan berjalan
	let selectedFile = $state<File | null>(null);
	let pendingFileMessageId = $state<number | null>(null);
	let submitPhase = $state<'idle' | 'uploading' | 'processing'>('idle');
	let isProcessing = $derived(submitPhase !== 'idle');

	// FR-09: klarifikasi terbuka (dengan id dari backend) + validasi jawaban kosong
	let awaitingClarification = $state<{
		claimId: string;
		clarificationId: string;
		code: string;
		message: string;
	} | null>(null);
	let submittingAnswer = $state(false);
	let composerError = $state<string | null>(null);

	// FR-03: retry proses hanya lewat tombol (bounded, tidak otomatis)
	let retryableClaimId = $state<string | null>(null);
	let pendingSubmissionKey = $state<string | null>(null);
	const submissionKeyManager = createSubmissionKeyManager();

	// FR-03: id klaim lama saat retake receipt agar konteks tidak hilang
	let retakeClaimId = $state<string | null>(null);

	function scrollToBottom() {
		setTimeout(() => {
			if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
		}, 60);
	}

	function updateMessage(id: number, patch: Partial<Message>) {
		messages = messages.map((m) => (m.id === id ? { ...m, ...patch } : m));
	}

	function sleep(ms: number) {
		return new Promise((r) => setTimeout(r, ms));
	}

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;

		// FR-01: tipe dan ukuran divalidasi sebelum upload
		if (!(ALLOWED_RECEIPT_TYPES as readonly string[]).includes(file.type)) {
			showToast('Format file tidak didukung! Harap upload JPG, PNG, atau PDF.');
			return;
		}
		if (file.size > MAX_RECEIPT_SIZE_BYTES) {
			showToast('Ukuran file melebihi batas maksimal 10 MB.');
			return;
		}
		if (submitPhase !== 'idle') return;

		selectedFile = file;
		submissionKeyManager.selectFile(file);
		pendingSubmissionKey = submissionKeyManager.getKey();
		if (pendingFileMessageId != null) {
			updateMessage(pendingFileMessageId, { file: { name: file.name, size: file.size } });
		} else {
			const messageId = nextId++;
			pendingFileMessageId = messageId;
			messages.push({
				id: messageId,
				from: 'user',
				file: { name: file.name, size: file.size },
				removable: true,
				timestamp: formatClock()
			});
		}
		scrollToBottom();
	}

	function removeSelectedFile(messageId: number) {
		if (submitPhase !== 'idle') return;
		messages = messages.filter((m) => m.id !== messageId);
		if (messageId === pendingFileMessageId) {
			selectedFile = null;
			pendingFileMessageId = null;
			submissionKeyManager.clear();
			pendingSubmissionKey = null;
		}
	}

	function openFilePicker() {
		if (isProcessing) return;
		fileInput?.click();
	}

	async function submitClaim() {
		if (!selectedFile || submitPhase !== 'idle') return;
		composerError = null;
		awaitingClarification = null;
		retryableClaimId = null;

		const file = selectedFile;
		const isRetake = retakeClaimId !== null;
		const existingClaimId = retakeClaimId;
		retakeClaimId = null;
		submitPhase = isRetake ? 'processing' : 'uploading';

		const stepsId = nextId++;
		messages.push({
			id: stepsId,
			from: 'agent',
			stepsTitle: isRetake ? 'Mengganti nota...' : 'Mengirim nota...',
			steps: [{ label: isRetake ? 'Mengunggah nota pengganti ke server' : 'Mengunggah nota ke server', status: 'active' }],
			timestamp: formatClock()
		});
		scrollToBottom();

		let claimId: string;
		if (isRetake && existingClaimId) {
			// FR-03: retake melanjutkan klaim yang sama — tidak membuat klaim baru
			claimId = existingClaimId;
			const uploadDetail = `Nota pengganti "${file.name}" diproses ulang untuk klaim ${shortClaimRef(claimId)}.`;
			updateMessage(stepsId, {
				claimRef: shortClaimRef(claimId),
				claimId,
				stepsTitle: 'Memproses ulang nota...',
				steps: [
					{ label: 'Mengunggah nota pengganti ke server', detail: uploadDetail, status: 'done' },
					{ label: 'Membaca nota (OCR)', status: 'active' }
				]
			});
			selectedFile = null;
			if (pendingFileMessageId != null) {
				updateMessage(pendingFileMessageId, { removable: false });
				pendingFileMessageId = null;
			}
			scrollToBottom();
			await sleep(400);
			try {
				const replacement = await replaceClaimReceipt({ claimId, file });
				updateMessage(stepsId, {
					steps: [
						{
							label: 'Mengunggah nota pengganti ke server',
							detail: `Nota "${replacement.receipt.original_filename}" tersimpan pada klaim ${shortClaimRef(claimId)}.`,
							status: 'done'
						},
						{ label: 'Membaca nota (OCR)', status: 'active' }
					]
				});
				await runProcessing(stepsId, claimId, true);
			} catch (error) {
				submitPhase = 'idle';
				const message = error instanceof Error ? error.message : 'Gagal mengunggah nota pengganti.';
				updateMessage(stepsId, {
					steps: [
						{ label: 'Mengunggah nota pengganti ke server', detail: message, status: 'failed' },
						{ label: 'Membaca nota (OCR)', status: 'skipped' }
					]
				});
				messages.push({
					id: nextId++,
					from: 'agent',
					text: `❌ ${message} Klaim lama tetap tersimpan — coba upload ulang.`,
					isError: true,
					timestamp: formatClock()
				});
				scrollToBottom();
			}
			return;
		}

		try {
			// FR-04: idempotency key per-submit mencegah duplikasi klaim saat retry jaringan
			const idempotencyKey = pendingSubmissionKey ?? submissionKeyManager.getKey();
			pendingSubmissionKey = idempotencyKey;
			const response = await createClaim({ file, idempotencyKey });
			claimId = response.claim.id;
			pendingSubmissionKey = null;
			submissionKeyManager.clear();
			const quality = response.receipts[0]?.quality_score;
			const uploadDetail =
				`Klaim ${shortClaimRef(claimId)} diterima. Nota "${response.receipts[0]?.original_filename ?? file.name}" tersimpan.` +
				(quality != null ? ` Skor kualitas: ${formatConfidence(quality)}.` : '');
			updateMessage(stepsId, {
				claimRef: shortClaimRef(claimId),
				claimId,
				stepsTitle: 'Memproses nota...',
				steps: [
					{ label: 'Mengunggah nota ke server', detail: uploadDetail, status: 'done' },
					{ label: 'Membaca nota (OCR)', status: 'active' }
				]
			});
			scrollToBottom();
		} catch (error) {
			submitPhase = 'idle';
			const message = error instanceof Error ? error.message : 'Terjadi kesalahan tak terduga.';
			messages = messages.filter((m) => m.id !== stepsId);
			messages.push({
				id: nextId++,
				from: 'agent',
				text: `❌ ${message} Notamu masih terlampir — coba kirim ulang.`,
				isError: true,
				actions: [{ label: 'Coba upload lagi', kind: 'retry-upload' }],
				timestamp: formatClock()
			});
			scrollToBottom();
			return;
		}

		// FR-01: file sudah diterima backend, chip menjadi riwayat (tidak bisa dihapus)
		selectedFile = null;
		if (pendingFileMessageId != null) {
			updateMessage(pendingFileMessageId, { removable: false });
			pendingFileMessageId = null;
		}

		submitPhase = 'processing';
		await sleep(700);
		await runProcessing(stepsId, claimId);
	}

	/** FR-09: hubungkan permintaan klarifikasi dengan id klarifikasi terbuka. */
	async function attachOpenClarification(
		claimId: string,
		request: { code: string; message: string }
	) {
		try {
			const list = await listClarifications(claimId);
			const open = list.items.find((item) => item.status === 'open');
			if (open) {
				awaitingClarification = {
					claimId,
					clarificationId: open.id,
					code: request.code,
					message: open.question || request.message
				};
			}
		} catch {
			// daftar klarifikasi gagal dimuat — aksi retake tetap menjadi jalur lanjutan
		}
	}

	async function runProcessing(stepsId: number, claimId: string, resume = false) {
		updateMessage(stepsId, {
			steps: [
				{ label: 'Mengunggah nota ke server', status: 'done' },
				{ label: 'Membaca nota (OCR)', status: 'active' }
			]
		});

		let result: ProcessClaimResponse;
		try {
			result = await processClaim(claimId, crypto.randomUUID(), resume);
		} catch (error) {
			submitPhase = 'idle';
			retryableClaimId = claimId;
			const message = error instanceof Error ? error.message : 'Terjadi kesalahan tak terduga.';
			updateMessage(stepsId, {
				steps: [
					{ label: 'Mengunggah nota ke server', status: 'done' },
					{ label: 'Membaca nota (OCR)', detail: message, status: 'failed' },
					{ label: 'Keputusan agent', status: 'skipped', detail: 'Tidak dijalankan karena pembacaan gagal.' }
				]
			});
			messages.push({
				id: nextId++,
				from: 'agent',
				text: `❌ ${message}`,
				isError: true,
				actions: [{ label: 'Coba proses lagi', kind: 'retry-process' }],
				timestamp: formatClock()
			});
			scrollToBottom();
			return;
		}

		const extraction = result.extractions.at(-1);
		const attemptCount = result.attempts.length;
		const clarification = result.clarification;

		const ocrDetail = extraction
			? `Vendor: ${String(extraction.vendor.value)} · Tanggal: ${formatDate(
					String(extraction.receipt_date.value)
				)} · Total: ${formatCurrency(extraction.total.value as number | string, extraction.currency.value as string)} (keyakinan ${formatConfidence(
					extraction.total.confidence
				)})${attemptCount > 1 ? ` · Percobaan ke-${attemptCount}` : ''}`
			: 'Hasil pembacaan tidak tersedia.';

		if (clarification) {
			// FR-03: permintaan retake dari backend dijelaskan apa perbaikannya
			const clarificationInfo = describeReasonCode(clarification.code);
			updateMessage(stepsId, {
				steps: [
					{ label: 'Mengunggah nota ke server', status: 'done' },
					{ label: 'Membaca nota (OCR)', detail: ocrDetail, status: 'warn' },
					{
						label: 'Validasi kualitas bacaan',
						detail: `${clarificationInfo.label}: ${clarification.message}`,
						status: 'warn'
					},
					{ label: 'Keputusan agent', status: 'skipped', detail: 'Ditunda sampai nota yang lebih jelas diterima.' }
				]
			});
			await sleep(600);
			messages.push({
				id: nextId++,
				from: 'agent',
				text: `⚠️ Butuh tindakanmu untuk klaim ${shortClaimRef(claimId)}: ${clarification.message}`,
				claimId,
				actions: [{ label: 'Upload nota yang lebih jelas', kind: 'retake' }],
				timestamp: formatClock()
			});
			awaitingClarification = null;
			await attachOpenClarification(claimId, clarification);
			submitPhase = 'idle';
			scrollToBottom();
			return;
		}

		// FR-08: render keputusan asli dari backend; tanpa keputusan, tampil jujur menunggu
		const status = result.claim.status;
		const decision = result.decision;
		updateMessage(stepsId, {
			claimStatus: status,
			steps: [
				{ label: 'Mengunggah nota ke server', status: 'done' },
				{ label: 'Membaca nota (OCR)', detail: ocrDetail, status: 'done' },
				{ label: 'Validasi kualitas bacaan', detail: 'Semua field terbaca dengan keyakinan memadai.', status: 'done' },
				{
					label: 'Keputusan agent',
					detail: decision
						? 'Keputusan diterbitkan oleh backend.'
						: 'Klaim masuk antrean penilaian. Pantau status di halaman detail.',
					status: 'done'
				}
			],
			decision: decision ?? null,
			decisionPending: !decision
		});
		messages.push({
			id: nextId++,
			from: 'agent',
			text: `📩 Klaim ${shortClaimRef(claimId)} berhasil diajukan.`,
			claimId,
			claimStatus: status,
			timestamp: formatClock()
		});
		submitPhase = 'idle';
		scrollToBottom();

		// FR-01: respons sukses menghasilkan klaim dan mengarahkan ke halaman detail
		setTimeout(() => goto(`/riwayat/${claimId}`), 1400);
	}

	async function retryProcess(claimId: string, actionMessageId: number) {
		if (submitPhase !== 'idle') return;
		submitPhase = 'processing';
		retryableClaimId = null;
		messages = messages.filter((m) => m.id !== actionMessageId);

		const stepsId = nextId++;
		messages.push({
			id: stepsId,
			from: 'agent',
			claimRef: shortClaimRef(claimId),
			claimId,
			stepsTitle: 'Memproses ulang nota...',
			steps: [{ label: 'Membaca nota (OCR)', status: 'active' }],
			timestamp: formatClock()
		});
		scrollToBottom();
		await runProcessing(stepsId, claimId);
	}

	function handleAction(message: Message, action: ChatAction) {
		if (action.kind === 'retry-upload') {
			messages = messages.filter((item) => item.id !== message.id);
			void submitClaim();
		} else if (action.kind === 'retry-process' && message.claimId) {
			retryProcess(message.claimId, message.id);
		} else if (action.kind === 'retake') {
			// FR-03: simpan claimId lama agar retake melanjutkan klaim yg sama
			if (message.claimId) retakeClaimId = message.claimId;
			openFilePicker();
		}
		// kind 'detail' berupa <a>, ditangani browser
	}

	async function sendText() {
		if (submittingAnswer) return;
		const text = draft.trim();
		if (!text) {
			// FR-09: jawaban/pesan kosong ditolak dengan pesan inline
			composerError = awaitingClarification
				? 'Jawaban tidak boleh kosong.'
				: 'Tulis pesan terlebih dahulu.';
			return;
		}
		composerError = null;

		if (!awaitingClarification) {
			messages.push({ id: nextId++, from: 'user', text, timestamp: formatClock() });
			draft = '';
			scrollToBottom();
			return;
		}

		// FR-09: POST jawaban ke backend; kegagalan mempertahankan input
		const clarification = awaitingClarification;
		submittingAnswer = true;
		const userMessageId = nextId++;
		messages.push({ id: userMessageId, from: 'user', text, timestamp: formatClock() });
		scrollToBottom();

		try {
			const response = await answerClarification({
				claimId: clarification.claimId,
				clarificationId: clarification.clarificationId,
				answer: text
			});
			draft = '';
			awaitingClarification = null;
			const resumedRef = shortClaimRef(clarification.claimId);

			if (response.decision) {
				messages.push({
					id: nextId++,
					from: 'agent',
					text: `✅ Jawaban terkirim. Pemrosesan klaim ${resumedRef} dilanjutkan dan backend menerbitkan keputusan.`,
					claimId: clarification.claimId,
					claimStatus: response.claim.status,
					decision: response.decision,
					actions: [{ label: 'Lihat detail klaim →', kind: 'detail', href: `/riwayat/${clarification.claimId}` }],
					timestamp: formatClock()
				});
			} else if (response.clarification) {
				messages.push({
					id: nextId++,
					from: 'agent',
					text: `🔁 Pemrosesan dilanjutkan, namun backend masih meminta perbaikan: ${response.clarification.message}`,
					claimId: clarification.claimId,
					actions: [{ label: 'Upload nota yang lebih jelas', kind: 'retake' }],
					timestamp: formatClock()
				});
				await attachOpenClarification(clarification.claimId, response.clarification);
			} else {
				messages.push({
					id: nextId++,
					from: 'agent',
					text: `✅ Jawaban terkirim untuk klaim ${resumedRef}. Pantau kelanjutannya di halaman detail.`,
					claimId: clarification.claimId,
					claimStatus: response.claim.status,
					actions: [{ label: 'Lihat detail klaim →', kind: 'detail', href: `/riwayat/${clarification.claimId}` }],
					timestamp: formatClock()
				});
			}
		} catch (error) {
			messages = messages.filter((m) => m.id !== userMessageId);
			draft = text;
			composerError = error instanceof Error ? error.message : 'Gagal mengirim jawaban.';
		} finally {
			submittingAnswer = false;
			scrollToBottom();
		}
	}
</script>

<svelte:head>
	<title>Beranda | Tera Expense Agent</title>
	<meta name="description" content="Upload nota dan ajukan klaim reimbursement dengan mudah menggunakan Tera." />
</svelte:head>

<section class="chat-page">
	<Toast />

	<header class="chat-header">
		<div class="header-left">
			<div class="agent-avatar" aria-hidden="true">
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<rect x="3" y="11" width="18" height="10" rx="2"/>
					<circle cx="12" cy="5" r="2"/>
					<path d="M12 7v4"/>
					<circle cx="8.5" cy="15" r="1.5"/>
					<circle cx="15.5" cy="15" r="1.5"/>
				</svg>
			</div>
			<div>
				<h1>Tera AI Agent</h1>
				<span class="status-online">
					<span class="dot" aria-hidden="true"></span> Online · Siap memproses nota
				</span>
			</div>
		</div>
	</header>

	<div class="tip-banner">
		<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
		<span>Upload foto nota BBM, makan, tol, parkir, atau hotel (JPG/PNG/PDF, maks 10 MB).</span>
	</div>

	<div class="messages" aria-live="polite" bind:this={messagesEl}>
		{#each messages as message (message.id)}
			<div class="msg-row {message.from}">
				{#if message.from === 'agent'}
					<div class="avatar agent-mini" aria-hidden="true">AI</div>
				{/if}

				{#if message.typing}
					<div class="bubble agent typing-bubble">
						<span class="dot-1"></span>
						<span class="dot-2"></span>
						<span class="dot-3"></span>
					</div>
				{:else if message.steps}
					<div class="bubble agent steps-host">
						<AgentSteps steps={message.steps} title={message.stepsTitle ?? 'Memproses nota...'} />
						{#if message.claimRef}<span class="claim-id">{message.claimRef}</span>{/if}
						{#if message.decision}
							<DecisionBanner decision={message.decision} />
						{:else if message.decisionPending}
							<DecisionBanner decision={null} waitingNote="Keputusan resmi akan muncul setelah agent selesai menilai. Status saat ini ditampilkan di halaman detail." />
						{/if}
						{#if message.timestamp}<span class="bubble-time">{message.timestamp}</span>{/if}
					</div>
				{:else}
					<div class="bubble {message.from} {message.isError ? 'error-bubble' : ''}">
						{#if message.file}
							<FileAttachment
								fileName={message.file.name}
								sizeBytes={message.file.size}
								removable={message.removable ?? false}
								onremove={() => removeSelectedFile(message.id)}
							/>
						{:else}
							<p>{message.text}</p>
						{/if}
						{#if message.actions?.length}
							<div class="message-actions">
								{#each message.actions as action (action.label)}
									{#if action.kind === 'detail' && action.href}
										<a class="action-btn primary" href={action.href}>{action.label}</a>
									{:else}
										<button type="button" class="action-btn {action.kind === 'retry-process' ? '' : 'primary'}" onclick={() => handleAction(message, action)} disabled={isProcessing}>
											{action.label}
										</button>
									{/if}
								{/each}
							</div>
						{/if}
						{#if message.claimStatus}
							<div class="status-line">
								<StatusBadge status={message.claimStatus} size="sm" />
							</div>
						{/if}
						{#if message.timestamp}
							<span class="bubble-time">{message.timestamp}</span>
						{/if}
					</div>
				{/if}

				{#if message.from === 'user'}
					<div class="avatar user-mini" aria-hidden="true">S</div>
				{/if}
			</div>
		{/each}
	</div>

	{#if composerError}
		<p class="composer-error" role="alert">{composerError}</p>
	{/if}

	<form
		class="composer"
		onsubmit={(event) => {
			event.preventDefault();
			sendText();
		}}
	>
		<input
			bind:this={fileInput}
			type="file"
			accept="image/jpeg,image/png,application/pdf"
			onchange={onFileChange}
			hidden
			id="file-upload"
		/>
		<button type="button" class="upload-btn" onclick={openFilePicker} id="btn-upload-nota" title="Upload nota" disabled={isProcessing} aria-label={selectedFile ? `Ganti nota terpilih: ${selectedFile.name}` : 'Upload nota'}>
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="17 8 12 3 7 8"/>
				<line x1="12" y1="3" x2="12" y2="15"/>
			</svg>
			<span>{selectedFile ? 'Ganti Nota' : 'Upload Nota'}</span>
		</button>
		<input
			class="text-input"
			type="text"
			placeholder={submittingAnswer
				? 'Mengirim jawaban...'
				: awaitingClarification
					? 'Tulis jawaban klarifikasi...'
					: 'Tulis pesan atau tanyakan sesuatu...'}
			bind:value={draft}
			id="chat-text-input"
			aria-label="Pesan"
			aria-invalid={composerError ? 'true' : undefined}
			disabled={submittingAnswer}
		/>
		<button type="submit" class="send-btn" id="btn-kirim-pesan" disabled={submittingAnswer}>
			<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<line x1="22" y1="2" x2="11" y2="13"/>
				<polygon points="22 2 15 22 11 13 2 9 22 2"/>
			</svg>
			<span>Kirim</span>
		</button>
	</form>
</section>

<style>
	.chat-page {
		display: flex;
		flex-direction: column;
		height: calc(100dvh - 3.5rem);
		max-width: 800px;
	}

	/* Header */
	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		background: rgba(255, 255, 255, 0.75);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		margin-bottom: 0.75rem;
		box-shadow: var(--shadow-md);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.85rem;
	}

	.agent-avatar {
		width: 44px;
		height: 44px;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		box-shadow: 0 2px 12px rgba(26, 107, 92, 0.3);
		flex-shrink: 0;
	}

	.chat-header h1 {
		font-size: 1rem;
		font-weight: 700;
		margin: 0 0 0.1rem;
		color: var(--color-text);
	}

	.status-online {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}

	.dot {
		width: 7px;
		height: 7px;
		background: #22c55e;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.55; transform: scale(0.8); }
	}

	/* Tip */
	.tip-banner {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.6rem 1rem;
		background: linear-gradient(135deg, rgba(26, 107, 92, 0.07) 0%, rgba(46, 204, 168, 0.05) 100%);
		border: 1px solid rgba(26, 107, 92, 0.12);
		border-radius: var(--radius-sm);
		font-size: 0.77rem;
		color: var(--color-primary);
		margin-bottom: 0.75rem;
		font-weight: 500;
	}

	.tip-banner svg { flex-shrink: 0; }

	/* Messages */
	.messages {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		overflow-y: auto;
		padding: 0.25rem 0;
		scroll-behavior: smooth;
	}

	.messages::-webkit-scrollbar { width: 4px; }
	.messages::-webkit-scrollbar-track { background: transparent; }
	.messages::-webkit-scrollbar-thumb {
		background: rgba(26, 107, 92, 0.18);
		border-radius: 4px;
	}

	.msg-row {
		display: flex;
		align-items: flex-end;
		gap: 0.5rem;
		animation: fadeSlide 0.22s ease-out;
	}

	.msg-row.user { justify-content: flex-end; }
	.msg-row.agent { justify-content: flex-start; }

	@keyframes fadeSlide {
		from { opacity: 0; transform: translateY(10px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		font-size: 0.62rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.agent-mini {
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		color: white;
	}

	.user-mini {
		background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary) 100%);
		color: white;
	}

	.bubble {
		max-width: 72%;
		padding: 0.75rem 1rem;
		border-radius: var(--radius-md);
		line-height: 1.55;
		font-size: 0.875rem;
	}

	.bubble p { margin: 0; }

	.bubble.agent {
		background: rgba(255, 255, 255, 0.85);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border: 1px solid var(--color-border);
		color: var(--color-text);
		border-bottom-left-radius: 4px;
		box-shadow: 0 2px 10px rgba(26, 107, 92, 0.07);
	}

	.bubble.user {
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		color: white;
		border-bottom-right-radius: 4px;
		box-shadow: 0 2px 12px rgba(26, 107, 92, 0.25);
	}

	.bubble.error-bubble {
		background: #fef2f2;
		border: 1px solid #f87171;
		color: #b91c1c;
	}

	.steps-host { max-width: 88%; }

	.claim-id {
		display: inline-block;
		margin-top: 0.5rem;
		font-size: 0.68rem;
		font-weight: 600;
		color: var(--color-text-muted);
		background: rgba(26, 107, 92, 0.08);
		padding: 0.15rem 0.5rem;
		border-radius: 20px;
		font-family: monospace;
	}

	.message-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.7rem;
	}

	.action-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.5rem 0.9rem;
		border-radius: var(--radius-sm);
		border: 1.5px solid var(--color-border);
		background: rgba(255, 255, 255, 0.9);
		color: var(--color-primary);
		font: inherit;
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
		text-decoration: none;
		transition: all var(--transition);
	}

	.action-btn:hover:not(:disabled) {
		border-color: var(--color-primary);
		transform: translateY(-1px);
	}

	.action-btn.primary {
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border-color: transparent;
		color: white;
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.25);
	}

	.action-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.action-btn:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	.status-line {
		margin-top: 0.6rem;
	}

	.bubble-time {
		display: block;
		font-size: 0.65rem;
		margin-top: 0.35rem;
		opacity: 0.5;
		text-align: right;
	}

	.bubble.user .bubble-time { color: rgba(255,255,255,0.85); }
	.bubble.agent .bubble-time { color: var(--color-text-muted); }

	/* Composer */
	.composer {
		display: flex;
		gap: 0.5rem;
		padding-top: 0.85rem;
		border-top: 1px solid var(--color-border);
		margin-top: 0.5rem;
	}

	.composer-error {
		margin: 0.4rem 0 0;
		font-size: 0.75rem;
		font-weight: 600;
		color: #b91c1c;
	}

	.upload-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.65rem 1rem;
		background: rgba(255, 255, 255, 0.85);
		backdrop-filter: blur(10px);
		border: 1.5px solid var(--color-border);
		border-radius: var(--radius-sm);
		color: var(--color-primary);
		font: inherit;
		font-size: 0.82rem;
		font-weight: 600;
		cursor: pointer;
		transition: all var(--transition);
		white-space: nowrap;
	}

	.upload-btn:hover:not(:disabled) {
		background: rgba(26, 107, 92, 0.07);
		border-color: var(--color-primary);
		transform: translateY(-1px);
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.12);
	}

	.text-input {
		flex: 1;
		padding: 0.65rem 1rem;
		background: rgba(255, 255, 255, 0.85);
		backdrop-filter: blur(10px);
		border: 1.5px solid var(--color-border);
		border-radius: var(--radius-sm);
		font: inherit;
		font-size: 0.875rem;
		color: var(--color-text);
		transition: all var(--transition);
		outline: none;
	}

	.text-input::placeholder { color: rgba(74, 123, 115, 0.55); }

	.text-input:focus {
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgba(26, 107, 92, 0.1);
		background: rgba(255, 255, 255, 0.98);
	}

	.text-input[aria-invalid='true'] {
		border-color: #f87171;
	}

	.send-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.65rem 1.1rem;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
		border: none;
		border-radius: var(--radius-sm);
		color: white;
		font: inherit;
		font-size: 0.82rem;
		font-weight: 600;
		cursor: pointer;
		transition: all var(--transition);
		box-shadow: 0 2px 8px rgba(26, 107, 92, 0.3);
		white-space: nowrap;
	}

	.send-btn:hover {
		background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary) 100%);
		transform: translateY(-1px);
		box-shadow: 0 4px 14px rgba(26, 107, 92, 0.38);
	}

	.send-btn:active { transform: translateY(0); }

	@media (max-width: 680px) {
		.chat-page { height: calc(100dvh - 9rem); }
		.upload-btn span, .send-btn span { display: none; }
		.upload-btn, .send-btn { padding: 0.65rem 0.85rem; }
	}

	/* ─── Typing Dots ─── */
	.typing-bubble {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 0.8rem 1.1rem;
		min-width: 56px;
	}

	.typing-bubble span {
		width: 7px;
		height: 7px;
		background: var(--color-text-muted);
		border-radius: 50%;
		display: inline-block;
		animation: typingBounce 1.2s infinite ease-in-out;
	}

	.dot-1 { animation-delay: 0s; }
	.dot-2 { animation-delay: 0.2s; }
	.dot-3 { animation-delay: 0.4s; }

	@keyframes typingBounce {
		0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
		30% { transform: translateY(-6px); opacity: 1; }
	}
</style>
