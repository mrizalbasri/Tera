<script lang="ts">
	type Message = {
		id: number;
		from: 'agent' | 'user';
		text?: string;
		fileName?: string;
	};

	let messages = $state<Message[]>([
		{
			id: 1,
			from: 'agent',
			text: 'Halo! Kirim foto nota kamu, nanti aku bantu proses klaimnya.'
		}
	]);
	let draft = $state('');
	let fileInput: HTMLInputElement | undefined;
	let nextId = 2;

	function sendText() {
		const text = draft.trim();
		if (!text) return;
		messages.push({ id: nextId++, from: 'user', text });
		draft = '';
	}

	function openFilePicker() {
		fileInput?.click();
	}

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		messages.push({ id: nextId++, from: 'user', fileName: file.name });
		input.value = '';
	}
</script>

<svelte:head>
	<title>Beranda | Expense Agent</title>
	<meta name="description" content="Expense reimbursement automation prototype" />
</svelte:head>

<section class="chat">
	<header>
		<h1>Halo, Salesman</h1>
		<p>Upload nota transaksi, dan biarkan Tera bekerja.</p>
	</header>

	<div class="messages" aria-live="polite">
		{#each messages as message (message.id)}
			<div class="bubble {message.from}">
				{#if message.fileName}
					<strong>Foto nota terkirim</strong>
					<span>{message.fileName}</span>
				{:else}
					{message.text}
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
		/>
		<button type="button" class="upload" onclick={openFilePicker}>Nota</button>
		<input
			class="text"
			type="text"
			placeholder="Tulis pesan atau upload nota..."
			bind:value={draft}
		/>
		<button type="submit" class="send">Kirim</button>
	</form>
</section>

<style>
	.chat {
		display: flex;
		flex-direction: column;
		height: calc(100dvh - 3rem);
		max-width: 760px;
	}

	h1 {
		margin: 0 0 0.25rem;
		font-size: 1.5rem;
	}

	header p {
		margin: 0;
		color: #5b665c;
	}

	.messages {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin: 1.25rem 0;
		overflow-y: auto;
	}

	.bubble {
		display: flex;
		flex-direction: column;
		max-width: 80%;
		padding: 0.7rem 0.95rem;
		border-radius: 12px;
		line-height: 1.5;
	}

	.bubble.agent {
		align-self: flex-start;
		background: #ffffff;
		border: 1px solid #dfe5dc;
	}

	.bubble.user {
		align-self: flex-end;
		background: #eaf2e7;
		color: #36593b;
	}

	.composer {
		display: flex;
		gap: 0.5rem;
		padding-top: 0.75rem;
		border-top: 1px solid #dfe5dc;
	}

	.text {
		flex: 1;
		padding: 0.65rem 0.9rem;
		border: 1px solid #cbd9c9;
		border-radius: 8px;
		background: #ffffff;
		font: inherit;
	}

	.upload,
	.send {
		padding: 0.65rem 1rem;
		border: 1px solid #cbd9c9;
		border-radius: 8px;
		background: #ffffff;
		color: #36593b;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	.send {
		background: #36593b;
		border-color: #36593b;
		color: #ffffff;
	}
</style>