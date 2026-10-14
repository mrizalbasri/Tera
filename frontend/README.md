# Tera Frontend: panduan tugas Sheren dan Nisa

**Pemilik proyek mengerjakan backend. Sheren dan Nisa mengerjakan frontend bersama.**
Pembagian halaman berikut merupakan usulan awal supaya pekerjaan tidak bertabrakan.
Tanggal rencana: 14 Oktober 2026. Halaman sudah memiliki implementasi; tugas tim
adalah melengkapi dan memperbaiki alur yang ada.

## Pembagian kerja

Panduan tugas terpisah yang bisa dibagikan langsung:

- [Tugas Sheren: pengajuan, riwayat dan klarifikasi](tasks/SHEREN.md)
- [Tugas Nisa: dashboard, review dan laporan](tasks/NISA.md)

Gunakan checklist pada file masing-masing untuk mencatat progres.

| PIC | Area | Hasil utama |
| --- | --- | --- |
| Sheren | Pengajuan, riwayat, detail klaim dan klarifikasi | Alur karyawan terintegrasi dengan API |
| Nisa | Dashboard, antrean/detail review dan laporan | Alur admin dan ekspor terintegrasi dengan API |
| Pemilik proyek | Backend, database, agent, kontrak API dan konfigurasi autentikasi | API tersedia dan integrasi akhir ditinjau |

## Persiapan

1. Baca [CONTRIBUTING](../CONTRIBUTING.md) dan [DESIGN.md](../DESIGN.md).
2. Gunakan branch/commit baseline yang diberikan pemilik. Perubahan lokal yang
   belum dibagikan perlu masuk baseline sebelum kedua teman mulai bekerja.
3. Dari folder `frontend/`, jalankan `pnpm install`. Salin `.env.example` ke `.env`
   hanya jika file lokal belum ada.
4. Isi `BACKEND_URL` pada `.env` sesuai backend pemilik; default
   `http://127.0.0.1:8000`. Jalankan `pnpm dev`, lalu buka URL yang dicetak Vite.
5. Minta pemilik menyiapkan backend mode demo untuk onboarding tanpa akun/API key.
   Untuk mode normal, minta pemilik menyiapkan konfigurasi login dan akun tes.

Browser memakai proxy same-origin `/api`. `BACKEND_URL` hanya untuk server.
Mode demo memakai memory/mock; restart backend menghapus data demo. Pengujian
demo tidak membuktikan pembatasan akses pada mode normal.

## Tugas Sheren

Path berikut relatif terhadap `frontend/`.

| ID | Tugas | File utama |
| --- | --- | --- |
| S1 | Pengajuan nota | `src/routes/pengajuan/+page.svelte`, `src/lib/components/ClaimChat.svelte` |
| S2 | Riwayat dan detail | `src/routes/riwayat/+page.svelte`, `src/routes/riwayat/[id]/+page.svelte`, `src/routes/claims/[claimId]/+page.svelte` |
| S3 | Klarifikasi dan retry | `src/routes/claims/[claimId]/clarification/+page.svelte`, `ClaimChat.svelte`, `src/lib/api/claims.ts` |

### S1. Pengajuan nota

- [ ] Periksa pilihan file, nama/ukuran, hapus pilihan dan status upload.
- [ ] Tampilkan error file kosong, format tidak didukung dan ukuran berlebih sesuai backend.
- [ ] Cegah klik ganda selama request dan pertahankan mekanisme idempotency yang ada.
- [ ] Bedakan nota berhasil disimpan dari klaim berhasil diproses.
- [ ] Sediakan error dan retry tanpa menampilkan keputusan berhasil yang tidak diberikan API.

Selesai bila nota sintetis dapat dikirim, klaim tersimpan dapat dibuka, dan failure
state mempertahankan konteks yang diperlukan untuk retry.

### S2. Riwayat dan detail

- [ ] Gunakan data API, status, tanggal dan nominal melalui formatter bersama.
- [ ] Periksa daftar ke detail, refresh halaman dan tautan detail langsung.
- [ ] Pastikan loading, error dengan retry, serta empty state tersedia.
- [ ] Periksa hasil ekstraksi, alasan keputusan, temuan dan timeline.
- [ ] Gunakan identitas sesi yang sudah tersedia untuk riwayat karyawan.
- [ ] Koordinasikan tombol ekspor riwayat dengan Nisa; laporan/CSV saat ini khusus admin.

Selesai bila klaim baru ditemukan di riwayat dan data detail cocok dengan respons API.

### S3. Klarifikasi dan proses ulang

- [ ] Tampilkan pertanyaan terbuka dan input jawaban yang sesuai.
- [ ] Setelah jawaban dikirim, muat status/hasil terbaru dan pertahankan riwayat jawaban.
- [ ] Cegah pengiriman ganda dan sembunyikan form aktif ketika klarifikasi selesai.
- [ ] Periksa penggantian nota dan retry pada status yang didukung backend.
- [ ] Uji kegagalan provider, 404 dan sesi berakhir.

Selesai bila klarifikasi dapat dilanjutkan sampai hasil baru tampil, dengan pesan
kegagalan yang menjelaskan langkah berikutnya.

## Tugas Nisa

| ID | Tugas | File utama |
| --- | --- | --- |
| N1 | Dashboard dan antrean | `src/routes/dashboard/+page.svelte`, `src/routes/reviews/+page.svelte` |
| N2 | Keputusan review | `src/routes/reviews/[claimId]/+page.svelte`, `src/lib/components/ReviewActions.svelte`, `src/lib/api/reviews.ts` |
| N3 | Laporan dan ekspor | `src/routes/reports/+page.svelte`, `src/lib/api/reports.ts` |

### N1. Dashboard dan antrean review

- [ ] Pastikan angka, daftar terbaru dan antrean berasal dari API.
- [ ] Periksa tautan dashboard ke riwayat/detail/review.
- [ ] Tampilkan loading, error dengan retry dan antrean kosong.
- [ ] Pastikan label angka sesuai arti data; jangan memakai angka contoh sebagai metrik nyata.

Selesai bila dashboard dan antrean cocok dengan klaim sintetis dari alur pengajuan.

### N2. Detail review dan keputusan

- [ ] Tampilkan bukti yang tersedia, alasan agent dan temuan risiko sebelum tindakan.
- [ ] Validasi alasan keputusan sesuai kontrak API.
- [ ] Minta konfirmasi approve/reject; batal tidak mengirim keputusan.
- [ ] Cegah klik ganda dan muat keputusan/status terbaru setelah berhasil.
- [ ] Tampilkan konflik 409 dan akses ditolak tanpa menimpa keputusan sebelumnya.
- [ ] Gunakan identitas reviewer dari sesi yang diverifikasi backend.

Selesai bila admin dapat memeriksa bukti, membatalkan konfirmasi, lalu menyimpan
keputusan dengan alasan dan melihat antrean diperbarui.

### N3. Laporan dan ekspor

Endpoint sekarang adalah `GET /reports/summary` dan `GET /reports/claims.csv`.
Filter yang tersedia saat rencana dibuat: `period_from`, `period_to`, `employee_id`.

- [ ] Tambahkan kontrol tanggal awal/akhir dan karyawan untuk filter yang didukung.
- [ ] Gunakan filter yang telah diterapkan untuk summary dan CSV; tampilkan filter aktif.
- [ ] Sediakan Terapkan, Reset, validasi tanggal, loading, empty state dan retry.
- [ ] Pertahankan filter ketika muat/ekspor gagal; cegah respons lama menimpa hasil terbaru.
- [ ] Tampilkan status unduhan, cegah klik ganda dan lepaskan object URL setelah dipakai.
- [ ] Koordinasikan filter status/kategori dengan pemilik; aktifkan setelah API mendukungnya.
- [ ] Laporkan definisi metrik yang meragukan kepada pemilik untuk diperbaiki di backend.
- [ ] Jika durasi/estimasi ditampilkan, bedakan null dari nol dan jelaskan asumsi estimasi.

Catatan backend: saat ditinjau, otomatis dihitung sebagai total dikurangi manual,
sehingga pending ikut dihitung. Koreksi rumus adalah tugas pemilik.

Selesai bila summary dan CSV memakai filter sama, error dapat dicoba ulang,
dan laporan mengikuti hak akses admin.

## Koordinasi dan batas pekerjaan

Sheren memiliki alur karyawan dan `api/claims.ts`. Nisa memiliki alur admin,
`api/reviews.ts` dan `api/reports.ts`. Sebelum mengubah layout, styles/tokens,
types, client API, komponen bersama atau auth, tentukan satu PIC bersama pemilik.
Ikuti desain yang sudah tersedia.

Sheren dan Nisa tidak mendapat tugas mengubah backend, database atau agent.
Jika API belum cukup, sampaikan halaman/aksi, endpoint, respons sekarang,
field/perilaku yang dibutuhkan dan contoh sintetis kepada pemilik.
Mock boleh dipakai untuk pengembangan dengan kontrak yang disepakati;
integrasi baru selesai setelah diuji terhadap API nyata.

## Urutan pengerjaan

Estimasi awal 10 hari kerja efektif sejak baseline dan backend siap; sesuaikan
dengan waktu luang anggota.

| Tahap | Sheren | Nisa | Pemilik |
| --- | --- | --- | --- |
| H1 | Jalankan pengajuan/riwayat; catat gap | Jalankan admin/laporan; catat gap | Bagikan baseline dan kontrak |
| H2–H3 | S1: pengajuan | N1: dashboard/antrean | Tangani kebutuhan API |
| H4–H5 | S2: riwayat/detail | N2: review | Verifikasi kontrak/akses |
| H6–H7 | S3: klarifikasi/retry | N3: laporan/CSV | Lengkapi API bila diperlukan |
| H8 | Uji alur karyawan bersama Nisa | Uji alur admin bersama Sheren | Integrasikan PR |
| H9–H10 | Perbaikan, screenshot dan QA | Perbaikan, screenshot dan QA | Review akhir |

## Kriteria selesai dan penyerahan

- [ ] Jalankan `pnpm test`, `pnpm check`, dan `pnpm build`; catat hasil aktual.
- [ ] Tambahkan tes bermakna untuk perilaku yang berubah, termasuk failure path.
- [ ] Periksa browser pada 375, 768 dan 1280px, tanpa overflow horizontal halaman.
- [ ] Periksa keyboard, fokus, label form dan pesan error pada kontrol yang diubah.
- [ ] Uji hak akses mode normal bersama pemilik; mode demo saja tidak cukup.
- [ ] Sertakan screenshot desktop/mobile dan langkah reproduksi pada PR.
- [ ] Gunakan data sintetis; jangan commit `.env`, token, secret atau nota asli.

Keduanya membuat catatan QA bersama di `docs/development/frontend-team-qa.md`
(relatif terhadap root proyek): skenario, langkah, hasil harapan, hasil aktual,
mode, screenshot dan blocker. Pemilik menangani backend dan review integrasi akhir.
Gunakan PR kecil dan Conventional Commits sesuai CONTRIBUTING.

## Perintah pengembangan

SvelteKit and TypeScript frontend for Expense Agent.

## Developing

Install dependencies and start the development server:

```powershell
pnpm install
pnpm dev
```

Run the type and Svelte checks:

```powershell
pnpm check
```

Build and preview a production version:

```powershell
pnpm build
pnpm preview
```

To deploy the app, install an adapter for the target environment.
