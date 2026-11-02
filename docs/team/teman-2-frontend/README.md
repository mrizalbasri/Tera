> Rencana ini sudah digantikan setelah koreksi pembagian tim. Pemilik menangani backend; Sheren dan Nisa menangani frontend. Ikuti [README frontend](../../../frontend/README.md) sebagai acuan terbaru.

# Tugas Nisa: frontend laporan dan QA alur pengguna

Baca [panduan tim](../README.md) dan [project plan](../PROJECT-PLAN.md). Fokusmu membuat laporan dapat digunakan dan membuktikan alur yang sudah ada. Ikuti DESIGN.md; pekerjaan ini melengkapi interface saat ini.

## File yang menjadi tanggung jawabmu

| File/area | Penggunaan |
| --- | --- |
| `frontend/src/routes/reports/+page.svelte` | Laporan; summary/unduhan sudah ada, kontrol filter belum ada |
| `frontend/src/lib/api/reports.ts` | Tipe summary/filter, query dan transport CSV |
| `frontend/src/routes/riwayat/+page.svelte` | Riwayat dan tombol ekspor; sesuaikan visibilitas hak akses |
| `frontend/src/routes/dashboard/+page.svelte` | Ringkasan; periksa kesesuaian label dan data |
| `frontend/src/routes/reviews/` dan `riwayat/[id]/` | Uji review dan detail |
| `frontend/src/lib/components/ClaimChat.svelte` | Alur pengajuan/klarifikasi yang diuji |
| `frontend/src/lib/api/*.spec.ts` | Pola tes Vitest transport |
| `docs/development/` | Hasil QA dan bukti demo |
| `DESIGN.md` | Acuan tampilan yang ada |

## F1. Jalankan baseline dan petakan alur

- [ ] Ikuti setup demo pada README tim.
- [ ] Jalankan pengajuan, riwayat/detail, klarifikasi, review, dashboard dan laporan.
- [ ] Catat route aktual dan masalah yang bisa direproduksi.
- [ ] Baca kontrak B1 bersama Sheren sebelum mengubah tipe respons.
- [ ] Buat `docs/development/team-qa.md` berisi kasus, langkah, hasil harapan, hasil aktual dan bukti.

Saat ditinjau, laporan memakai API nyata. Jangan mengisi grafik atau angka dengan data fiktif. Mock hanya dipakai untuk pengembangan/tes dengan kontrak yang sama.

## F2. Tambahkan filter laporan

- [ ] Tambahkan tanggal awal/akhir, employee, status dan kategori sesuai kontrak B1.
- [ ] Gunakan satu objek filter yang telah diterapkan untuk summary dan CSV.
- [ ] Pisahkan input yang sedang diedit dari filter yang sudah diterapkan bila memakai tombol Terapkan.
- [ ] Tampilkan periode dan filter aktif; reset mengembalikan kondisi awal.
- [ ] Tolak rentang tanggal terbalik dengan pesan dekat field.
- [ ] Tampilkan loading, error dengan retry, dan empty state yang relevan.
- [ ] Respons request lama tidak boleh menimpa hasil filter yang lebih baru.
- [ ] Gagal muat/ekspor mempertahankan filter dan menyediakan tindakan ulang.
- [ ] Panggil API melalui client/proxy yang sudah ada; jangan menaruh BACKEND_URL/token pada URL unduhan.

Selesai bila parameter summary dan CSV sama untuk filter yang diterapkan, termasuk karakter employee yang perlu URL encoding.

## F3. Cocokkan metrik dan hak akses

- [ ] Sesuaikan tipe/label metrik dengan B1, termasuk klarifikasi dan eskalasi bila ditambahkan.
- [ ] Jangan menyebut pending sebagai pekerjaan yang selesai otomatis.
- [ ] Tampilkan durasi null sebagai "Belum tersedia"; jangan mengubahnya menjadi nol detik.
- [ ] Bila estimasi penghematan ditampilkan, jelaskan rumus dan bahwa nilainya estimasi.
- [ ] Ekspor memberi status mengunduh, mencegah klik ganda dan menampilkan error yang dapat dicoba ulang.
- [ ] Sembunyikan/nonaktifkan ekspor khusus admin pada riwayat akun karyawan normal. Gunakan data peran terverifikasi yang sudah tersedia.
- [ ] Pertahankan akses demo sesuai baseline; jangan menghapus guard normal.
- [ ] Uji sesi berakhir, 403, backend tidak tersedia dan respons non-JSON.
- [ ] Kelola object URL unduhan agar dilepas setelah dipakai.

Frontend tidak menentukan kepemilikan atau reviewer. Backend tetap memverifikasi sesi/hak akses. Perubahan hooks/auth dikoordinasikan pemilik.

## Q1. Matriks QA minimum

Isi hasil aktual di `docs/development/team-qa.md`. Tabel ini adalah rencana tes, belum hasil lulus.

| Kasus | Hasil yang diharapkan |
| --- | --- |
| Nota valid sintetis | Klaim tersimpan, diproses dan hasil/timeline dapat dibuka |
| Upload yang sama diulang | Tidak membuat klaim ganda untuk replay; duplikat ditangani jelas |
| File tidak didukung/terlalu besar | Error jelas, tidak menampilkan pengajuan berhasil |
| Klarifikasi | Pertanyaan tampil, jawaban tercatat, hasil baru muncul |
| Review admin | Bukti tersedia, batal tidak menyimpan keputusan, konfirmasi menyimpan keputusan |
| Review diulang | Konflik ditampilkan tanpa menimpa keputusan sebelumnya |
| Provider gagal | Error/retry terlihat; tidak menampilkan persetujuan palsu |
| Riwayat kosong/filter tidak cocok | Empty state yang sesuai |
| Filter laporan | Tampilan dan CSV memakai parameter yang sama |
| Ekspor gagal | Filter bertahan dan unduhan dapat diulang |
| Karyawan A membuka klaim B | Ditolak/disembunyikan oleh backend dalam mode normal |
| Karyawan membuka laporan/review | Akses admin ditolak dalam mode normal |
| Tanpa sesi | Halaman terproteksi mengarah ke login dalam mode normal |
| Mode demo | Banner terlihat; restart backend menjadikan data demo kosong |

Mode normal diuji dengan akun tes bersama pemilik atau tes JWT sintetis yang sudah tersedia. Jangan menandai akses normal lulus hanya berdasarkan mode demo. Login/logout akun nyata membutuhkan pemilik akun.

Periksa viewport 375, 768 dan 1280px: tidak ada overflow horizontal halaman, tabel dapat dibaca, tombol dapat dijangkau, serta Tab/Enter/Escape dan fokus bekerja pada kontrol terkait.

## Tes dan hasil yang diserahkan

Dari `frontend/`, jalankan:

```powershell
pnpm test
pnpm check
pnpm build
```

Tambah tes bermakna untuk serialisasi filter, summary/CSV memakai filter sama, dan failure download. Tes browser/manual memeriksa perilaku halaman; lulus build saja belum membuktikan interaksi.

Serahkan:

- PR frontend laporan dengan screenshot desktop/mobile.
- Catatan QA dengan hasil aktual, tanggal, mode, perintah dan blocker.
- Panduan demo singkat di `docs/development/team-demo.md`: setup, data sintetis, urutan pengajuan → klarifikasi/review → laporan → CSV dan cara reset mode memory.
- Pembaruan README/spec frontend yang masih menyebut route atau status lama.

## Urutan kerja

F1 dapat dimulai tanpa perubahan backend. F2 memakai mock kontrak B1 yang disepakati. F3 dan QA integrasi menunggu PR backend. Koordinasikan `api/reports.ts` dan kontrak dengan Sheren agar perubahan dua sisi tidak berbeda.

