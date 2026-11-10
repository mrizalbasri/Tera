# Perbaikan nominal, klarifikasi, dan UI klaim

## Tujuan dan batas perubahan

Menindaklanjuti laporan pengguna pada aplikasi live: nominal kosong walaupun
nota sudah dibaca, total disetujui yang tampak nol, pertanyaan klarifikasi yang
berulang, tombol persetujuan kurang terbaca, serta layout antrean yang padat.
Pertahankan identitas Tera dan batas otorisasi karyawan/finance.

Perubahan dikerjakan pada branch terfokus. Tidak termasuk deployment, perubahan
data produksi, pencairan pembayaran, atau pembukaan kembali klaim final.

## Kondisi kode saat diperiksa

- Tabel riwayat dan antrean memakai `Claim.declared_amount`.
- Ringkasan riwayat menjumlahkan nominal pengajuan kosong sebagai nol.
- CSV juga hanya mengekspor `declared_amount`.
- Ekstraksi dan nominal pengajuan merupakan rekaman yang terpisah.
- Jawaban klarifikasi disimpan sebagai teks dan proses kembali ke ekstraksi.
- Commit `ab61d70` sudah menangani sebagian pertanyaan berulang melalui eskalasi.
  Pertahankan perbaikan tersebut; jangan menggantinya dengan confidence buatan.
- Style global menetapkan teks putih pada `.approve`, sementara warna latar
  tombol lokal dapat berbeda. Perlu reproduksi di browser sebelum menentukan
  selector penyebab.

## Pendekatan

Perbaikan hanya di frontend paling kecil, tetapi menghasilkan aturan nominal
yang berbeda dari laporan dan ekspor. Mengisi `declared_amount` dari hasil OCR
lebih sederhana, tetapi menghilangkan perbedaan antara pernyataan karyawan dan
bukti mesin.

Gunakan satu aturan nominal di backend dengan sumber nilai yang eksplisit.
Frontend hanya menyajikan nilai dan provenance yang diberikan backend.
Pisahkan pekerjaan menjadi tiga bagian yang dapat diuji: nominal, klarifikasi,
dan layout. Tidak melakukan redesign atau refactor yang tidak terkait.

## Aturan nominal

1. Pertahankan nominal pengajuan, hasil ekstraksi, dan nominal final sebagai
   konsep terpisah. Jangan menimpa bukti ekstraksi asli.
2. Nilai uang memakai Decimal di backend, harus finite, positif, dan memiliki
   mata uang yang sesuai. Nilai kosong tetap null, bukan nol.
3. Nominal tampilan berprioritas: nominal final terverifikasi, total ekstraksi
   yang valid dari nota aktif, kemudian nominal pengajuan. Sertakan sumbernya.
4. Nota pengganti mengeluarkan nota lama dari perhitungan. Jangan menjumlahkan
   beberapa percobaan ekstraksi untuk nota yang sama.
5. Total multi-nota hanya tersedia jika seluruh nota aktif mempunyai nominal
   valid dan mata uang konsisten; hasil parsial tidak boleh tampak sebagai
   total lengkap.
6. Selisih nominal pengajuan dan bukti tetap terlihat, bukan diselesaikan dengan
   memilih nilai yang lebih nyaman tanpa penjelasan.
7. Finance dapat menetapkan nominal final ketika memberikan keputusan review
   terbuka, disertai alasan dan sumber bukti. Simpan bersama keputusan dalam
   transaksi yang sama. Karyawan tidak boleh menetapkan nominal final.
8. Persetujuan baru wajib mempunyai nominal final positif yang dikonfirmasi
   finance atau berasal dari hasil pipeline valid untuk auto-approval.
   Penolakan tidak wajib mempunyai nominal.
9. Klaim lama yang sudah disetujui tidak otomatis diubah. Bila bukti nominal
   valid tersedia, sajikan sebagai nominal dari ekstraksi, bukan verifikasi
   finance baru. Bila tidak tersedia, tampilkan jumlah klaim yang belum
   memiliki nominal dalam ringkasan.
10. Tabel karyawan/admin, antrean, detail, ringkasan, dan CSV memakai aturan
    backend yang sama. CSV mempertahankan kolom lama dan menambah nilai nominal
    yang dipakai, sumber, serta kelengkapannya.

## Klarifikasi

- Permintaan field yang spesifik mempunyai isian berlabel: nama toko, tanggal,
  nominal, mata uang, atau kategori sesuai informasi yang diminta.
- Simpan jawaban terstruktur sebagai konfirmasi karyawan yang terhubung dengan
  klarifikasi dan nota terkait; jangan menyamarkannya sebagai hasil OCR.
- Jawaban teks lama tetap dapat ditampilkan dan ditangani dengan jalur eskalasi
  yang ada. Jangan menebak nilai terstruktur dari teks yang ambigu.
- Validasi input sebelum mencatat jawaban sebagai selesai. Jawaban tanggal
  menggunakan format transport ISO; UI menggunakan pemilih tanggal.
- Tindak lanjut tidak menanyakan ulang field yang sudah dijawab untuk bukti
  yang sama tanpa menjelaskan konflik atau bukti yang berubah.
- Konfirmasi manusia tidak menaikkan confidence model. Bukti yang tetap
  meragukan diteruskan ke finance dengan jawaban dan bukti asli.
- Tidak ada byte nota, jawaban bebas, atau data sensitif baru di checkpoint.
- Pengiriman jawaban berulang tetap idempotent dan tidak membuat review ganda.

## UI dan navigasi

- Gunakan tema teal, token, dan font yang sudah ditetapkan DESIGN.md.
- Tombol aktif, dipilih, disabled, dan sedang menyimpan mempunyai state yang
  berbeda dan teks terbaca. Tampilkan alasan bila persetujuan diblokir.
- Beri jarak antara link detail dan kelompok aksi Setujui/Tolak. Pertahankan
  konfirmasi serta alasan wajib sebelum keputusan disimpan.
- Tanggal tidak terpecah per kata di desktop. Teks panjang dan email tidak
  memaksa lebar halaman. Kolom/tabel dapat scroll dalam region sendiri jika
  diperlukan; jangan menyembunyikan konten melalui clipping halaman.
- Pada mobile, gunakan susunan responsif yang tetap menampilkan identitas,
  nominal, status, dan akses detail. Target sentuh minimum 44px.
- Klaim terkirim tetap dapat ditemukan dari riwayat/detail setelah navigasi.
  Pengajuan menampilkan akses ke klaim yang masih perlu tindak lanjut tanpa
  menyimpan nota atau percakapan sensitif di localStorage.
- Verifikasi scroll halaman karyawan di browser. Keluhan arah scroll belum
  dipastikan dari screenshot admin; jangan menghilangkan scroll vertikal normal
  atau menyembunyikan audit trail untuk memaksakan halaman pendek.

## Pengujian dan penerimaan

- Tambahkan regresi untuk nominal pengajuan kosong dengan OCR valid, nominal
  benar-benar kosong, ekstraksi berulang, nota pengganti, multi-nota parsial,
  konflik nilai, serta nominal non-finite/non-positif.
- Uji review: persetujuan tanpa nominal ditolak backend, penetapan nilai final
  dan audit bersifat atomik, penolakan tanpa nominal tetap dapat berjalan,
  role karyawan tidak dapat menetapkan nilai final.
- Uji jawaban terstruktur, kompatibilitas teks lama, replay, eskalasi tanpa
  pengulangan pertanyaan, dan restart pada penyimpanan SQL.
- Uji konsistensi tabel, detail, agregat, dan ekspor; data lama tidak dilaporkan
  sebagai total lengkap bila nominal belum tersedia.
- Jalankan `python -m pytest` pada backend; `pnpm check`, `pnpm test`, dan
  `pnpm build` pada frontend. Laporkan dependency atau layanan yang tidak tersedia.
- Periksa hasil render antrean, detail review, riwayat, dan klarifikasi dengan
  data sintetis pada lebar 320, 375, 414, 768, dan desktop; uji keyboard,
  kontras state tombol, overflow, serta error/loading/empty state.
- Migrasi diuji pada database disposable, bukan produksi. Tidak memanggil
  provider live atau mengunggah nota asli untuk pengujian.
