# Menuntaskan jalur produksi Tera

Permintaan pengguna 24 Oktober 2026 melanjutkan kesiapan reimbursement sesuai
konsep produk: karyawan mengajukan nota, agent memeriksa bukti dan kebijakan,
finance menangani pengecualian, dan keputusan dapat ditelusuri.

## Cakupan perubahan

Pertahankan arsitektur, identitas visual, data lokal dan alur bisnis yang ada.
Perbaiki celah yang ditemukan pada jalur produksi:

1. Tolak placeholder dari contoh deployment pada password database, API key,
   model, endpoint dan issuer. ID admin harus berbentuk ID pengguna Clerk.
   Development dan test tetap mendukung fixture sintetis dan mode demo.
2. Ambil token sesi terbaru untuk permintaan notifikasi dan kebijakan, sama
   seperti klaim/review/laporan. Jangan kirim token ke URL eksternal atau health.
3. Teruskan Retry-After dan X-Request-ID dari backend melalui proxy agar klien
   menerima informasi pembatasan request dan pelacakan gangguan.

Mode demo tetap jujur berlabel di lingkungan pengembangan. Produksi menolak
demo, memory, mock dan fallback mock melalui validasi konfigurasi yang ada.
Tidak ada perubahan otomatis pada .env, database aplikasi, atau akun eksternal.

## Penerimaan dan verifikasi

Tambahkan regresi untuk konfigurasi contoh yang sebelumnya diterima, rotasi
token pada dua fitur tambahan, batas rute proxy, status/error/header dan body
permintaan. Jalankan pytest, tes frontend, pemeriksaan Svelte/TypeScript, build,
evaluasi agent offline, serta satu verifikasi live dengan nota sintetis pada
storage terisolasi. Integrasi PostgreSQL memakai database tes disposable.

## Batas rilis

Kesiapan kode tidak menyatakan deployment publik atau UAT telah lulus. Domain,
host produksi, backup terjadwal dan sesi pengguna tetap harus diverifikasi di
lingkungan tujuan. Pembayaran, akuntansi, approval bertingkat dan pemisahan
banyak perusahaan tetap di luar cakupan produk yang disepakati.
