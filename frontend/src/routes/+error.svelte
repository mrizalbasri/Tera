<script lang="ts">
	import { page } from '$app/state';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

	interface ErrorPresentation {
		badge: string;
		title: string;
		description: string;
		suggestion: string;
		icon: IconName;
		actionLabel: string;
		actionHref?: string;
		isReload?: boolean;
	}

	const presentation = $derived.by<ErrorPresentation>(() => {
		const status = page.status;
		const message = page.error?.message;

		if (status === 404) {
			return {
				badge: 'Halaman Tidak Ditemukan',
				title: 'Halaman atau data tidak ditemukan',
				description: message && !message.startsWith('Not')
					? message
					: 'Halaman yang Anda tuju mungkin sudah dipindahkan, dihapus, atau tautan tidak valid.',
				suggestion: 'Silakan periksa kembali alamat URL atau kembali ke halaman pengajuan klaim.',
				icon: 'search',
				actionLabel: 'Ke Halaman Pengajuan',
				actionHref: '/pengajuan'
			};
		}

		if (status === 403) {
			return {
				badge: 'Akses Dibatasi',
				title: 'Anda belum memiliki izin akses',
				description: message && message !== 'Forbidden'
					? message
					: 'Akun Anda belum memiliki hak akses untuk membuka halaman atau fitur ini.',
				suggestion: 'Jika Anda memerlukan akses ke halaman ini, silakan hubungi tim administrator Tera.',
				icon: 'shield',
				actionLabel: 'Kembali ke Dashboard',
				actionHref: '/dashboard'
			};
		}

		if (status === 502 || status === 503 || status === 504) {
			return {
				badge: 'Layanan Sedang Menyiapkan Koneksi',
				title: 'Server sedang bersiap atau memulihkan koneksi',
				description: message && !message.startsWith('Internal') && !message.startsWith('Service')
					? message
					: 'Layanan backend atau database sedang aktif kembali setelah jeda istirahat (cold start) atau pemulihan berkala.',
				suggestion: 'Biasanya proses ini hanya membutuhkan waktu 5–15 detik. Silakan klik tombol "Coba Lagi" di bawah.',
				icon: 'refresh',
				actionLabel: 'Coba Lagi Sekarang',
				isReload: true
			};
		}

		return {
			badge: 'Kendala Sistem',
			title: 'Terjadi kendala saat memuat halaman',
			description: message && !message.startsWith('Internal')
				? message
				: 'Sistem mengalami kendala sementara saat memproses permintaan Anda.',
			suggestion: 'Data Anda tetap aman. Coba muat ulang halaman ini atau kembali beberapa saat lagi.',
			icon: 'alert',
			actionLabel: 'Muat Ulang Halaman',
			isReload: true
		};
	});

	function handleAction() {
		if (presentation.isReload && typeof window !== 'undefined') {
			window.location.reload();
		}
	}
</script>

<svelte:head>
	<title>{presentation.title} · Tera</title>
</svelte:head>

<div class="error-container">
	<div class="error-card">
		<div class="error-icon-badge">
			<Icon name={presentation.icon} size={28} />
		</div>

		<span class="error-badge">{presentation.badge}</span>
		<h1 class="error-title">{presentation.title}</h1>
		<p class="error-desc">{presentation.description}</p>
		<p class="error-suggestion">{presentation.suggestion}</p>

		<div class="error-actions">
			{#if presentation.isReload}
				<button type="button" class="button" onclick={handleAction}>
					<Icon name="refresh" size={18} />
					{presentation.actionLabel}
				</button>
			{:else}
				<a href={presentation.actionHref ?? '/pengajuan'} class="button">
					{presentation.actionLabel}
				</a>
			{/if}

			<a href="/pengajuan" class="button secondary">
				<Icon name="plus" size={18} />
				Pengajuan Baru
			</a>
			<a href="/dashboard" class="button secondary">
				<Icon name="home" size={18} />
				Dashboard
			</a>
		</div>

		<div class="error-meta">
			<small>Kode referensi teknis: <code>{page.status}</code></small>
		</div>
	</div>
</div>

<style>
	.error-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: var(--space-6) var(--space-4);
	}
	.error-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md, 16px);
		box-shadow: var(--shadow-card);
		max-width: 580px;
		width: 100%;
		padding: var(--space-8);
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	.error-icon-badge {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: var(--color-light);
		color: var(--color-primary);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: var(--space-4);
	}
	.error-badge {
		display: inline-block;
		font-size: var(--text-xs);
		font-weight: 650;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-primary-dark);
		background: var(--color-soft);
		border: 1px solid var(--color-border);
		padding: 4px 12px;
		border-radius: 9999px;
		margin-bottom: var(--space-3);
	}
	.error-title {
		font-size: var(--text-xl, 1.5rem);
		font-weight: 700;
		color: var(--color-ink);
		margin: 0 0 var(--space-3);
		line-height: 1.3;
	}
	.error-desc {
		font-size: var(--text-sm);
		color: var(--color-text);
		margin: 0 0 var(--space-2);
		line-height: 1.6;
	}
	.error-suggestion {
		font-size: var(--text-sm);
		color: var(--color-text-muted);
		margin: 0 0 var(--space-6);
		line-height: 1.6;
	}
	.error-actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
		justify-content: center;
		width: 100%;
		margin-bottom: var(--space-6);
	}
	.error-meta {
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-border);
		width: 100%;
		color: var(--color-text-muted);
		font-size: var(--text-xs);
	}
	.error-meta code {
		font-family: var(--font-mono);
		background: var(--color-soft);
		padding: 2px 6px;
		border-radius: 4px;
		color: var(--color-ink);
	}
</style>
