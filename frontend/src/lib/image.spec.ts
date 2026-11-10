import { describe, expect, it } from 'vitest';
import { compressImageIfLarge } from './image';

describe('compressImageIfLarge', () => {
	it('returns the same file when size is below the threshold', async () => {
		const smallFile = new File(['hello'], 'nota.png', { type: 'image/png' });
		const result = await compressImageIfLarge(smallFile, 1024 * 1024);
		expect(result).toBe(smallFile);
	});

	it('returns the same file for non-image files such as PDF', async () => {
		const pdfContent = new Uint8Array(5 * 1024 * 1024);
		const pdfFile = new File([pdfContent], 'nota.pdf', { type: 'application/pdf' });
		const result = await compressImageIfLarge(pdfFile, 1024 * 1024);
		expect(result).toBe(pdfFile);
	});
});
