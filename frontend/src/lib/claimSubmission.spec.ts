import { describe, expect, it } from 'vitest';
import { createSubmissionKeyManager } from './claimSubmission';

const firstFile = new File(['receipt'], 'receipt.jpg', { type: 'image/jpeg' });

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

		manager.selectFile(new File(['receipt'], 'replacement.jpg', { type: 'image/jpeg' }));

		expect(manager.getKey()).toBe('key-2');
	});

	it('creates a new key for different contents with identical metadata', () => {
		let sequence = 0;
		const manager = createSubmissionKeyManager(() => `key-${++sequence}`);
		const sameMetadataFile = new File(['first'], 'receipt.jpg', { type: 'image/jpeg' });
		const differentContents = new File(['second'], 'receipt.jpg', { type: 'image/jpeg' });

		manager.selectFile(sameMetadataFile);
		expect(manager.getKey()).toBe('key-1');
		manager.selectFile(differentContents);

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
