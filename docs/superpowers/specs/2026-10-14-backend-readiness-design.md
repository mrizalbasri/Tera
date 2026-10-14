# Kesiapan backend Tera

## Tujuan dan cakupan

Menuntaskan tujuh kekurangan backend yang disetujui pengguna: pemulihan proses,
koordinasi worker, migrasi skema, pagination/laporan, batas API, monitoring, dan
validasi konfigurasi production. Perubahan UI, pembayaran, serta deployment ke
layanan publik berada di luar pekerjaan ini.

## Rancangan

Pertahankan FastAPI, LangGraph, dan PostgreSQL. PostgreSQL advisory lock melindungi
mutasi satu klaim antar-worker. Setiap node menyimpan hasil domain dan penanda
selesai dalam satu transaksi. Replay setelah crash membaca penanda tersebut;
panggilan provider yang terputus sebelum commit boleh diulang. Tidak ada jaminan
exactly-once untuk layanan eksternal. Checkpoint hanya memuat referensi.

Pemrosesan berikutnya memulihkan run yang tertinggal setelah memperoleh lock.
Worker SQL memindai otomatis setiap 30 detik, dengan batas 3 upaya pemulihan per
run; interval dan batas dapat dikonfigurasi. Perintah operasional juga memindai
dan memulihkan klaim tanpa permintaan pengguna.
Keputusan review yang belum tersimpan memerlukan pengiriman ulang input admin;
recovery tidak boleh mengarang keputusan admin. Review yang sudah tersimpan
harus tetap tunggal setelah restart.

Migrasi domain bernomor versi berjalan eksplisit di production, otomatis hanya
untuk pengembangan/test. Migrasi awal menerima skema lama tanpa menghapus data;
versi berikutnya menambah penanda node dan penyimpanan rate limit. Checkpoint
dan domain diperiksa saat readiness.

Daftar klaim dan review menerima limit/offset dengan total hasil terfilter.
Laporan memakai batch query, ekspor CSV menghasilkan halaman bertahap. Batas
upload diperiksa pada jumlah file, jumlah byte file, dan byte request sebelum
multipart selesai diparsing. Rate limit berbasis identitas terautentikasi dan
disimpan di PostgreSQL untuk deployment beberapa worker.

Production menolak memory/SQLite, provider mock, fallback mock, issuer/key
kosong, origin non-HTTPS, dan kredensial contoh. Liveness tetap terpisah dari
readiness. Metrik operasional hanya tersedia untuk admin dan tidak berisi data
nota, token, atau detail koneksi.

## Validasi

Uji rollback di tengah node; replay setelah node commit sebelum checkpoint;
crash/restart proses; konflik antar-worker PostgreSQL; resume klarifikasi dan
review; migrasi ulang dan data lama; pagination dengan batas/ownership;
rate limit lintas-instance; upload chunked/oversize; readiness gagal tanpa
membocorkan kredensial; konfigurasi production invalid. Jalankan seluruh pytest
dan pemeriksaan frontend untuk kompatibilitas API. Semua data uji sintetis,
database integrasi disposable, tanpa panggilan provider berbayar.
