/** Nominal dari backend bisa berupa number (float) atau string (Decimal). */
export type Numeric = number | string;

export function toNumber(value: Numeric | null | undefined): number | null {
	if (value == null) return null;
	const parsed = typeof value === 'number' ? value : Number(value);
	return Number.isFinite(parsed) ? parsed : null;
}

export function formatCurrency(value: Numeric | null | undefined, currency = 'IDR'): string {
	const amount = toNumber(value);
	if (amount == null) return '—';
	return new Intl.NumberFormat('id-ID', {
		style: 'currency',
		currency,
		maximumFractionDigits: 0
	}).format(amount);
}

/** Ukuran file dalam bentuk yang mudah dibaca (FR-01 metadata panel). */
export function formatFileSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Keyakinan 0..1 menjadi persen yang konsisten di semua tampilan (FR-02/07). */
export function formatConfidence(value: Numeric | null | undefined): string {
	const confidence = toNumber(value);
	if (confidence == null) return '—';
	return `${Math.round(confidence * 100)}%`;
}

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export function confidenceLevel(value: Numeric | null | undefined): ConfidenceLevel {
	const confidence = toNumber(value);
	if (confidence == null) return 'low';
	if (confidence >= 0.8) return 'high';
	if (confidence >= 0.6) return 'medium';
	return 'low';
}
