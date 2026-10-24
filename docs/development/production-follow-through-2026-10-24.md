# Verifikasi lanjutan produksi Tera, 24 Oktober 2026

Status: perbaikan kode teruji; rilis produksi belum dinyatakan siap.
Pekerjaan melanjutkan branch `feat/agent-readiness` dan draft PR #36.

## Perubahan

- Konfigurasi production menolak placeholder pada file contoh deployment,
  model kosong, domain contoh, serta daftar admin yang bukan ID pengguna Clerk.
  Pesan validasi tidak mencetak password database.
- Notifikasi dan kebijakan mengambil token sesi terbaru melalui transport
  autentikasi yang sama dengan klaim, review dan laporan.
- Proxy meneruskan `Retry-After` dan `X-Request-ID`, termasuk pada respons error.
  Tes memeriksa body/header mutasi, query, pembatasan rute, origin asing dan
  kegagalan koneksi backend.
- README dan panduan operasional diperbarui agar tidak lagi menyebut dashboard
  berisi metrik prototype atau pagination klaim/review sebagai pekerjaan tertunda.

## Hasil aktual

| Pemeriksaan | Hasil | Batas bukti |
|---|---|---|
| Backend dengan PostgreSQL disposable | 638 passed, 1 skipped; 182,64 detik | Skip hanya skenario server tanpa pgvector karena extension tersedia |
| Frontend | 96 tes lulus | Termasuk regresi rotasi token dan proxy |
| Svelte/TypeScript | 0 error, 0 warning | Pemeriksaan otomatis |
| Build frontend | Berhasil, adapter-node | Build lokal, bukan deployment publik |
| Evaluasi agent offline | 18/18; 0 false approvals | Dataset sintetis, mock/local/rules; bukan ukuran akurasi produksi |
| Backup/restore PostgreSQL | Berhasil | Dua database sintetis disposable; nota, keputusan, checkpoint, notifikasi, kebijakan dan vector-schema probe pulih; replay tidak menggandakan keputusan |
| Provider live | Gagal, `provider_unavailable`, HTTP 502 | Satu upaya PNG sintetis pada memory terisolasi, tanpa fallback mock; layanan endpoint lokal menolak koneksi TCP |

Laporan JSON rinci pada folder yang diabaikan Git:
`backend/data/local/evaluation/agent-readiness-2026-10-24.json`,
`live-agent-2026-10-24.json`, dan `restore-2026-10-24.json`.
Evaluasi mencatat revision dasar `ed3e43b` dengan working tree berubah.
Keberhasilan live pada 23 Oktober adalah bukti historis; percobaan terbaru
pada 24 Oktober belum berhasil.

## Pekerjaan yang bergantung pada lingkungan dan pengguna

1. Nyalakan kembali layanan provider lokal atau konfigurasi endpoint pengganti,
   lalu ulangi `python -m scripts.verify_live_agent`. Jangan menganggap mock
   sebagai hasil pembacaan nota asli.
2. Pilih host/domain HTTPS dan isi konfigurasi production aktual, termasuk
   instance Clerk, admin, provider, database, kebijakan perusahaan, backup dan
   monitor. Ikuti [runbook deployment](agent-deployment.md).
3. Verifikasi login/logout akun nyata pada domain tujuan serta jalankan
   [UAT karyawan dan finance](agent-uat.md). Pengujian JWT dan fixture tidak
   menggantikan sesi pengguna.

Konfigurasi lokal tetap development/SQL dengan provider mock. File `.env`,
database aplikasi, dan perubahan pengguna yang sudah ada tidak diubah.
Mode demo tetap tersedia dan berlabel untuk pengembangan; validasi production
menolak demo/memory/mock. Pembayaran, akuntansi, approval bertingkat serta
pemisahan banyak perusahaan tetap di luar cakupan produk saat ini.
