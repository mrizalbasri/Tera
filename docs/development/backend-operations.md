# Operasi backend Tera

## Menjalankan dan memigrasikan

Jalankan perintah dari `backend/` dengan interpreter yang memiliki dependensi
`requirements.txt`. Konfigurasi contoh berada di `backend/.env.example`.

Untuk production, isi `ENVIRONMENT=production`, `STORAGE_BACKEND=sql`, URL
PostgreSQL dengan kredensial sendiri, `PROVIDER_MODE=live`, API key provider,
origin frontend HTTPS, issuer Clerk HTTPS, dan ID admin. Mock, memory, SQLite,
fallback mock, demo, serta kredensial contoh ditolak sebelum aplikasi berjalan.

Sebelum menjalankan versi baru:

```powershell
python -m app.migrate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

`app.migrate` meng-upgrade tabel domain dan checkpoint. Versi domain tersimpan
di `schema_migrations`: v1 merupakan baseline domain termasuk kompatibilitas
SQLite/PostgreSQL lama; v2 menambah `workflow_steps` dan `api_rate_limits`.
V3 memperbaiki kolom `insertion_order` yang belum ada pada database legacy
yang sudah tercatat v1/v2. PostgreSQL memakai identity untuk mengisi baris lama
dan menghasilkan urutan untuk insert berikutnya. Definisi migrasi
dibekukan, bukan mengikuti model terbaru. Migrasi bersifat aditif dan bisa diulang.
Proses production memeriksa versi tanpa menjalankan DDL. Development/test tetap
memigrasikan otomatis. Buat migrasi baru untuk perubahan skema berikutnya.

Migrasi checkpoint memerlukan hak DDL pada schema `GRAPH_CHECKPOINT_SCHEMA`.
Jalankan migrasi sebagai tahap deployment terpisah dari worker. PostgreSQL
advisory lock menserialkan migrasi domain. Jalankan satu job migrasi checkpoint
sebelum worker dihidupkan. Tabel RAG tetap dikelola oleh prosedur seed yang sudah
ada; lihat [[pgvector]].

## Pemulihan dan koordinasi worker

PostgreSQL memakai advisory lock satu klaim per koneksi khusus. Lock dilepas
ketika scope selesai atau proses pemilik mati. Permintaan yang tidak memperoleh
lock dalam `CLAIM_LOCK_TIMEOUT_SECONDS` menerima HTTP 409 `claim_busy`.
Recovery mencoba lock tanpa menunggu, sehingga tidak mengambil alih worker aktif.
SQLite dan memory hanya ditujukan untuk satu proses development.

Tiap langkah graph menyimpan hasil domain serta penanda penyelesaian dalam satu
transaksi. Crash sebelum commit me-rollback hasil langkah; crash setelah commit
sebelum checkpoint membaca penanda saat replay. Keputusan, evaluasi, dan audit
yang sudah commit tidak dibuat ulang. Panggilan provider sebelum commit bisa
diulang; transaksi lokal tidak menjamin exactly-once pada layanan eksternal.

Worker recovery aktif otomatis pada SQL storage. Ia memindai run pending setiap
`RECOVERY_INTERVAL_SECONDS` (default 30), paling banyak 100 klaim per putaran.
Pemrosesan ulang lewat API juga memulihkan run pending. Recovery berulang dibatasi
`MAX_RECOVERY_ATTEMPTS` (default 3) per run. Setelah batas tercapai, run menjadi
FAILED dengan `recovery_exhausted`; pengguna bisa memulai run baru dengan key baru.

Recovery hanya mengambil run `running` atau `queued`; `needs_clarification`
dan `escalated` tidak dilanjutkan otomatis. Jawaban klarifikasi, konteks, audit,
status klaim, dan run lanjutan `queued` disimpan dalam satu transaksi melalui
endpoint jawaban. Jika crash terjadi setelah commit sebelum graph dilanjutkan,
recovery memproses run `queued` tersebut. Nota pengganti tidak melewati jawaban.
Review yang belum commit kembali menunggu input admin. Backend tidak membuat
keputusan admin dari callback yang hilang. Admin mengirim ulang keputusan setelah
recovery. Review yang sudah commit tetap tersimpan satu kali.

Pemulihan manual tanpa kredensial sesi HTTP:

```powershell
python -m app.services.recovery --limit 100
```

CLI memakai konfigurasi deployment yang sama dan menutup koneksi saat selesai.
Respons JSON berisi `scanned`, `recovered`, `busy`, dan `failed`; exit code 1
menandakan ada pemulihan gagal. Endpoint admin `POST /operations/recover?limit=100`
menyediakan operasi yang sama melalui autentikasi aplikasi.

Saat shutdown, aplikasi menghentikan scan baru dan menunggu scan yang berjalan
sebelum menutup koneksi. Atur grace period host sesuai batas waktu provider dan
jumlah nota. Forced termination aman untuk data domain karena replay memakai
penanda transaksi, tetapi panggilan provider yang sedang berlangsung bisa diulang.

## Monitoring

- `GET /health`: liveness proses, tidak menyentuh dependency.
- `GET /health/ready`: HTTP 200 jika versi/tabel domain, checkpoint, dan adapter
  RAG/ML yang diaktifkan siap; HTTP 503 dengan pesan umum jika gagal. Tidak
  memanggil provider LLM atau memvalidasi API key melalui request berbayar.
- `GET /operations/metrics`: khusus admin, jumlah klaim/run per status, rata-rata
  durasi run, serta umur run aktif tertua, dibaca dari penyimpanan bersama.
- Log request memuat method, path, status, request ID tervalidasi, dan durasi.
  Log recovery mencatat klaim yang dipulihkan dan hasil batch tanpa data nota.

Hubungkan monitor deployment ke readiness. Buat alert untuk readiness 503,
kenaikan `runs_failed`, `oldest_active_run_seconds` yang melewati durasi normal,
dan log recovery gagal. Pengiriman alert memerlukan layanan monitoring deployment;
tidak ada pesan yang dikirim ke akun eksternal oleh perubahan ini.

## Batas API dan pagination

Default batas: 10 nota per klaim, 10 MiB per nota, 25 MiB gabungan file,
26 MiB seluruh request termasuk multipart. Penggantian nota ikut batas jumlah
nota klaim. ASGI middleware menghitung byte aktual, termasuk request tanpa
Content-Length; file terlalu besar menerima 413, jumlah file berlebih 422.
Samakan batas request reverse proxy dengan `MAX_REQUEST_BYTES`.

Semua mutasi klaim/review dibatasi 60 request per identitas terautentikasi per
window 60 detik. Respons 429 memuat `Retry-After`. PostgreSQL menyimpan counter
bersama antar-worker; data counter lama dibersihkan otomatis. Fixed window
memungkinkan burst di batas dua window. Konfigurasikan batas ingress untuk
traffic tidak terautentikasi; counter aplikasi berjalan setelah autentikasi.

`GET /claims` dan `GET /reviews` menerima `limit` (1–200, default 100) serta
`offset` (default 0). Respons tetap memiliki `items` dan `total`, ditambah
`limit`/`offset`. `total` adalah jumlah seluruh hasil terfilter. Klaim mendukung
`employee_id`, `status`, `period_from`, dan `period_to` (tanggal inklusif).
Identitas member selalu membatasi hasil ke klaim miliknya.

Klien perlu mengambil halaman berikutnya sampai `offset + items.length >= total`.
Frontend saat ini kompatibel dengan respons tambahan, tetapi tampilan yang hanya
mengambil satu halaman akan menampilkan paling banyak 100 hasil. Pagination UI
merupakan pekerjaan frontend terpisah.

Laporan membaca klaim serta keputusan/run/sinyal dalam batch 200, bukan query per
klaim. CSV menghasilkan chunk per batch dan menetralkan awalan formula pada
teks. Hasil merupakan tampilan data berjalan, bukan snapshot transaksi panjang.
`automated_claims` hanya menghitung klaim final dengan keputusan agent; pending
tidak dihitung selesai otomatis. Estimasi waktu tersimpan masih memakai asumsi
5 menit per klaim otomatis, bukan hasil pengukuran waktu kerja manusia.

## Backup, restore, dan retensi

Backup harus menyertakan domain, `schema_migrations`, `workflow_steps`, schema
checkpoint, serta schema RAG. Jangan memulihkan hanya checkpoint atau hanya tabel
domain dari waktu yang berbeda. Nota pada mode SQL tersimpan dalam `file_storage`
dan ikut backup database. Lindungi akses dan penyimpanan backup sesuai kebijakan
organisasi. Uji restore di database terpisah, jalankan readiness, lalu replay
klaim uji sebelum mengarahkan traffic.

Tidak ada penghapusan otomatis klaim/nota/audit/checkpoint karena masa retensi
belum ditentukan. `workflow_steps` harus tetap ada selama checkpoint/run masih
bisa direplay. Menentukan retensi dan penyimpanan backup adalah konfigurasi
operasional organisasi, bukan default yang menghapus data diam-diam.

## Pengujian

```powershell
$env:TEST_POSTGRES_URL='postgresql+psycopg://tera_test:test_only@127.0.0.1:5432/postgres'
python -m pytest -q -ra
```

Fixture membuat dan menghapus database `tera_test_<uuid>` miliknya sendiri.
Tes mencakup proses mati sungguhan, transaksi node, replay, dua proses worker,
klarifikasi/review terputus, migrasi berulang/legacy, pagination/ownership,
rate limit bersama, upload chunked, readiness, dan konfigurasi production.
Tes LLM memakai mock. Tes pgvector memerlukan extension vector; CI memakai
image [pgvector resmi](https://github.com/pgvector/pgvector#docker) untuk PostgreSQL 18.

Rancangan replay mengacu pada [persistence LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence)
dan transaksi [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/connections.html).
