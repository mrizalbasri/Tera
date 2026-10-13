// All browser requests use the same-origin SvelteKit proxy. BACKEND_URL is server-only.
const BASE_URL = '/api';

/**
 * Normalisasi error API (roadmap: pesan singkat untuk pengguna + detail
 * per-bidang bila tersedia). Error jaringan dan respons non-JSON juga
 * dipetakan ke sini supaya UI tidak pernah menampilkan kegagalan sebagai
 * keberhasilan.
 */
export class ApiError extends Error {
	readonly status: number;
	readonly code: string;
	readonly details: Record<string, unknown> | null;

	constructor(status: number, code: string, message: string, details: Record<string, unknown> | null = null) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.code = code;
		this.details = details;
	}
}

const USER_MESSAGES: Record<string, string> = {
	network_error: 'Tidak dapat menghubungi server Tera. Pastikan backend berjalan.',
	unsupported_media_type: 'Format file tidak didukung. Gunakan JPG, PNG, atau PDF.',
	file_too_large: 'Ukuran file melebihi batas maksimal 10 MB.',
	invalid_file: 'File tidak valid atau kosong.',
	duplicate_receipt: 'Nota yang sama sudah pernah diajukan sebelumnya.',
	receipt_required: 'Nota wajib dilampirkan.',
	invalid_claim: 'Data klaim tidak valid.',
	receipt_content_unavailable: 'Isi nota tidak tersedia di server.',
	malformed_extraction: 'Pembacaan nota gagal. Coba upload nota yang lebih jelas.',
	not_found: 'Data tidak ditemukan.',
	invalid_state_transition: 'Status klaim tidak bisa diubah sekarang.',
	policy_unavailable: 'Kebijakan belum tersedia. Coba lagi setelah layanan pulih.',
	provider_unavailable: 'Layanan pembaca nota belum tersedia. Coba lagi nanti.',
	provider_timeout: 'Pembacaan nota melewati batas waktu. Coba lagi.',
	upstream_unavailable: 'Backend belum dapat dihubungi. Pastikan layanan API berjalan.'
};

function shortMessage(code: string, fallback: string): string {
	return USER_MESSAGES[code] ?? fallback;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try {
		response = await fetch(`${BASE_URL}${path}`, init);
	} catch {
		throw new ApiError(0, 'network_error', USER_MESSAGES.network_error);
	}

	if (!response.ok) {
		let code = `http_${response.status}`;
		const message = response.status === 422
			? 'Periksa isian formulir. Ada nilai yang belum sesuai.'
			: `Permintaan gagal (HTTP ${response.status}).`;
		let details: Record<string, unknown> | null = null;
		try {
			const body = (await response.json()) as {
				code?: string;
				message?: string;
				details?: Record<string, unknown>;
				detail?: string;
			};
			if (body.code) code = body.code;
			if (body.details) details = body.details;
		} catch {
			// respons non-JSON: pertahankan pesan generik
		}
		throw new ApiError(response.status, code, shortMessage(code, message), details);
	}

	if (response.status === 204) return undefined as T;
	return (await response.json()) as T;
}

export { BASE_URL };
