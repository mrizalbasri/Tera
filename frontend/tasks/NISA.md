# Tugas Nisa: frontend admin

PIC: Nisa. Penanggung jawab backend: pemilik proyek.
Status awal: belum dikerjakan dalam paket tugas ini.
Panduan setup dan aturan bersama: [README frontend](../README.md).
Koordinasi dengan: [Sheren](SHEREN.md).

Tujuan: admin dapat memantau klaim, meninjau bukti, menyimpan keputusan review, dan mengunduh laporan. Lanjutkan halaman yang ada; checklist ini merupakan target kerja, bukan hasil pengujian.

## Mulai di sini

1. Jalankan frontend sesuai README dan gunakan baseline Git dari pemilik.
2. Minta backend demo dengan contoh klaim eskalasi dan data laporan.
3. Coba dashboard → review → laporan sebelum mengubah kode.
4. Catat bug yang ditemukan dan kerjakan N1 → N2 → N3.
5. Jika bagian sudah benar, verifikasi dan catat buktinya; perubahan kode tidak wajib untuk setiap checklist.

Semua path kode di bawah relatif terhadap folder `frontend/`.

## N1. Dashboard dan antrean review — prioritas pertama

File utama:

- `src/routes/dashboard/+page.svelte`
- `src/routes/reviews/+page.svelte`
- `src/lib/api/reviews.ts`

Pekerjaan:

- [ ] Gunakan data API untuk angka, klaim terbaru dan antrean review.
- [ ] Pastikan label metrik sesuai arti respons; jangan menampilkan angka contoh sebagai data nyata.
- [ ] Periksa tautan ke riwayat/detail/review.
- [ ] Sediakan loading, error dengan retry dan antrean kosong.
- [ ] Pastikan tampilan daftar dapat dibaca pada mobile.

Bukti selesai: jumlah dan daftar cocok dengan klaim sintetis yang diajukan melalui alur Sheren.

## N2. Detail dan keputusan review — setelah N1

File utama:

- `src/routes/reviews/[claimId]/+page.svelte`
- `src/lib/components/ReviewActions.svelte`
- `src/lib/api/reviews.ts`

Pekerjaan:

- [ ] Tampilkan bukti yang tersedia, alasan agent dan temuan risiko.
- [ ] Validasi alasan keputusan sesuai kontrak API.
- [ ] Tindakan approve/reject memerlukan konfirmasi.
- [ ] Batal konfirmasi tidak mengirim keputusan.
- [ ] Cegah klik ganda selama penyimpanan.
- [ ] Setelah berhasil, muat status/keputusan terbaru dan perbarui antrean.
- [ ] Tangani 409, sesi berakhir dan akses ditolak tanpa menimpa keputusan.
- [ ] Gunakan identitas reviewer dari sesi yang diverifikasi backend.

Bukti selesai: admin dapat memeriksa klaim, membatalkan konfirmasi, lalu menyimpan keputusan dan melihat hasil tersimpan setelah refresh.

## N3. Laporan dan CSV — setelah N2

File utama:

- `src/routes/reports/+page.svelte`
- `src/lib/api/reports.ts`

Kontrak saat rencana dibuat: `GET /reports/summary` dan
`GET /reports/claims.csv`. Filter tersedia: `period_from`,
`period_to` dan `employee_id`. Konfirmasi ulang pada baseline pemilik.

Pekerjaan:

- [ ] Tambahkan kontrol tanggal awal/akhir dan karyawan untuk filter yang didukung.
- [ ] Gunakan filter yang telah diterapkan untuk summary dan CSV.
- [ ] Tampilkan periode/filter aktif, tombol Terapkan dan Reset.
- [ ] Validasi rentang tanggal terbalik.
- [ ] Sediakan loading, empty state, error dan retry tanpa menghilangkan filter.
- [ ] Cegah respons lama menimpa hasil filter terbaru.
- [ ] Tampilkan status unduhan dan cegah klik ganda.
- [ ] Lepaskan object URL setelah unduhan.
- [ ] Tampilkan durasi null sebagai belum tersedia jika metrik tersebut ditampilkan.
- [ ] Jelaskan asumsi estimasi waktu jika ditampilkan.
- [ ] Koordinasikan ekspor riwayat dengan Sheren agar tampil sesuai hak akses admin.

Filter status/kategori menunggu dukungan backend dari pemilik. Perbaikan rumus
metrik juga tugas pemilik; jangan menghitung ulang keputusan bisnis sendiri
di frontend untuk menutupi masalah API.

Bukti selesai: summary dan CSV memakai filter sama, failure dapat dicoba ulang,
dan unduhan tetap mengikuti hak akses admin.

## Pengujian yang harus dicatat

| Kasus | Hasil yang diharapkan |
| --- | --- |
| Antrean kosong | Empty state jelas |
| Dashboard berisi klaim | Angka/daftar cocok dengan API |
| Batal konfirmasi | Tidak ada keputusan yang tersimpan |
| Approve/reject valid | Keputusan tersimpan dan antrean diperbarui |
| Review diulang | Konflik ditampilkan, keputusan lama tetap |
| Filter laporan | Query summary dan CSV sama |
| Tidak ada hasil filter | Empty state sesuai filter |
| Unduhan gagal | Error terlihat, filter bertahan, retry tersedia |
| Karyawan membuka halaman admin | Ditolak dalam mode normal bersama pemilik |
| Tanpa sesi/sesi berakhir | Penanganan login sesuai mekanisme yang ada |

Periksa desktop/mobile pada 375, 768 dan 1280px, serta keyboard dan fokus.
Mode demo tidak cukup untuk menyatakan akses normal lulus.

## Penyerahan

- [ ] Jalankan dari `frontend/`: `pnpm test`, `pnpm check`, `pnpm build`.
- [ ] Tambahkan tes relevan untuk filter dan failure download bila perilakunya berubah.
- [ ] Sertakan screenshot desktop/mobile untuk tampilan yang berubah.
- [ ] Catat hasil aktual, langkah reproduksi dan blocker di laporan QA bersama.
- [ ] Buat PR terfokus; usulan urutan PR: N1, lalu N2, lalu N3.
- [ ] Jelaskan perubahan dan perintah validasi pada deskripsi PR.

Koordinasikan layout, styles, types, auth dan komponen bersama sebelum diedit.
Backend/database/agent ditangani pemilik. Untuk kebutuhan API, kirim endpoint,
respons sekarang, perilaku yang dibutuhkan dan contoh sintetis.

Estimasi mengikuti [jadwal bersama](../README.md#urutan-pengerjaan), disesuaikan dengan waktu luang dan kesiapan API.
