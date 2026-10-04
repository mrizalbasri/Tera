import { describe, expect, it } from 'vitest';
import { shortClaimRef } from './claim';

describe('shortClaimRef', () => {
	it('membentuk referensi singkat dari UUID', () => {
		expect(shortClaimRef('1faeda3d-f355-4d4f-94b8-06e93cfa021b')).toBe('CLM-1FAE');
	});

	it('konsisten untuk UUID yang sama', () => {
		const id = '9d22ddd1-aaaa-bbbb-cccc-dddddddddddd';
		expect(shortClaimRef(id)).toBe(shortClaimRef(id));
	});
});
