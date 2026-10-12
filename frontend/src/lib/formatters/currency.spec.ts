import { describe, expect, it } from 'vitest';
import {
	confidenceLevel,
	formatConfidence,
	formatCurrency,
	formatFileSize,
	toNumber
} from './currency';

describe('toNumber', () => {
	it('mengubah string Decimal dari backend menjadi number', () => {
		expect(toNumber('0.96')).toBe(0.96);
		expect(toNumber('10000')).toBe(10000);
	});

	it('menerima number apa adanya', () => {
		expect(toNumber(1500)).toBe(1500);
	});

	it('mengembalikan null untuk nilai kosong atau tidak valid', () => {
		expect(toNumber('bukan-angka')).toBeNull();
		expect(toNumber(null)).toBeNull();
		expect(toNumber(undefined)).toBeNull();
	});
});

describe('formatCurrency', () => {
	it('memformat Decimal string ke Rupiah', () => {
		const formatted = formatCurrency('10000');
		expect(formatted).toContain('10.000');
		expect(formatted).toContain('Rp');
	});

	it('menampilkan tanda — untuk nilai kosong, bukan nol palsu', () => {
		expect(formatCurrency(null)).toBe('—');
		expect(formatCurrency(undefined)).toBe('—');
	});
});

describe('formatFileSize', () => {
	it('menampilkan B, KB, dan MB yang terbaca', () => {
		expect(formatFileSize(512)).toBe('512 B');
		expect(formatFileSize(2048)).toBe('2 KB');
		expect(formatFileSize(3 * 1024 * 1024)).toBe('3.0 MB');
	});
});

describe('formatConfidence', () => {
	it('mengubah Decimal string menjadi persen', () => {
		expect(formatConfidence('0.96')).toBe('96%');
	});

	it('menampilkan tanda — untuk nilai kosong', () => {
		expect(formatConfidence(null)).toBe('—');
	});
});

describe('confidenceLevel', () => {
	it('>= 0.8 dianggap high', () => {
		expect(confidenceLevel('0.8')).toBe('high');
		expect(confidenceLevel(0.96)).toBe('high');
	});

	it('>= 0.6 dianggap medium', () => {
		expect(confidenceLevel('0.7')).toBe('medium');
	});

	it('< 0.6 atau kosong dianggap low', () => {
		expect(confidenceLevel('0.55')).toBe('low');
		expect(confidenceLevel(null)).toBe('low');
	});
});
