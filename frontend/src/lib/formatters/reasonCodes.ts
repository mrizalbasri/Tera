/**
 * Formatter reason code terpusat (FR-08): semua kode dari backend
 * diterjemahkan di satu tempat agar konsisten di seluruh UI.
 */

export interface ReasonCodeInfo {
	label: string;
	explanation?: string;
}

const REASON_CODES: Record<string, ReasonCodeInfo> = {
	total_ambiguous: { label: 'Total pembayaran belum jelas', explanation: 'Nominal belum dapat dibedakan dari subtotal atau angka lain pada nota.' },
	total_breakdown_mismatch: { label: 'Rincian nominal berbeda', explanation: 'Subtotal, pajak, dan diskon belum cocok dengan total pembayaran.' },
	invalid_total: { label: 'Total nota tidak valid' },
	invalid_receipt_date: { label: 'Tanggal nota tidak valid' },
	clarification_limit_reached: { label: 'Perlu pemeriksaan finance', explanation: 'Informasi belum cukup setelah batas klarifikasi tercapai.' },
	policy_date_gap: { label: 'Kebijakan tanggal nota belum tersedia', explanation: 'Finance perlu memeriksa klaim karena belum ada versi kebijakan yang berlaku.' },
	policy_evidence_missing: { label: 'Dasar kebijakan belum tersedia' },
	auto_approve_amount_limit: { label: 'Melebihi batas persetujuan otomatis' },
	confidence_unavailable: { label: 'Keyakinan pembacaan belum tersedia' },
	auto_approved: { label: 'Disetujui otomatis' },
	below_auto_approve_limit: {
		label: 'Di bawah batas auto-approve',
		explanation: 'Nominal klaim berada di bawah batas persetujuan otomatis.'
	},
	above_auto_approve_limit: {
		label: 'Melebihi batas auto-approve',
		explanation: 'Nominal klaim melebihi batas persetujuan otomatis sehingga perlu review.'
	},
	within_policy: {
		label: 'Sesuai kebijakan',
		explanation: 'Klaim tidak melanggar aturan kebijakan yang berlaku.'
	},
	confidence_sufficient: {
		label: 'Keyakinan bacaan memadai',
		explanation: 'Hasil ekstraksi melewati ambang keyakinan minimum.'
	},
	escalation_amount_threshold: {
		label: 'Melebihi ambang eskalasi nominal',
		explanation: 'Nominal klaim melebihi ambang sehingga diteruskan ke reviewer manusia.'
	},
	policy_limit_exceeded: {
		label: 'Melebihi limit kebijakan',
		explanation: 'Nilai klaim melampaui limit kategori pada kebijakan yang berlaku.'
	},
	extraction_confidence_low: {
		label: 'Keyakinan ekstraksi rendah',
		explanation: 'Agent tidak cukup yakin membaca nota, mohon perjelas nota.'
	},
	duplicate_suspected: {
		label: 'Diduga nota ganda',
		explanation: 'Nota serupa pernah diajukan sebelumnya.'
	},
	duplicate_receipt: {
		label: 'Nota ganda',
		explanation: 'Nota yang sama sudah pernah diajukan.'
	},
	anomaly_score_high: {
		label: 'Skor anomali tinggi',
		explanation: 'Pola klaim menonjol dibanding riwayat sehingga perlu review.'
	},
	needs_review: {
		label: 'Perlu review',
		explanation: 'Klaim diteruskan ke reviewer manusia.'
	},
	image_may_be_unreadable: {
		label: 'Gambar kemungkinan tidak terbaca',
		explanation: 'Ukuran berkas terlalu kecil untuk dibaca dengan andal.'
	},
	pdf_metadata_incomplete: {
		label: 'Metadata PDF tidak lengkap',
		explanation: 'Struktur PDF tidak lengkap, hasil baca bisa jadi kurang akurat.'
	},
	receipt_content_unavailable: {
		label: 'Isi nota tidak tersedia',
		explanation: 'Server tidak dapat membaca isi nota yang tersimpan.'
	},
	malformed_extraction: {
		label: 'Pembacaan nota gagal',
		explanation: 'Hasil pembacaan tidak valid, coba nota yang lebih jelas.'
	}
};

/** Kode tak dikenal tetap tampil, di-humanize, tanpa mengarang arti. */
export function describeReasonCode(code: string): ReasonCodeInfo {
	const known = REASON_CODES[code];
	if (known) return known;
	const humanized = code
		.split(/[_\s-]+/)
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
	return { label: humanized || code };
}

export function describeReasonCodes(codes: string[] | null | undefined): ReasonCodeInfo[] {
	if (!codes?.length) return [];
	return codes.map(describeReasonCode);
}
