# PRD — Penguatan AI Agent dan Kesiapan Tera

| | |
|---|---|
| Produk | Tera |
| One-liner | Tera membantu karyawan dan finance menyelesaikan pemeriksaan reimbursement melalui ekstraksi AI, pemeriksaan terstruktur, klarifikasi, dan review manusia. |
| Versi / tanggal | 1.0 / 23 Oktober 2026 |
| Status | Disetujui pengguna pada 23 Oktober 2026; belum merupakan laporan penyelesaian |

## 1. Problem Statement

Alur pemeriksaan sudah tersedia, tetapi laporan lokal belum membuktikan login akun nyata, pemrosesan live pada deployment publik, atau kualitas keputusan reimbursement secara menyeluruh. Eksperimen OCR menemukan risiko separator nominal, digit salah, dan subtotal yang dipilih sebagai total. Pengguna juga membutuhkan tindak lanjut yang terlihat dan kebijakan yang dapat dikelola tanpa menghilangkan dasar keputusan lama.

Dokumen ini melaksanakan permintaan pengguna untuk mengerjakan seluruh rekomendasi dan memastikan kemampuan AI agent. PRODUCT.md menjadi dasar audiens dan batas produk. Angka sasaran pada PRD lama tidak diperlakukan sebagai hasil pengukuran.

## 2. Target User & Persona

| Peran | Deskripsi | Tujuan utama | Masalah yang ditangani |
|---|---|---|---|
| Karyawan | Pengaju reimbursement lintas industri | Mengajukan bukti dan menyelesaikan informasi kurang | Status atau tindakan berikutnya tidak diketahui |
| Finance/admin | Pemeriksa pengecualian dan pengelola kebijakan | Memutuskan berdasarkan bukti dan aturan yang berlaku | Pemeriksaan berulang dan dasar keputusan sulit ditelusuri |
| Operator | Pengelola deployment aplikasi | Menjalankan, memonitor, dan memulihkan layanan | Build lokal belum membuktikan kesiapan server |

Peran ini merupakan peran produk, bukan persona atau pelanggan fiktif.

## 3. User Stories & Fitur

| Kode | User story dan penerimaan | Fitur terkait | Prioritas |
|---|---|---|---|
| AR-01 | Sebagai karyawan, saya dapat menjalankan unggah, klarifikasi, nota pengganti, dan melihat keputusan dari akun saya; akun lain tidak dapat membaca atau mengubahnya. | Alur akun nyata dan ownership | M |
| AR-02 | Sebagai finance, saya dapat melihat pemeriksaan yang dijalankan agent, asal bukti, aturan/versi, alasan tindakan, serta informasi yang belum cukup. | Bukti agent | M |
| AR-03 | Sebagai finance, saya tidak menerima auto-approve dari total ambigu, mata uang tidak didukung, atau pemeriksaan wajib yang gagal; masing-masing memiliki reason code dan tindak lanjut. | Validasi nominal dan fail-closed | M |
| AR-04 | Sebagai karyawan, saya mendapat pertanyaan yang sesuai field bermasalah; setelah menjawab atau mengganti bukti, proses berlanjut tanpa keputusan ganda. | Tindakan adaptif terbatas | M |
| AR-05 | Sebagai pengembang, saya dapat mengulang evaluasi dengan sekurangnya 12 skenario berlabel yang meliputi jalur berhasil, risiko, dan kegagalan. | Evaluasi agent | M |
| AR-06 | Sebagai operator, saya dapat membangun frontend/backend untuk server, memigrasikan database uji, memeriksa readiness, dan membuktikan restore ke database terpisah. | Deployment dan recovery | M |
| AR-07 | Sebagai pengguna, saya dapat membuka nota gambar/PDF, menjawab klarifikasi, menyimpan review, dan mengunduh CSV melalui browser; pengujian meliputi mobile dan keyboard. | QA dan CI frontend | M |
| AR-08 | Sebagai karyawan, saya melihat notifikasi dalam aplikasi saat klaim membutuhkan tindakan atau mendapat keputusan; hanya pemilik dapat membacanya. | Notifikasi | M |
| AR-09 | Sebagai finance, saya melihat pengingat review tertunda; klaim yang sudah selesai tidak terus meminta tindakan. | Pengingat dalam aplikasi | M |
| AR-10 | Sebagai admin, saya dapat membuat draft kebijakan, menerbitkan versi bertanggal berlaku, dan melihat audit; klaim lama mempertahankan versi evaluasinya. | Manajemen kebijakan | M |
| AR-11 | Sebagai finance, saya melihat waktu pemrosesan aktif dan waktu menunggu manusia secara terpisah; estimasi dan data tidak tersedia diberi label. | Metrik operasional | M |
| AR-12 | Sebagai pemilik produk, saya memiliki panduan uji pengguna dan formulir hasil yang membedakan observasi nyata dari dugaan. | UAT dan riset pengguna | M |

Prioritas M menyatakan bagian dari permintaan ini. Pekerjaan dibagi ke paket terpisah agar setiap perubahan tetap dapat direview dan diuji.

## 4. Alur Utama (Happy Path)

1. Karyawan login dan mengunggah nota sintetis saat pengujian.
2. Agent memanggil ekstraksi AI, menyimpan hasil beserta sumber, lalu memeriksa kelengkapan dan nominal.
3. Jika bukti cukup, agent mengevaluasi versi kebijakan yang berlaku, duplikasi, dan anomali.
4. Agent mencatat keputusan atau memilih klarifikasi/review dengan alasan terstruktur.
5. Bila ada klarifikasi, proses menunggu input yang diotorisasi dan melanjutkan setelah input tersimpan.
6. Finance memutuskan kasus eskalasi berdasarkan nota, hasil pemeriksaan, dan alasan; keputusan manusia disimpan dengan identitas admin.
7. Notifikasi dalam aplikasi mengarahkan pemilik ke tindakan yang masih berlaku.
8. Laporan menampilkan hasil aktual beserta batas pengukurannya. Disetujui tetap berarti persetujuan klaim, bukan pembayaran.

## 5. Lingkup Rilis (MVP)

- Paket A: evaluasi baseline, pembuktian agent, penanganan nominal dan tindakan adaptif.
- Paket B: notifikasi/pengingat dalam aplikasi dan metrik waktu/usage.
- Paket C: draft/publikasi versi kebijakan dan kompatibilitas local/RAG.
- Paket D: CI frontend, QA browser, container server, restore, dan verifikasi live.
- Paket E: panduan dan pelaksanaan UAT bersama pengguna yang benar-benar tersedia.
- Tidak dibangun: pembayaran, akuntansi, approval bertingkat, pemisahan banyak perusahaan, serta pengiriman email/WhatsApp. Permintaan notifikasi diwujudkan di dalam aplikasi terlebih dahulu.

Uji akun nyata, publikasi, dan UAT tetap memiliki langkah manusia/layanan eksternal. Menyiapkan alat atau panduan tidak dihitung sebagai pelaksanaan langkah tersebut.

## 6. Kebutuhan Non-Fungsional Ringkas

| Aspek | Target penerimaan |
|---|---|
| Perangkat | Skenario inti lolos pada lebar 375 dan 1440 px, dengan keyboard; tabel lebar menggulir di wadahnya |
| Reliabilitas | Retry provider memakai batas konfigurasi; replay tidak menggandakan keputusan, publikasi kebijakan, atau notifikasi |
| Keamanan | Tes dua karyawan dan satu admin menolak akses lintas pemilik; tidak ada nota/token pada log atau hasil evaluasi yang dikomit |
| Audit | Setiap keputusan menunjuk bukti, hasil pemeriksaan, dan versi kebijakan yang digunakan |
| Kompatibilitas | Data/checkpoint lama tetap terbaca; migrasi additive memiliki tes upgrade berulang dan rollback transaksi gagal |
| Performa | Laporkan p50/p95 dan jumlah kegagalan; target latensi produksi baru ditetapkan dari baseline deployment |

## 7. Metrik Sukses

| Metrik | Target | Cara ukur |
|---|---|---|
| Salah approve pada kasus pemblokir | 0 pada set regresi yang ditentukan | Bandingkan keputusan dengan label independen; timeout tetap dihitung sebagai gagal |
| Skenario agent | Seluruh skenario penerimaan deterministik lulus | Jalankan fixture mock terisolasi dan rekam jejak tahap |
| Kelanjutan proses | Tidak ada keputusan/notifikasi ganda pada tes replay/concurrency | Tes restart, retry dan input ganda |
| Kelengkapan laporan evaluasi | Semua run mencatat versi Git, mode, jumlah kasus, error, durasi dan usage bila tersedia | Validasi schema laporan |
| CI frontend | Test, check, dan build dijalankan pada PR yang mengubah frontend | Workflow CI dan hasil eksekusi aktual |
| UAT | Setiap sesi mencatat peran, skenario, hasil tugas, waktu dan kendala dengan persetujuan peserta | Catatan sesi aktual; tanpa peserta tidak boleh dinyatakan lulus |

## 8. Asumsi & Terbuka

- Aplikasi tetap untuk satu perusahaan dan dua kelompok akses karyawan/admin.
- Rekomendasi arsitektur: pertahankan LangGraph dan aturan keputusan yang terstruktur. LLM dipakai pada pekerjaan yang memang membutuhkan interpretasi, dengan kontrak output tervalidasi.
- Notifikasi menggunakan aplikasi sendiri sehingga tidak memerlukan pemilihan penyedia pesan atau pengiriman ke pihak lain.
- Host publik, domain, anggaran layanan, dan peserta UAT belum dipilih dalam percakapan. Paket deployment disiapkan secara portabel; publikasi memerlukan tujuan yang diberikan pengguna.
- Login/OTP nyata diselesaikan pemilik akun; agen memverifikasi hasil dan alur sesudah sesi tersedia tanpa meminta password atau OTP.
- Penggunaan provider live memakai konfigurasi yang tersedia setelah mode, tujuan data, dan batas pemanggilan teridentifikasi. Tidak mengganti .env atau mengirim nota asli secara diam-diam.
- Rancangan teknis dan urutan pengerjaan: [SDD](2026-10-23-agent-readiness-design.md).
