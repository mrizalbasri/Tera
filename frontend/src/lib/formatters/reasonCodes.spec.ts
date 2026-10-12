import { describe, expect, it } from 'vitest';
import { describeReasonCode, describeReasonCodes } from './reasonCodes';

describe('describeReasonCode', () => {
	it('kode yang dikenal menghasilkan label dan penjelasan', () => {
		const info = describeReasonCode('extraction_confidence_low');
		expect(info.label).toBe('Keyakinan ekstraksi rendah');
		expect(info.explanation).toBeTruthy();
	});

	it('kode tak dikenal di-humanize tanpa mengarang arti', () => {
		const info = describeReasonCode('some_new_backend_code');
		expect(info.label).toBe('Some New Backend Code');
		expect(info.explanation).toBeUndefined();
	});
});

describe('describeReasonCodes', () => {
	it('menerjemahkan daftar reason code keputusan', () => {
		const reasons = describeReasonCodes(['above_auto_approve_limit', 'anomaly_score_high']);
		expect(reasons.map((r) => r.label)).toEqual([
			'Melebihi batas auto-approve',
			'Skor anomali tinggi'
		]);
	});

	it('daftar kosong atau null menghasilkan array kosong', () => {
		expect(describeReasonCodes([])).toEqual([]);
		expect(describeReasonCodes(null)).toEqual([]);
		expect(describeReasonCodes(undefined)).toEqual([]);
	});
});
