export type SubmissionFile = Pick<File, 'name' | 'size' | 'type' | 'lastModified'>;

function fileFingerprint(file: SubmissionFile) {
	return `${file.name}:${file.size}:${file.type}:${file.lastModified}`;
}

export function createSubmissionKeyManager(generateKey: () => string = () => crypto.randomUUID()) {
	let key: string | null = null;
	let fingerprint: string | null = null;

	return {
		selectFile(file: SubmissionFile) {
			const nextFingerprint = fileFingerprint(file);
			if (fingerprint !== nextFingerprint) key = null;
			fingerprint = nextFingerprint;
		},
		clear() {
			key = null;
			fingerprint = null;
		},
		getKey() {
			key ??= generateKey();
			return key;
		}
	};
}
