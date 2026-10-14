# Tugas Sheren: frontend karyawan

PIC: Sheren. Penanggung jawab backend: pemilik proyek.
Status awal: belum dikerjakan dalam paket tugas ini.
Panduan setup dan aturan bersama: [README frontend](../README.md).
Koordinasi dengan: [Nisa](NISA.md).

Tujuan: karyawan dapat mengirim nota, membuka riwayat/detail, dan menjawab klarifikasi melalui API yang sudah tersedia. Lanjutkan halaman yang ada; checklist ini merupakan target kerja, bukan hasil pengujian.

## Mulai di sini

1. Jalankan frontend sesuai README dan gunakan baseline Git dari pemilik.
2. Minta backend demo beserta data nota sintetis untuk pengujian.
3. Coba alur pengajuan → riwayat → detail sebelum mengubah kode.
4. Catat bug yang ditemukan dan kerjakan S1 → S2 → S3.
5. Jika bagian sudah benar, verifikasi dan catat buktinya; perubahan kode tidak wajib untuk setiap checklist.

Semua path kode di bawah relatif terhadap folder `frontend/`.

## S1. Pengajuan nota — prioritas pertama

File utama:

- `src/routes/pengajuan/+page.svelte`
- `src/lib/components/ClaimChat.svelte`
- `src/lib/api/claims.ts`

Pekerjaan:

- [ ] Tampilkan file terpilih, nama, ukuran dan tindakan hapus sebelum dikirim.
- [ ] Tangani file kosong, format tidak didukung dan batas ukuran sesuai API.
- [ ] Tampilkan status upload/proses; cegah klik ganda selama request.
- [ ] Pertahankan idempotency agar retry tidak membuat pengajuan ganda.
- [ ] Bedakan nota tersimpan dari pemrosesan selesai.
- [ ] Tampilkan error dan tindakan retry; jangan tampilkan persetujuan tanpa keputusan backend.

Bukti selesai: nota sintetis dapat dikirim, klaim tersimpan dapat dibuka, dan retry tidak membuat pengajuan baru untuk request yang sama.

## S2. Riwayat dan detail — setelah S1

File utama:

- `src/routes/riwayat/+page.svelte`
- `src/routes/riwayat/[id]/+page.svelte`
- `src/routes/claims/[claimId]/+page.svelte`
- Formatter bersama di `src/lib/formatters/`

Pekerjaan:

- [ ] Tampilkan status, tanggal dan nominal dari API memakai formatter bersama.
- [ ] Pastikan klaim baru muncul di riwayat.
- [ ] Periksa navigasi daftar ke detail, tautan detail langsung dan refresh.
- [ ] Tampilkan extraction, alasan keputusan, temuan dan timeline yang tersedia.
- [ ] Sediakan loading, error/retry, empty state dan penanganan 404.
- [ ] Gunakan identitas sesi yang sudah tersedia.
- [ ] Koordinasikan ekspor pada riwayat dengan Nisa; CSV laporan saat ini khusus admin.

Bukti selesai: data daftar/detail cocok dengan API dan klaim tetap dapat dibuka setelah refresh.

## S3. Klarifikasi dan retry — setelah S2

File utama:

- `src/routes/claims/[claimId]/clarification/+page.svelte`
- `src/lib/components/ClaimChat.svelte`
- `src/lib/api/claims.ts`

Pekerjaan:

- [ ] Tampilkan pertanyaan terbuka dan input yang sesuai.
- [ ] Cegah jawaban ganda saat request berjalan.
- [ ] Setelah jawaban berhasil, muat hasil terbaru dan tampilkan riwayat jawaban.
- [ ] Sembunyikan form aktif bila klarifikasi sudah selesai.
- [ ] Periksa penggantian nota/retry hanya pada status yang didukung API.
- [ ] Tangani provider gagal dan sesi berakhir dengan pesan serta langkah berikutnya.

Bukti selesai: klaim klarifikasi dapat dilanjutkan hingga status baru tampil tanpa kehilangan riwayat jawaban.

## Pengujian yang harus dicatat

| Kasus | Hasil yang diharapkan |
| --- | --- |
| Nota valid sintetis | Tersimpan, dapat diproses dan dibuka pada detail |
| File tidak valid | Error terlihat, tidak ada pesan berhasil palsu |
| Klik kirim berulang | Tidak membuat klaim ganda untuk request yang sama |
| Riwayat kosong | Empty state jelas |
| Detail tidak ditemukan | Pesan 404 yang dapat dipahami |
| Klarifikasi berhasil | Jawaban tercatat dan hasil baru dimuat |
| Backend/provider gagal | Error jelas dan retry tersedia sesuai status |
| Karyawan A membuka klaim B | Akses ditolak dalam mode normal bersama pemilik |

Periksa desktop/mobile pada 375, 768 dan 1280px, serta keyboard dan fokus.
Mode demo tidak cukup untuk menyatakan akses normal lulus.

## Penyerahan

- [ ] Jalankan dari `frontend/`: `pnpm test`, `pnpm check`, `pnpm build`.
- [ ] Sertakan screenshot desktop/mobile untuk tampilan yang berubah.
- [ ] Catat hasil aktual, langkah reproduksi dan blocker di laporan QA bersama.
- [ ] Buat PR terfokus; usulan urutan PR: S1, lalu S2, lalu S3.
- [ ] Jelaskan perubahan dan perintah validasi pada deskripsi PR.

Koordinasikan layout, styles, types, auth dan komponen bersama sebelum diedit.
Backend/database/agent ditangani pemilik. Untuk kebutuhan API, kirim endpoint,
respons sekarang, perilaku yang dibutuhkan dan contoh sintetis.

Estimasi mengikuti [jadwal bersama](../README.md#urutan-pengerjaan), disesuaikan dengan waktu luang dan kesiapan API.
