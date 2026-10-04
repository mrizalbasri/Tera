<script lang="ts">
	type AgentStep = {
		label: string;
		detail: string;
		status: 'done' | 'loading' | 'pending';
		icon: string;
	};

	type Message = {
		id: number;
		from: 'agent' | 'user';
		text?: string;
		fileName?: string;
		timestamp?: string;
		isClarificationReply?: boolean;
		typing?: boolean;          // animasi dots
		steps?: AgentStep[];       // langkah kerja agent (FR-12)
		verdict?: 'approved' | 'flagged' | 'rejected' | 'clarify';
		claimId?: string;
	};

	function getTime() {
		return new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
	}

	const AGENT_STEPS_TEMPLATE: AgentStep[] = [
		{ label: 'Membaca nota (OCR)', detail: 'Mengekstrak vendor, tanggal, total, dan item...', status: 'pending', icon: '🔍' },
		{ label: 'Validasi data', detail: 'Memeriksa format, total = jumlah item, tanggal wajar...', status: 'pending', icon: '✔️' },
		{ label: 'Cek kebijakan perusahaan', detail: 'Mencocokkan dengan limit kategori & syarat klaim...', status: 'pending', icon: '📋' },
		{ label: 'Deteksi duplikat', detail: 'Membandingkan dengan klaim sebelumnya...', status: 'pending', icon: '🔄' },
		{ label: 'Keputusan akhir', detail: 'Menentukan: setujui / tandai / minta klarifikasi...', status: 'pending', icon: '⚖️' }
	];

	let messages = $state<Message[]>([
		{
			id: 1,
			from: 'agent',
			text: 'Halo! 👋 Kirimkan foto nota transaksimu, dan biarkan Tera memproses klaimnya secara otomatis.',
			timestamp: getTime()
		}
	]);
	let draft = $state('');
	let fileInput: HTMLInputElement | undefined;
	let nextId = 2;
	let messagesEl: HTMLDivElement | undefined;
	let isProcessing = $state(false);
	let awaitingClarification = $state<{ claimId: string, stepsId: number } | null>(null);
	
	// Toast Notification
	let toast = $state<{ message: string, type: 'error' | 'success', visible: boolean }>({ message: '', type: 'error', visible: false });

	function showToast(message: string, type: 'error' | 'success' = 'error') {
		toast = { message, type, visible: true };
		setTimeout(() => { toast.visible = false; }, 3500);
	}

	function scrollToBottom() {
		setTimeout(() => {
			if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
		}, 60);
	}

	function sendText() {
		const text = draft.trim();
		if (!text) return;
		messages.push({ id: nextId++, from: 'user', text, timestamp: getTime(), isClarificationReply: !!awaitingClarification });
		draft = '';
		scrollToBottom();

		if (awaitingClarification) {
			const { claimId, stepsId } = awaitingClarification;
			awaitingClarification = null;
			resumeAgentProcessing(claimId, stepsId, text);
		}
	}

	function openFilePicker() {
		if (isProcessing) return;
		fileInput?.click();
	}

	async function sleep(ms: number) {
		return new Promise((r) => setTimeout(r, ms));
	}

	async function simulateAgentProcessing(fileName: string) {
		isProcessing = true;

		// 1. Typing indicator
		await sleep(600);
		const typingId = nextId++;
		messages.push({ id: typingId, from: 'agent', typing: true });
		scrollToBottom();

		// 2. Replace typing with steps bubble
		await sleep(1400);
		const steps: AgentStep[] = AGENT_STEPS_TEMPLATE.map((s) => ({ ...s }));
		const claimId = `CLM-${Date.now().toString().slice(-5)}`;
		const stepsId = nextId++;
		// Remove typing, add steps
		messages = messages.filter((m) => m.id !== typingId);
		messages.push({ id: stepsId, from: 'agent', steps, claimId, timestamp: getTime() });
		scrollToBottom();

		// 3. Reveal steps one by one
		const delays = [0, 1800, 2200, 1600, 2000];
		for (let i = 0; i < steps.length; i++) {
			await sleep(delays[i]);
			// Mark current as loading
			messages = messages.map((m) =>
				m.id === stepsId
					? { ...m, steps: steps.map((s, j) => ({ ...s, status: j < i ? 'done' : j === i ? 'loading' : 'pending' })) }
					: m
			);
			scrollToBottom();
			await sleep(900);
			// Mark current as done
			steps[i].status = 'done';
			messages = messages.map((m) =>
				m.id === stepsId ? { ...m, steps: [...steps] } : m
			);
		}

		// 4. Show verdict
		await sleep(400);
		// Simulate different outcomes
		const verdicts: Array<'approved' | 'flagged' | 'clarify'> = ['approved', 'clarify', 'approved'];
		const verdict = verdicts[Math.floor(Math.random() * verdicts.length)];
		
		if (verdict === 'clarify') {
			messages = messages.map((m) =>
				m.id === stepsId ? { ...m, verdict: 'clarify' } : m
			);
			scrollToBottom();
			await sleep(600);
			messages.push({ 
				id: nextId++, 
				from: 'agent', 
				text: `⚠️ **Butuh Klarifikasi (Klaim ${claimId})**\nTotal nota ini cukup besar (Rp 240.000). Apakah ini nota makan untuk beberapa orang? Mohon sebutkan jumlah orangnya.`, 
				timestamp: getTime() 
			});
			scrollToBottom();
			awaitingClarification = { claimId, stepsId };
			isProcessing = false;
			return; // Pause processing until user replies
		}

		messages = messages.map((m) =>
			m.id === stepsId ? { ...m, verdict } : m
		);
		scrollToBottom();

		// 5. Final text
		await sleep(600);
		const verdictText =
			verdict === 'approved'
				? `✅ Klaim **${claimId}** disetujui secara otomatis. Dana akan dicairkan dalam 1–2 hari kerja.`
				: `⚠️ Klaim **${claimId}** ditandai untuk ditinjau. Ada anomali kecil yang perlu konfirmasi tim finance.`;
		messages.push({ id: nextId++, from: 'agent', text: verdictText, timestamp: getTime() });
		scrollToBottom();

		isProcessing = false;
	}

	async function resumeAgentProcessing(claimId: string, stepsId: number, userReply: string) {
		isProcessing = true;
		await sleep(500);
		
		const typingId = nextId++;
		messages.push({ id: typingId, from: 'agent', typing: true });
		scrollToBottom();

		await sleep(1500);
		messages = messages.filter((m) => m.id !== typingId);
		
		// Update original steps bubble to approved
		messages = messages.map((m) =>
			m.id === stepsId ? { ...m, verdict: 'approved' } : m
		);

		messages.push({ 
			id: nextId++, 
			from: 'agent', 
			text: `Terima kasih atas konfirmasinya. ✅ Klaim **${claimId}** sekarang telah disetujui sesuai dengan limit ${userReply.includes('orang') || /\d/.test(userReply) ? 'makan kelompok' : 'kebijakan'}.`, 
			timestamp: getTime() 
		});
		scrollToBottom();
		isProcessing = false;
	}

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		// Validate file type
		const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
		if (!validTypes.includes(file.type)) {
			showToast('Format file tidak didukung! Harap upload JPG, PNG, atau PDF.', 'error');
			input.value = '';
			return;
		}
		messages.push({ id: nextId++, from: 'user', fileName: file.name, timestamp: getTime() });
		input.value = '';
		scrollToBottom();
		simulateAgentProcessing(file.name);
	}
</script>

<svelte:head>
	<title>Beranda | Tera Expense Agent</title>
	<meta name="description" content="Upload nota dan ajukan klaim reimbursement dengan mudah menggunakan Tera." />
</svelte:head>

<section class="chat-page">
	<!-- Toast Notification -->
	{#if toast.visible}
		<div class="toast {toast.type}">
			{#if toast.type === 'error'}
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
			{:else}
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
			{/if}
			<span>{toast.message}</span>
		</div>
	{/if}

	<header class="chat-header">
		<div class="header-left">
			<div class="agent-avatar">
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
					<span class="dot"></span> Online · Siap memproses nota
				</span>
			</div>
		</div>
		<div class="stat-badge">
			<span class="stat-num">3</span>
			<span class="stat-label">Klaim bulan ini</span>
		</div>
	</header>

	<div class="tip-banner">
		<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
		<span>Upload foto nota BBM, makan, tol, parkir, atau hotel. Auto-approve untuk klaim ≤ Rp 500.000.</span>
	</div>

	<div class="messages" aria-live="polite" bind:this={messagesEl}>
		{#each messages as message (message.id)}
			<div class="msg-row {message.from}">
				{#if message.from === 'agent'}
					<div class="avatar agent-mini">AI</div>
				{/if}

				<!-- Typing indicator -->
				{#if message.typing}
					<div class="bubble agent typing-bubble">
						<span class="dot-1"></span>
						<span class="dot-2"></span>
						<span class="dot-3"></span>
					</div>

				<!-- Agent Steps bubble (FR-12) -->
				{:else if message.steps}
					<div class="bubble agent steps-bubble">
						<div class="steps-header">
							<span class="steps-title">🤖 Memproses nota...</span>
							{#if message.claimId}<span class="claim-id">{message.claimId}</span>{/if}
						</div>
						<div class="steps-list">
							{#each message.steps as step}
								<div class="step-item {step.status}">
									<div class="step-icon-wrap">
										{#if step.status === 'done'}
											<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
										{:else if step.status === 'loading'}
											<span class="spin">⟳</span>
										{:else}
											<span class="step-emoji">{step.icon}</span>
										{/if}
									</div>
									<div class="step-text">
										<span class="step-label">{step.label}</span>
										{#if step.status !== 'pending'}
											<span class="step-detail">{step.detail}</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
						{#if message.verdict}
							<div class="verdict-badge {message.verdict}">
								{#if message.verdict === 'approved'}
									✅ Keputusan: <strong>DISETUJUI</strong>
								{:else if message.verdict === 'flagged'}
									⚠️ Keputusan: <strong>DITANDAI — perlu tinjauan</strong>
								{:else if message.verdict === 'clarify'}
									🤔 Keputusan: <strong>TERTUNDA — butuh klarifikasi</strong>
								{:else if message.verdict === 'rejected'}
									❌ Keputusan: <strong>DITOLAK</strong>
								{/if}
							</div>
						{/if}
						{#if message.timestamp}<span class="bubble-time">{message.timestamp}</span>{/if}
					</div>

				<!-- Normal bubble -->
				{:else}
					<div class="bubble {message.from}">
						{#if message.fileName}
							<div class="file-attach">
								<div class="file-icon">
									<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
										<polyline points="14 2 14 8 20 8"/>
									</svg>
								</div>
								<div>
									<strong>Nota terkirim</strong>
									<span class="file-name">{message.fileName}</span>
								</div>
							</div>
						{:else}
							<p>{message.text}</p>
						{/if}
						{#if message.timestamp}
							<span class="bubble-time">{message.timestamp}</span>
						{/if}
					</div>
				{/if}

				{#if message.from === 'user'}
					<div class="avatar user-mini">S</div>
				{/if}
			</div>
		{/each}
	</div>

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
		<button type="button" class="upload-btn" class:processing={isProcessing} onclick={openFilePicker} id="btn-upload-nota" title="Upload nota" disabled={isProcessing}>
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="17 8 12 3 7 8"/>
				<line x1="12" y1="3" x2="12" y2="15"/>
			</svg>
			<span>Upload Nota</span>
		</button>
		<input
			class="text-input"
			type="text"
			placeholder="Tulis pesan atau tanyakan sesuatu..."
			bind:value={draft}
			id="chat-text-input"
		/>
		<button type="submit" class="send-btn" id="btn-kirim-pesan">
			<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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

	.stat-badge {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		background: rgba(26, 107, 92, 0.07);
		padding: 0.5rem 0.9rem;
		border-radius: var(--radius-sm);
	}

	.stat-num {
		font-size: 1.25rem;
		font-weight: 800;
		color: var(--color-primary);
		line-height: 1;
	}

	.stat-label {
		font-size: 0.67rem;
		color: var(--color-text-muted);
		font-weight: 500;
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

	.file-attach {
		display: flex;
		align-items: center;
		gap: 0.65rem;
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

	.file-attach strong {
		display: block;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.file-name {
		display: block;
		font-size: 0.72rem;
		color: var(--color-text-muted);
		max-width: 200px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
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

	.upload-btn:hover {
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
		.stat-badge { display: none; }
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

	/* ─── Steps Bubble ─── */
	.steps-bubble {
		max-width: 88%;
		padding: 1rem 1.1rem;
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(14px);
		border: 1px solid var(--color-border);
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

	.claim-id {
		font-size: 0.68rem;
		font-weight: 600;
		color: var(--color-text-muted);
		background: rgba(26, 107, 92, 0.08);
		padding: 0.15rem 0.5rem;
		border-radius: 20px;
		font-family: monospace;
	}

	.steps-list {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.step-item {
		display: flex;
		align-items: flex-start;
		gap: 0.65rem;
		padding: 0.5rem 0;
		position: relative;
		opacity: 0.4;
		transition: opacity 0.3s ease;
	}

	.step-item.done,
	.step-item.loading {
		opacity: 1;
	}

	/* Vertical connector line */
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
	}

	.step-item.done .step-icon-wrap {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: white;
	}

	.step-item.loading .step-icon-wrap {
		background: rgba(245, 158, 11, 0.1);
		border-color: #f59e0b;
		color: #d97706;
	}

	.step-emoji { font-size: 0.7rem; }

	.spin {
		display: inline-block;
		animation: spinAnim 0.8s linear infinite;
		font-size: 0.95rem;
		color: #d97706;
	}

	@keyframes spinAnim {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.step-text {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		padding-top: 0.25rem;
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
	}

	/* ─── Verdict Badge ─── */
	.verdict-badge {
		margin-top: 0.85rem;
		padding: 0.6rem 0.9rem;
		border-radius: var(--radius-sm);
		font-size: 0.8rem;
		font-weight: 500;
		animation: fadeSlide 0.3s ease-out;
	}

	.verdict-badge.approved {
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid rgba(34, 197, 94, 0.25);
		color: #15803d;
	}

	.verdict-badge.flagged,
	.verdict-badge.clarify {
		background: rgba(245, 158, 11, 0.1);
		border: 1px solid rgba(245, 158, 11, 0.25);
		color: #b45309;
	}

	.verdict-badge.rejected {
		background: rgba(239, 68, 68, 0.08);
		border: 1px solid rgba(239, 68, 68, 0.2);
		color: #b91c1c;
	}

	/* ─── Upload btn disabled state ─── */
	.upload-btn:disabled,
	.upload-btn.processing {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none !important;
		box-shadow: none !important;
	}

	/* ─── Toast ─── */
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

	@keyframes toastSlide {
		from { top: -2rem; opacity: 0; }
		to { top: 1.5rem; opacity: 1; }
	}
</style>

