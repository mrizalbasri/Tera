<script lang="ts">
	import Icon from './Icon.svelte';
</script>

<section class="auth-story" aria-labelledby="auth-story-title">
	<a class="auth-brand" href="/" aria-label="Tera, beranda"><img src="/logo.webp" width="40" height="40" alt="" />Tera<span>Expense workspace</span></a>
	<div class="auth-narrative">
		<p class="auth-kicker"><span></span> PENGELUARAN KERJA, LEBIH TERTATA</p>
		<h1 id="auth-story-title">Dari pengajuan.<br />Sampai <em>keputusan.</em></h1>
		<p class="auth-description">Satu ruang untuk mengajukan nota, memeriksa bukti, dan mengikuti setiap prosesnya.</p>
		<div class="workflow" aria-label="Alur pengajuan Tera">
			<div class="workflow-heading"><span>ALUR KLAIM</span><Icon name="receipt" size={18} /></div>
			<div class="workflow-step"><span class="step-icon"><Icon name="upload" /></span><div><strong>Ajukan pengeluaran</strong><small>Nota dan konteks, dalam satu tempat.</small></div><span class="step-number">01</span></div>
			<div class="workflow-step"><span class="step-icon"><Icon name="shield" /></span><div><strong>Periksa dengan bukti</strong><small>Data nota dicocokkan dengan kebijakan.</small></div><span class="step-number">02</span></div>
			<div class="workflow-step"><span class="step-icon final"><Icon name="check" /></span><div><strong>Ikuti hasil keputusan</strong><small>Status dan tindak lanjut tetap terlihat.</small></div><span class="step-number">03</span></div>
		</div>
	</div>
	<div class="auth-story-footer"><span><Icon name="shield" size={16} />Akses sesuai peran</span><span><Icon name="review" size={16} />Riwayat keputusan</span></div>
</section>

<style>
	.auth-story { position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; min-height: 100svh; padding: clamp(28px, 4vw, 64px); background: var(--color-auth); color: var(--color-inverse); }
	.auth-story::before { content: ''; position: absolute; inset: 0; pointer-events: none; background-image: linear-gradient(var(--color-auth-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-auth-line) 1px, transparent 1px); background-size: 64px 64px; mask-image: linear-gradient(135deg, transparent 30%, black); }
	.auth-story > * { position: relative; }
	.auth-brand { display: flex; align-items: center; gap: 12px; text-decoration: none; color: var(--color-inverse); font-size: 28px; font-weight: 750; letter-spacing: -1px; }
	.auth-brand img { background: var(--color-surface); border-radius: 10px; padding: 4px; }
	.auth-brand > span { font-size: 12px; font-weight: 450; color: var(--color-auth-muted); margin-left: auto; letter-spacing: 0; }
	.auth-narrative { padding-block: 48px; max-width: 520px; }
	.auth-kicker { display: flex; align-items: center; gap: 8px; font-size: 10px; font-weight: 650; letter-spacing: 1.5px; color: var(--color-auth-highlight); margin: 0 0 24px; }
	.auth-kicker span { height: 6px; width: 6px; border-radius: 50%; background: var(--color-auth-highlight); }
	h1 { font-size: clamp(34px, 4.1vw, 60px); font-weight: 650; line-height: 1.12; letter-spacing: -.055em; margin: 0; color: var(--color-inverse); }
	h1 em { font-style: normal; color: var(--color-auth-highlight); }
	.auth-description { color: var(--color-auth-muted); max-width: 370px; font-size: 15px; line-height: 1.8; margin: 24px 0 32px; }
	.workflow { border: 1px solid var(--color-auth-border); background: var(--color-auth-raised); border-radius: 16px; padding: 20px 24px; box-shadow: 0 24px 48px var(--color-action-shadow); }
	.workflow-heading { display: flex; justify-content: space-between; align-items: center; color: var(--color-auth-muted); font-size: 10px; letter-spacing: 1.4px; padding-bottom: 12px; }
	.workflow-step { display: flex; align-items: center; gap: 16px; padding: 16px 0; }
	.workflow-step + .workflow-step { border-top: 1px solid var(--color-auth-border); }
	.step-icon { display: inline-flex; padding: 10px; background: var(--color-auth-hover); border: 1px solid var(--color-auth-border); border-radius: 12px; color: var(--color-auth-highlight); }
	.step-icon.final { background: var(--color-auth-highlight); color: var(--color-auth); }
	.workflow-step strong { display: block; font-size: 14px; font-weight: 600; }
	.workflow-step small { display: block; color: var(--color-auth-muted); font-size: 12px; line-height: 1.6; margin-top: 4px; }
	.step-number { margin-left: auto; color: var(--color-auth-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
	.auth-story-footer { display: flex; gap: 24px; flex-wrap: wrap; color: var(--color-auth-muted); font-size: 11px; }
	.auth-story-footer > span { display: inline-flex; align-items: center; gap: 8px; }
	@media (max-width: 900px) { .auth-story { padding: 32px; } .auth-brand > span { display: none; } .workflow { padding: 16px; } }
	@media (max-width: 760px) { .auth-story { min-height: auto; padding: 24px; } .auth-narrative { padding: 20px 0 4px; } .auth-kicker { display: none; } h1 { font-size: 30px; } .auth-description { display: none; } .workflow, .auth-story-footer { display: none; } }
</style>
