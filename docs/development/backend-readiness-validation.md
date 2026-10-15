# Validasi kesiapan backend — 14 Oktober 2026

## Hasil akhir

- `python -m pytest -q -ra --tb=short` dengan PostgreSQL 18 disposable:
  **517 passed, 5 skipped**, durasi 187,78 detik.
- Lima tes yang dilewati: integrasi pgvector dalam `test_pgvector.py` karena
  instalasi PostgreSQL lokal tidak memiliki extension vector. CI telah memakai
  `pgvector/pgvector:0.8.7-pg18`; eksekusi CI belum dilakukan dari workspace ini.
- `pnpm check`: **0 errors, 0 warnings**.
- `pnpm build`: **berhasil**. Warning ukuran chunk dan pemilihan platform
  adapter-auto masih berasal dari konfigurasi frontend yang ada.
- `git diff --check`: **berhasil**.

## Bukti perilaku

63 kasus operasional dalam `backend/tests/test_backend_readiness.py` meliputi:

- Proses Python benar-benar keluar dengan `os._exit` di tengah node; transaksi
  di-rollback, run dipulihkan, dan keputusan/attempt yang sudah commit tidak ganda.
- Dua proses PostgreSQL memproses klaim yang sama dengan satu run/keputusan;
  advisory lock juga diuji eksplisit ketika proses lain masih memegang lock.
- Crash sebelum commit dan setelah commit sebelum checkpoint, termasuk titik
  menunggu klarifikasi/review. Input berikutnya tetap dapat diproses.
- Klarifikasi tersimpan sebelum run lanjutan dibuat, penolakan jawaban lama tanpa
  mutasi, review terputus yang memerlukan input admin baru, serta batas recovery.
- Rollback intake termasuk isi file dan idempotency key; transaksi yang sudah
  rollback tidak boleh melakukan commit parsial. Kegagalan provider yang sengaja
  dicatat tetap menyimpan diagnostic attempt serta audit kegagalan secara atomik.
- Migrasi legacy SQLite dan PostgreSQL, eksekusi berulang, pemeriksaan versi,
  perintah migrasi/recovery, dan production tanpa DDL saat readiness/startup.
- Pagination dan total terfilter, ownership, batch laporan, streaming CSV,
  neutralisasi formula CSV, serta koreksi pending yang bukan klaim otomatis selesai.
- Batas jumlah/ukuran unggahan, request chunked, counter rate limit lintas-instance,
  Retry-After, pemisahan identitas, readiness 503 tanpa detail rahasia, dan akses
  admin untuk operasi.

## Lingkungan dan batas verifikasi

Semua nota/identitas uji sintetis. Provider LLM memakai mock; tidak ada panggilan
provider berbayar dan tidak ada verifikasi API key live. PostgreSQL uji dibuat
terpisah pada localhost port 55438; fixture memakai database disposable miliknya.
Konfigurasi `.env` serta database aplikasi tidak diubah.

Perubahan diserahkan di workspace. Deployment publik, aktivasi konfigurasi
production nyata, dan instalasi pgvector pada mesin pengguna tidak dilakukan.
Lihat [[backend-operations]] untuk prosedur deployment dan operasi.

## Tindak lanjut review — 15 Oktober 2026

- Migrasi v3 memperbaiki `insertion_order` pada PostgreSQL legacy tanpa versi,
  v1, dan v2. Tes membuktikan baris lama tetap utuh, nilai identity terisi,
  insert berikutnya mendapat urutan baru, migrasi bisa diulang, serta kegagalan
  DDL me-rollback perubahan kolom dan tidak mencatat versi baru.
- Pembacaan upload berbatas, validasi jumlah/ukuran, parsing nominal, dan
  penyamaran detail duplikat dipindahkan ke `ReceiptUploadService`. Route
  menangani kontrak HTTP, identitas pengguna, dan pemanggilan service.
- API query SQL, reporting, dan operasi memiliki anotasi parameter/return;
  reporting dan metrik memakai helper durasi yang sama.
- Tes terarah: **95 passed** untuk readiness, migrasi legacy PostgreSQL,
  intake, ownership, dan reporting; tes service upload: **5 passed**.
- Suite backend lengkap dengan SQLite dan PostgreSQL 18 disposable:
  **526 passed, 5 skipped**, durasi 208,07 detik. Lima skip tetap merupakan
  integrasi pgvector yang memerlukan extension lokal; tidak ada kegagalan tes.
- Diff PR #27 terhadap merge-base `main` tidak memuat file frontend. Perubahan
  UI pada `ClaimChat.svelte`, halaman utama, dan dashboard berasal dari riwayat
  dasar PR. Perubahan frontend lokal tetap di luar commit perbaikan ini.
- PostgreSQL disposable untuk review memakai localhost port 55439; semua data
  sintetis dan fixture hanya membuat/menghapus database uji miliknya.
