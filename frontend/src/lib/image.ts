/**
 * Client-side image optimization (HTMLCanvas).
 * Menjaga ukuran gambar di bawah batas payload serverless (Vercel max 4.5 MB)
 * sekaligus mempercepat waktu upload dan inferensi vision OCR.
 */

export async function compressImageIfLarge(
	file: File,
	maxSizeBytes: number = 3.5 * 1024 * 1024
): Promise<File> {
	if (!file.type.startsWith('image/') || file.size <= maxSizeBytes) {
		return file;
	}

	if (typeof window === 'undefined' || typeof document === 'undefined') {
		return file;
	}

	try {
		const img = new Image();
		const objectUrl = URL.createObjectURL(file);
		try {
			await new Promise<void>((resolve, reject) => {
				img.onload = () => resolve();
				img.onerror = () => reject(new Error('Gagal memuat gambar'));
				img.src = objectUrl;
			});

			let { width, height } = img;
			const maxDim = 2048;
			if (width > maxDim || height > maxDim) {
				if (width > height) {
					height = Math.round((height * maxDim) / width);
					width = maxDim;
				} else {
					width = Math.round((width * maxDim) / height);
					height = maxDim;
				}
			}

			const canvas = document.createElement('canvas');
			canvas.width = width;
			canvas.height = height;
			const ctx = canvas.getContext('2d');
			if (!ctx) return file;

			ctx.drawImage(img, 0, 0, width, height);

			const blob = await new Promise<Blob | null>((resolve) =>
				canvas.toBlob(resolve, 'image/jpeg', 0.85)
			);

			if (!blob || blob.size >= file.size) {
				return file;
			}

			const newName = file.name.replace(/\.[^.]+$/, '') + '.jpg';
			return new File([blob], newName, { type: 'image/jpeg', lastModified: Date.now() });
		} finally {
			URL.revokeObjectURL(objectUrl);
		}
	} catch {
		return file;
	}
}
