export function createSubmissionKeyManager(generateKey: () => string = () => crypto.randomUUID()) {
	let key: string | null = null;
	let selectedFile: File | null = null;

	return {
		selectFile(file: File) {
			if (selectedFile !== file) key = null;
			selectedFile = file;
		},
		clear() {
			key = null;
			selectedFile = null;
		},
		getKey() {
			key ??= generateKey();
			return key;
		}
	};
}
