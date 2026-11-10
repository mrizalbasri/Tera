import { authFetch } from '$lib/auth';

// All browser requests use the same-origin SvelteKit proxy. BACKEND_URL is server-only.
const BASE_URL = '/api';

/**
 * Normalisasi error API: pesan ramah pengguna dalam Bahasa Indonesia + detail
 * per-bidang bila tersedia. Menghindari pemaparan kode HTTP mentah (403, 413, 500, dll)
 * yang membingungkan karyawan.
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

export const HTTP_STATUS_MESSAGES: Record<number, string> = {
	400: 'Permintaan tidak dapat diproses. Periksa kembali kelengkapan data.',
	401: 'Sesi login telah berakhir. Silakan login kembali.',
	403: 'Akses ditolak. Anda tidak memiliki izin untuk melakukan tindakan ini.',
	404: 'Data atau berkas yang dicari tidak ditemukan.',
	408: 'Waktu tunggu permintaan habis. Silakan coba beberapa saat lagi.',
	409: 'Terjadi konflik data karena ada pembaruan terbaru. Silakan muat ulang halaman.',
	413: 'Ukuran file melebihi batas pengiriman server (maks 4.5 MB). Gunakan foto yang lebih ringkas.',
	415: 'Format file tidak didukung. Mohon gunakan JPG, PNG, atau PDF.',
	422: 'Periksa isian formulir. Ada nilai yang belum sesuai.',
	429: 'Terlalu banyak permintaan dalam waktu singkat. Mohon tunggu beberapa detik lalu coba lagi.',
	500: 'Terjadi kendala pada server saat memproses data. Silakan coba beberapa saat lagi.',
	502: 'Server Tera sementara tidak dapat dihubungi. Silakan tunggu beberapa detik dan coba lagi.',
	503: 'Layanan sedang bersiap atau dalam pemulihan. Silakan coba lagi beberapa saat.',
	504: 'Waktu koneksi ke server habis. Silakan coba beberapa saat lagi.'
};

export const USER_MESSAGES: Record<string, string> = {
	record_changed: 'Data sudah berubah. Muat ulang sebelum menyimpan kembali.',
	policy_dates_overlap: 'Tanggal berlaku bertumpang tindih dengan kebijakan terbit. Periksa tanggal versi yang ada.',
	policy_immutable: 'Versi terbit tidak dapat diedit. Salin sebagai draft baru untuk membuat perubahan.',
	invalid_policy: 'Aturan atau kategori kebijakan belum valid. Periksa isian draft.',
	authentication_required: 'Sesi berakhir. Silakan login kembali.',
	admin_access_required: 'Akun ini belum memiliki akses admin.',
	auth_unavailable: 'Sesi login belum dapat diperiksa. Coba lagi nanti.',
	auth_not_configured: 'Login belum dikonfigurasi. Hubungi pengelola Tera.',
	network_error: 'Tidak dapat menghubungi server Tera. Pastikan koneksi internet atau server berjalan.',
	unsupported_media_type: 'Format file tidak didukung. Gunakan file JPG, PNG, atau PDF.',
	unsupported_media_for_vision: 'Format file tidak didukung untuk pembacaan OCR. Gunakan gambar JPG atau PNG.',
	image_privacy_blocked: 'Gambar tidak dapat diproses karena mengandung data sensitif atau kebijakan privasi.',
	image_sanitization_failed: 'File gambar tidak dapat diproses. Coba gunakan foto nota lain.',
	file_too_large: 'Ukuran file melebihi batas maksimal 10 MB. Gunakan foto yang lebih ringkas.',
	request_too_large: 'Ukuran file melebihi batas pengiriman server (maks 4.5 MB). Gunakan foto yang lebih ringkas.',
	invalid_content_length: 'Ukuran pengiriman data tidak valid.',
	invalid_file: 'File tidak valid atau kosong. Pastikan file nota dapat dibuka.',
	duplicate_receipt: 'Nota yang sama sudah pernah diajukan sebelumnya.',
	receipt_required: 'Nota wajib dilampirkan sebelum klaim diajukan.',
	invalid_claim: 'Data klaim belum lengkap atau tidak valid.',
	receipt_content_unavailable: 'Isi berkas nota belum tersedia di server. Coba upload ulang.',
	malformed_extraction: 'Nota belum berhasil terbaca otomatis. Coba ambil foto ulang dengan pencahayaan terang dan tegak lurus.',
	extraction_confidence_low: 'Tulisan pada nota kurang terbaca jelas oleh AI. Coba foto ulang dengan fokus yang tajam.',
	not_found: 'Data yang dicari tidak ditemukan.',
	invalid_state_transition: 'Status klaim tidak bisa diubah pada tahap ini.',
	review_queue_changed: 'Antrean review berubah saat dimuat. Silakan muat ulang.',
	policy_unavailable: 'Kebijakan klaim belum tersedia. Coba lagi setelah layanan pulih.',
	provider_unavailable: 'Layanan pembaca nota (OCR) sedang tidak tersedia. Coba lagi nanti.',
	local_ocr_unavailable: 'Pembaca nota lokal belum siap. Notamu tetap tersimpan. Hubungi pengelola Tera jika masalah berulang.',
	provider_timeout: 'Waktu pembacaan nota habis. Notamu tetap aman, silakan coba proses lagi.',
	provider_rate_limited: 'Layanan pembaca AI sedang menerima banyak antrean. Mohon tunggu sejenak lalu coba lagi.',
	provider_authentication_failed: 'Autentikasi layanan OCR internal gagal. Tim teknis sedang menangani.',
	provider_invalid_request: 'Sistem OCR tidak dapat memproses format nota ini.',
	provider_unsupported_configuration: 'Konfigurasi pembaca nota belum didukung.',
	persistence_conflict: 'Data sedang diperbarui oleh sistem lain. Silakan coba kembali sesaat lagi.',
	idempotency_in_progress: 'Pengajuan sedang diproses oleh sistem. Mohon tunggu beberapa detik.',
	upstream_unavailable: 'Layanan backend belum dapat dihubungi atau sedang dimulai ulang. Coba lagi sebentar lagi.',
	invalid_origin: 'Permintaan ditolak demi keamanan (origin tidak valid).',
	internal_error: 'Terjadi kendala pada server saat memproses data. Silakan coba beberapa saat lagi.',
	http_413: 'Ukuran file melebihi batas pengiriman server (maks 4.5 MB). Gunakan foto yang lebih ringkas.'
};

export function resolveErrorMessage(
	status: number,
	code: string,
	rawMessage?: string | null,
	rawDetail?: string | null
): string {
	if (code && USER_MESSAGES[code]) {
		return USER_MESSAGES[code];
	}

	const candidate = (rawMessage || rawDetail || '').trim();
	if (
		candidate &&
		!candidate.toLowerCase().includes('traceback') &&
		!candidate.toLowerCase().includes('internal server error') &&
		!candidate.toLowerCase().includes('an unexpected error occurred') &&
		!candidate.toLowerCase().includes('private-')
	) {
		if (candidate.toLowerCase().includes('maximum allowed size') || candidate.toLowerCase().includes('request entity too large')) {
			return HTTP_STATUS_MESSAGES[413];
		}
		return candidate;
	}

	if (HTTP_STATUS_MESSAGES[status]) {
		return HTTP_STATUS_MESSAGES[status];
	}

	return 'Terjadi kendala pada server. Silakan coba lagi beberapa saat lagi.';
}

export function shortMessage(code: string, fallback?: string): string {
	if (USER_MESSAGES[code]) return USER_MESSAGES[code];
	if (fallback) return fallback;
	return 'Terjadi kendala pada server. Silakan coba lagi nanti.';
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try {
		response = await authFetch(`${BASE_URL}${path}`, init);
	} catch {
		throw new ApiError(0, 'network_error', USER_MESSAGES.network_error);
	}

	if (!response.ok) {
		if (response.status === 401 && typeof window !== 'undefined') window.location.assign('/login');
		let code = `http_${response.status}`;
		let rawMessage: string | undefined;
		let rawDetail: string | undefined;
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
			if (body.message) rawMessage = body.message;
			if (body.detail) rawDetail = body.detail;
		} catch {
			// respons non-JSON
		}
		const userMessage = resolveErrorMessage(response.status, code, rawMessage, rawDetail);
		throw new ApiError(response.status, code, userMessage, details);
	}

	if (response.status === 204) return undefined as T;
	return (await response.json()) as T;
}

export { BASE_URL };
