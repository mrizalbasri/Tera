import { describe, expect, it } from 'vitest';
import { createSubmissionKeyManager } from './claimSubmission';

const firstFile = {
	name: 'receipt.jpg',
	size: 128,
	type: 'image/jpeg',
	lastModified: 1
};

describe('claim submission idempotency state', () => {
	it('reuses the key when retrying the unchanged file', () => {
		let sequence = 0;
		const manager = createSubmissionKeyManager(() => `key-${++sequence}`);

		manager.selectFile(firstFile);
		const firstKey = manager.getKey();
		const retryKey = manager.getKey();

		expect(retryKey).toBe(firstKey);
		expect(sequence).toBe(1);
	});

	it('creates a new key when the selected file changes after failure', () => {
		let sequence = 0;
		const manager = createSubmissionKeyManager(() => `key-${++sequence}`);

		manager.selectFile(firstFile);
		expect(manager.getKey()).toBe('key-1');

		manager.selectFile({ ...firstFile, name: 'replacement.jpg' });

		expect(manager.getKey()).toBe('key-2');
	});

	it('clears the key when the selected file is removed', () => {
		let sequence = 0;
		const manager = createSubmissionKeyManager(() => `key-${++sequence}`);

		manager.selectFile(firstFile);
		expect(manager.getKey()).toBe('key-1');
		manager.clear();

		expect(manager.getKey()).toBe('key-2');
	});
});
