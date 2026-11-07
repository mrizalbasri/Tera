<script lang="ts">
	import Toast from '$lib/components/Toast.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import AgentSteps from '$lib/components/AgentSteps.svelte';
	import DecisionBanner from '$lib/components/DecisionBanner.svelte';
	import FileAttachment from '$lib/components/FileAttachment.svelte';
	import {
		answerClarification,
		createClaim,
		getClaim,
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
		kind: 'retry-upload' | 'retry-replacement' | 'retry-process' | 'retake' | 'detail';
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

	let messages = $state<Message[]>([]);
	let draft = $state('');
	let fileInput: HTMLInputElement | undefined;
	let nextId = 2;
	let messagesEl = $state<HTMLDivElement>();

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
	const hasConversation = $derived(messages.length > 0 || selectedFile !== null || isProcessing || awaitingClarification !== null);
	const activeClaim = $derived([...messages].reverse().find((message) => message.claimId));
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

	let isDragging = $state(false);

	function handleFileSelection(file: File) {
		if (isProcessing || submittingAnswer) return;
		if (!(ALLOWED_RECEIPT_TYPES as readonly string[]).includes(file.type)) {
			showToast('Format file tidak didukung! Harap upload JPG, PNG, atau PDF.');
			return;
		}
		if (file.size === 0) {
			showToast('File kosong. Pilih nota yang berisi foto atau dokumen.');
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

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (file) handleFileSelection(file);
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		if (submitPhase === 'idle') isDragging = true;
	}

	function onDragLeave(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
		const file = event.dataTransfer?.files?.[0];
		if (file) handleFileSelection(file);
	}


	function removeSelectedFile(messageId: number) {
		if (submitPhase !== 'idle') return;
		messages = messages.filter((m) => m.id !== messageId);
		if (messageId === pendingFileMessageId) {
			selectedFile = null;
			pendingFileMessageId = null;
			submissionKeyManager.clear();
			pendingSubmissionKey = null;
			retakeClaimId = null;
		}
	}

	function openFilePicker() {
		if (isProcessing || submittingAnswer) return;
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
			scrollToBottom();
			let receiptCountBefore: number | null = null;
			try {
				receiptCountBefore = (await getClaim(claimId)).receipts.length;
			} catch {
				// The replacement request remains retryable if the preflight check is unavailable.
			}
			await sleep(400);
			try {
				const replacement = await replaceClaimReceipt({ claimId, file });
				selectedFile = null;
				retakeClaimId = null;
				if (pendingFileMessageId != null) {
					updateMessage(pendingFileMessageId, { removable: false });
					pendingFileMessageId = null;
				}
				updateMessage(stepsId, {
					steps: [
						{
							label: 'Mengunggah nota pengganti ke server',
							detail: `Nota "${replacement.receipt.original_filename}" tersimpan pada klaim ${shortClaimRef(claimId)}.`,
							status: 'done'
						},
						{ label: 'Pemeriksaan tersedia di detail klaim', status: 'skipped' }
					]
				});
				await runProcessing(stepsId, claimId);
			} catch (error) {
				submitPhase = 'idle';
				const message = error instanceof Error ? error.message : 'Gagal mengunggah nota pengganti.';
				if (receiptCountBefore !== null) {
					try {
						const refreshed = await getClaim(claimId);
						if (refreshed.receipts.length > receiptCountBefore) {
							selectedFile = null;
							retakeClaimId = null;
							if (pendingFileMessageId != null) {
								updateMessage(pendingFileMessageId, { removable: false });
								pendingFileMessageId = null;
							}
							messages.push({
								id: nextId++,
								from: 'agent',
								text: `✅ Nota pengganti sudah tersimpan pada klaim ${shortClaimRef(claimId)}. Buka detail untuk memulai pemeriksaan.`,
								claimId,
								timestamp: formatClock()
							});
							await runProcessing(stepsId, claimId);
							return;
						}
					} catch {
						// Keep the bounded retry action when the confirmation request also fails.
					}
				}
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
					actions: [{ label: 'Coba upload nota pengganti lagi', kind: 'retry-replacement' }],
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
			messages = messages.map((message) => ({ ...message, actions: message.actions?.filter((action) => action.kind !== 'retry-upload') }));
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
					{ label: 'Pemeriksaan tersedia di detail klaim', status: 'skipped' }
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
		submitPhase = 'processing';
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
				stepsTitle: 'Pembacaan belum selesai',
				steps: [
					{ label: 'Mengunggah nota ke server', status: 'done' },
					{ label: 'Membaca nota (OCR)', detail: message, status: 'failed' },
					{ label: 'Keputusan agent', status: 'skipped', detail: 'Tidak dijalankan karena pembacaan gagal.' }
				]
			});
			messages.push({
				id: nextId++,
				from: 'agent',
				text: `Pembacaan belum selesai. ${message}`,
				claimId,
				isError: true,
				actions: [{ label: 'Coba proses lagi', kind: 'retry-process' }],
				timestamp: formatClock()
			});
			scrollToBottom();
			return;
		}

		messages = messages.map((message) => message.claimId === claimId
			? { ...message, actions: message.actions?.filter((action) => action.kind === 'detail') }
			: message);
		const extraction = result.extractions.at(-1);
		const attemptCount = result.attempts.length;
		const clarification = result.clarification;

		const ocrDetail = extraction
			? `Vendor: ${String(extraction.vendor.value ?? 'Belum terbaca')} · Tanggal: ${extraction.receipt_date.value ? formatDate(String(extraction.receipt_date.value)) : 'Belum terbaca'} · Total: ${formatCurrency(extraction.total.value as number | string, extraction.currency.value as string)} (keyakinan ${formatConfidence(
					extraction.total.confidence
				)})${attemptCount > 1 ? ` · Percobaan ke-${attemptCount}` : ''}`
			: 'Hasil pembacaan tidak tersedia.';

		if (clarification) {
			// FR-03: permintaan retake dari backend dijelaskan apa perbaikannya
			const clarificationInfo = describeReasonCode(clarification.code);
			updateMessage(stepsId, {
				stepsTitle: 'Perlu informasi tambahan',
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
			stepsTitle: 'Pemeriksaan selesai',
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
			text: `📩 Klaim ${shortClaimRef(claimId)} berhasil diajukan dan dinilai oleh agen.`,
			claimId,
			claimStatus: status,
			actions: [{ label: 'Buka Detail & Bukti Klaim →', kind: 'detail', href: `/riwayat/${claimId}` }],
			timestamp: formatClock()
		});
		submitPhase = 'idle';
		scrollToBottom();
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
		} else if (action.kind === 'retry-replacement') {
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
		if (submittingAnswer || isProcessing) return;
		if (selectedFile) {
			await submitClaim();
			return;
		}
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
			messages.push({ id: nextId++, from: 'agent', text: 'Untuk mengajukan klaim, pilih foto atau PDF melalui tombol Upload nota, lalu tekan Kirim nota. Jawaban teks digunakan saat Tera meminta klarifikasi.', timestamp: formatClock() });
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
	<title>Ajukan klaim · Tera</title>
	<meta name="description" content="Upload nota dan ajukan klaim reimbursement dengan mudah menggunakan Tera." />
</svelte:head>

<section class="chat-page">
	<Toast />

	<header class="chat-header">
		<div>
			<h1>Ajukan klaim</h1>
			<p>Kirim nota pengeluaranmu. Tera membantu memeriksa detailnya.</p>
		</div>
		{#if hasConversation}<span class="task-status" role="status">{isProcessing ? 'Memeriksa nota…' : awaitingClarification ? 'Perlu klarifikasi' : selectedFile ? 'Nota siap dikirim' : 'Hasil pemeriksaan'}</span>{/if}
	</header>

	<input bind:this={fileInput} type="file" accept="image/jpeg,image/png,application/pdf" onchange={onFileChange} hidden id="file-upload" />
	<div class="intake-layout">
	<div class="intake-main" class:has-conversation={hasConversation}>

	{#if !hasConversation}
		<div class="intake-start">
			<div class="intake-panel-heading"><h2>Upload nota</h2><span>Satu nota per pengajuan</span></div>
			<button
				type="button"
				class="dropzone-box"
				class:dragging={isDragging}
				ondragover={onDragOver}
				ondragleave={onDragLeave}
				ondrop={onDrop}
				onclick={openFilePicker}
				aria-label="Tarik dan lepas nota ke sini atau klik untuk memilih file"
			>
				<span class="dropzone-icon" aria-hidden="true">
					<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
						<polyline points="17 8 12 3 7 8"/>
						<line x1="12" y1="3" x2="12" y2="15"/>
					</svg>
				</span>
				<span class="dropzone-text">
					<strong>Pilih nota pengeluaran</strong>
					<span>Tarik file ke sini atau klik untuk memilih</span>
					<span>Mendukung foto JPG, PNG, atau dokumen PDF (maks. 10 MB)</span>
				</span>
			</button>
			<p class="intake-note">Setelah diunggah, kamu bisa meninjau hasil dan melengkapi data yang belum terbaca.</p>
		</div>
	{/if}

	{#if hasConversation}
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
									removable={(message.removable ?? false) && !isProcessing && !submittingAnswer}
									onremove={() => removeSelectedFile(message.id)}
								/>
							{:else}
								<p>{message.text}</p>
							{/if}
							{#if message.decision}<DecisionBanner decision={message.decision} />{/if}
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
						<div class="avatar user-mini" aria-hidden="true">K</div>
					{/if}
				</div>
			{/each}
		</div>

		{#if composerError}
			<p id="composer-error" class="composer-error" role="alert">{composerError}</p>
		{/if}

		{#if selectedFile || awaitingClarification}<form
			class="composer"
			onsubmit={(event) => {
				event.preventDefault();
				sendText();
			}}
		>
			{#if selectedFile}<button type="button" class="upload-btn" onclick={openFilePicker} id="btn-upload-nota" title="Ganti nota" disabled={isProcessing || submittingAnswer} aria-label={`Ganti nota terpilih: ${selectedFile.name}`}>
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
					<polyline points="17 8 12 3 7 8"/>
					<line x1="12" y1="3" x2="12" y2="15"/>
				</svg>
				<span>{selectedFile ? 'Ganti Nota' : 'Upload Nota'}</span>
			</button>{/if}
			{#if awaitingClarification && !selectedFile}<input
				class="text-input"
				type="text"
				placeholder={submittingAnswer
					? 'Mengirim jawaban...'
					: awaitingClarification
						? 'Tulis jawaban klarifikasi...'
						: selectedFile ? 'Nota siap dikirim' : 'Pilih nota melalui tombol upload'}
				bind:value={draft}
				id="chat-text-input"
				aria-label="Pesan"
				aria-invalid={composerError ? 'true' : undefined}
				aria-describedby={composerError ? 'composer-error' : undefined}
				disabled={submittingAnswer || isProcessing}
			/>
			{:else}<p class="selection-summary">{selectedFile?.name}<span>Siap diperiksa oleh Tera</span></p>{/if}
			<button type="submit" class="send-btn" id="btn-kirim-pesan" aria-label={selectedFile ? 'Periksa nota' : 'Kirim jawaban klarifikasi'} disabled={submittingAnswer || isProcessing}>
				<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<line x1="22" y1="2" x2="11" y2="13"/>
					<polygon points="22 2 15 22 11 13 2 9 22 2"/>
				</svg>
				<span>{selectedFile ? 'Periksa nota' : 'Kirim jawaban'}</span>
			</button>
		</form>{:else if !isProcessing}
			<div class="next-upload">
				<div class="next-actions">
					<button type="button" class="secondary" onclick={openFilePicker}>Upload nota lain</button>
					<a href="/dashboard">Kembali ke dashboard</a>
				</div>
			</div>
		{/if}
	{/if}
	</div>
	<aside class="intake-guide" aria-label="Panduan pengajuan">
		{#if activeClaim}<section class="claim-context"><span class="guide-label">Pengajuan aktif</span><h2>{shortClaimRef(activeClaim.claimId ?? '')}</h2><p>{isProcessing ? 'Tera sedang membaca dan memeriksa nota.' : awaitingClarification ? 'Lengkapi informasi agar pemeriksaan bisa dilanjutkan.' : 'Lihat bukti dan perkembangan pengajuan.'}</p><a href={`/riwayat/${activeClaim.claimId}`}>Buka detail klaim</a></section>{/if}
		<section class="guide-section"><h2>Siapkan nota yang jelas</h2><ul><li>Nama tempat atau penyedia jasa</li><li>Tanggal transaksi</li><li>Total pembayaran</li></ul><p>BBM, makan, tol, parkir, atau hotel. Gunakan nota asli pengeluaran kerja.</p></section>
		<section class="guide-section workflow-guide"><h2>Setelah nota dikirim</h2><ol><li><strong>Nota dibaca</strong><span>Detail transaksi diambil dari bukti.</span></li><li><strong>Klaim diperiksa</strong><span>Kebijakan dan indikasi duplikat dicocokkan.</span></li><li><strong>Hasil ditampilkan</strong><span>Ikuti status atau lengkapi klarifikasi.</span></li></ol></section>
	</aside>
	</div>
</section>

<style>
	.chat-page {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		width: 100%;
		max-width: 1440px;
		margin-inline: auto;
	}

	.chat-header { display: flex; align-items: start; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; flex-shrink: 0; }
	.chat-header h1 { margin: 0 0 8px; }
	.chat-header p { margin: 0; color: var(--color-text-muted); }
	.task-status { font-size: var(--text-xs); padding: 8px 12px; border-radius: var(--radius-sm); background: var(--color-light); color: var(--color-primary-dark); }
	.intake-start { flex: 1; min-height: 0; padding: 0; }
	.intake-note { max-width: 420px; margin: 16px auto 24px; text-align: center; font-size: var(--text-xs); color: var(--color-text-muted); }

	/* Dropzone Box */
	.dropzone-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 100%;
		min-height: 240px;
		padding: 2rem 1.25rem;
		white-space: normal;
		font-weight: 400;
		margin-bottom: 0.75rem;
		background: var(--color-surface);
		border: 1.5px dashed var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		text-align: center;
		gap: 0.75rem;
		transition: border-color var(--dur-short) var(--ease-out), background-color var(--dur-short) var(--ease-out);
	}

	.dropzone-box:hover, .dropzone-box:focus-visible, .dropzone-box.dragging {
		border-color: var(--color-primary);
		background: var(--color-soft);
	}

	.dropzone-icon {
		display: grid;
		place-items: center;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: var(--color-light);
		color: var(--color-primary);
	}

	.dropzone-text {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.dropzone-text strong {
		font-size: 18px;
		color: var(--color-ink);
	}

	.dropzone-text span {
		font-size: var(--text-xs);
		color: var(--color-text-muted);
	}

	/* Messages */
	.messages {
		flex: 1;
		min-height: 0;
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
		background: var(--color-primary);
		color: white;
	}

	.user-mini {
		background: var(--color-primary-dark);
		color: white;
	}

	.bubble {
		max-width: min(85%, 620px);
		min-width: 0;
		overflow-wrap: anywhere;
		padding: 0.75rem 1rem;
		border-radius: var(--radius-md);
		line-height: 1.55;
		font-size: 0.875rem;
	}

	.bubble p { margin: 0; }

	.bubble.agent {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		color: var(--color-text);
		border-bottom-left-radius: 4px;
		box-shadow: none;
	}

	.bubble.user {
		background: var(--color-primary);
		color: white;
		border-bottom-right-radius: 4px;
		box-shadow: none;
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
		background: var(--color-primary);
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
		opacity: 1;
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
		background: var(--color-surface);
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
		background: var(--color-surface);
		border: 1.5px solid var(--color-border);
		border-radius: var(--radius-sm);
		font: inherit;
		font-size: 0.875rem;
		color: var(--color-text);
		transition: all var(--transition);
		outline: none;
	}

	.text-input::placeholder { color: var(--color-text-muted); }

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
		background: var(--color-primary);
		border: none;
		border-radius: var(--radius-sm);
		color: white;
		font: inherit;
		font-size: 0.82rem;
		font-weight: 600;
		cursor: pointer;
		transition: all var(--transition);
		box-shadow: none;
		white-space: nowrap;
	}

	.send-btn:hover {
		background: var(--color-primary-dark);
		transform: translateY(-1px);
		box-shadow: 0 4px 14px rgba(26, 107, 92, 0.38);
	}

	.send-btn:active { transform: translateY(0); }

	@media (max-width: 680px) {
		.upload-btn span { display: none; }
		.upload-btn, .send-btn { padding: 0.65rem 0.85rem; min-width: 44px; flex-shrink: 0; }
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

	/* The main panel holds one claim; the narrower rail explains its next step. */
	.intake-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: var(--space-6); align-items: start; }
	.intake-main { display: flex; flex-direction: column; min-width: 0; min-height: 520px; padding: var(--space-6); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
	.intake-main.has-conversation { min-height: 0; }
	.intake-panel-heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-6); }
	.intake-panel-heading h2 { margin: 0; font-size: var(--text-md); }
	.intake-panel-heading > span { color: var(--color-text-muted); font-size: var(--text-xs); }
	.intake-guide { display: grid; gap: var(--space-6); min-width: 0; }
	.guide-section { padding: var(--space-5); border-bottom: 1px solid var(--color-border); }
	.guide-section h2, .claim-context h2 { font-size: var(--text-md); margin: 0 0 var(--space-4); }
	.guide-section ul { padding-left: var(--space-5); margin: 0; display: grid; gap: var(--space-3); color: var(--color-ink); font-size: var(--text-xs); }
	.guide-section p, .claim-context p { color: var(--color-text-muted); font-size: var(--text-xs); line-height: 1.8; }
	.guide-section p { margin: var(--space-5) 0 0; }
	.workflow-guide ol { list-style: decimal; padding-left: var(--space-5); margin: 0; display: grid; gap: var(--space-5); }
	.workflow-guide li { padding-left: var(--space-2); color: var(--color-primary); font-size: var(--text-xs); }
	.workflow-guide strong, .workflow-guide span { display: block; }
	.workflow-guide strong { color: var(--color-ink); font-weight: 600; }
	.workflow-guide span { color: var(--color-text-muted); line-height: 1.8; margin-top: var(--space-1); }
	.claim-context { background: var(--color-light); border-radius: var(--radius-md); padding: var(--space-5); }
	.guide-label { display: block; font-size: var(--text-xs); color: var(--color-primary-dark); margin-bottom: var(--space-3); }
	.claim-context a { min-height: 44px; display: inline-flex; align-items: center; font-size: var(--text-xs); font-weight: 600; }
	.dropzone-box { min-height: 248px; border-color: var(--color-border-strong); padding: var(--space-8) var(--space-5); }
	.messages { flex: 1; max-height: max(240px, calc(100dvh - 360px)); padding: var(--space-1); gap: var(--space-4); }
	.bubble { max-width: calc(100% - 36px); }
	.bubble.error-bubble { color: var(--color-danger); background: var(--color-danger-soft); border-color: var(--color-danger); }
	.action-btn { min-height: 44px; padding: var(--space-2) var(--space-3); background: var(--color-surface); }
	.action-btn.primary { box-shadow: none; }
	.composer { align-items: center; flex-wrap: wrap; padding-top: var(--space-4); margin-top: var(--space-4); }
	.selection-summary { flex: 1; min-width: 0; overflow-wrap: anywhere; margin: 0; font-size: var(--text-xs); }
	.selection-summary span { display: block; color: var(--color-text-muted); }
	.text-input { width: auto; min-width: 120px; }
	.text-input:focus-visible { outline: 3px solid var(--color-focus); outline-offset: 2px; }
	.next-upload { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-4); border-top: 1px solid var(--color-border); padding-top: var(--space-4); margin-top: var(--space-5); }
	.next-upload a { display: inline-flex; align-items: center; min-height: 44px; font-size: var(--text-xs); }
	@media (max-width: 1100px) { .intake-layout { grid-template-columns: minmax(0, 1fr) 248px; gap: var(--space-4); } }
	@media (max-width: 900px) { .intake-layout { grid-template-columns: minmax(0, 1fr); } .intake-guide { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
	@media (max-width: 680px) { .intake-main { padding: var(--space-4); min-height: 0; } .intake-guide { grid-template-columns: minmax(0, 1fr); gap: var(--space-3); } .selection-summary { flex-basis: 100%; order: -1; } .send-btn { margin-left: auto; } .messages { max-height: 55dvh; } .dropzone-text strong { font-size: var(--text-md); } }
	.next-actions {
		display: flex;
		gap: var(--space-3);
		align-items: center;
	}
</style>
