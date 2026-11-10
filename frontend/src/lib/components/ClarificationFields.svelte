<script lang="ts">
	let { fields, values = $bindable({}), disabled = false }: {
		fields: string[]; values?: Record<string, string>; disabled?: boolean;
	} = $props();
	const labels: Record<string, string> = { vendor: 'Nama toko', receipt_date: 'Tanggal nota', total: 'Total pembayaran (IDR)', currency: 'Mata uang', category: 'Kategori' };
</script>

<div class="clarification-fields">
	{#each fields.filter((field) => field in labels) as field}
		<label>
			<span>{labels[field]}</span>
			{#if field === 'category'}
				<select bind:value={values[field]} {disabled} required>
					<option value="">Pilih kategori</option><option value="meals">Makan</option><option value="fuel">BBM</option><option value="toll_parking">Tol / parkir</option><option value="hotel">Hotel</option><option value="other">Lainnya</option>
				</select>
			{:else if field === 'currency'}
				<select bind:value={values[field]} {disabled} required><option value="">Pilih mata uang</option><option value="IDR">IDR — Rupiah</option></select>
			{:else}
				<input type={field === 'receipt_date' ? 'date' : 'text'} inputmode={field === 'total' ? 'decimal' : undefined} bind:value={values[field]} {disabled} required maxlength="255" placeholder={field === 'vendor' ? 'Contoh: Toko Sinar Jaya' : field === 'total' ? 'Contoh: 75000 (tanpa titik ribuan)' : undefined} />
			{/if}
		</label>
	{/each}
	<p>Isi sesuai nota asli. Jawaban ini dicatat sebagai konfirmasi karyawan; finance tetap memverifikasi buktinya.</p>
</div>

<style>
	.clarification-fields { display: grid; gap: 16px; margin-block: 20px; min-width: 0; }
	label { display: grid; gap: 8px; font-weight: 600; }
	input, select { width: 100%; min-width: 0; padding: 10px; }
	p { color: var(--color-text-muted); font-size: 12px; margin: 0; }
</style>
