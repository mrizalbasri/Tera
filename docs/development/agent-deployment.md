# Menjalankan dan memverifikasi paket deployment Tera

Paket ini mempertahankan SvelteKit 2 dengan adapter-node 5.5.7, FastAPI dan PostgreSQL. Pemilihan adapter mengikuti [dokumentasi server Node SvelteKit](https://svelte.dev/docs/kit/adapter-node). Model live tetap digunakan melalui adaptor LangChain; [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) mengatur state, branching, interrupt/resume dan recovery.

## Build dan staging

1. Siapkan PostgreSQL terpisah serta host/domain HTTPS. Tujuan hosting publik belum diberikan pada pekerjaan ini.
2. Salin `docker/backend.production.env.example` menjadi `docker/backend.production.env`, lalu isi konfigurasi sendiri. File hasil salinan diabaikan Git. Jangan menaruh secret di perintah shell atau commit.
3. Tentukan `FRONTEND_ORIGIN` dan variabel backend di environment proses Compose.
4. Jalankan `docker compose -f docker/compose.app.yaml build`, lalu `docker compose -f docker/compose.app.yaml up -d`. Job migrate menyelesaikan migrasi sebelum backend berjalan. Frontend menunggu backend sehat.
5. Reverse proxy HTTPS mengarah ke frontend pada loopback port 3000. Backend loopback port 8000 dapat dipakai untuk monitor internal; jangan mengekspos database ke publik. Origin frontend dan proxy harus sesuai.
6. Verifikasi `/api/health/ready`, login pengguna, hak karyawan/admin, unggah, klarifikasi, review, notifikasi, pengelolaan kebijakan dan CSV. HTTP/build berhasil belum membuktikan login akun nyata atau seluruh alur production.

Image backend memasang `requirements-runtime.txt`. Build argument `LOCAL_MODELS=true` memasang dependensi RAG/ML lokal; siapkan indeks kebijakan secara eksplisit sebelum mengaktifkan RAG. Instalasi pengembangan `pip install -r requirements.txt` menyertakan pytest dan dependensi model tersebut. Volume `/app/data/local` menyimpan artefak lokal. Mengaktifkan RAG/ML tanpa model/index tidak dianggap deployment siap. Image default tidak mengunduh model saat request.

## OCR lokal sebelum model AI

Mode ini bersifat opt-in untuk backend live. Default aplikasi tetap `vision` agar
deployment yang sudah berjalan tidak berubah tanpa pemasangan dependensi.
Contoh environment Docker mengaktifkan `ocr_first` untuk deployment baru.

Untuk instalasi tanpa Docker, dari `backend/` dengan venv aktif:

```powershell
python -m pip install -r requirements-local-ocr.txt
python -m scripts.verify_local_ocr
```

Kemudian atur environment lokal/deployment dan restart backend:

```dotenv
PROVIDER_MODE=live
RECEIPT_EXTRACTION_MODE=ocr_first
OCR_CPU_THREADS=2
OCR_MIN_CONFIDENCE=0.9
PROVIDER_FALLBACK=none
```

Tetap isi `LLM_BASE_URL`, `LLM_MODEL`, dan `LLM_API_KEY` melalui pengelolaan secret
deployment untuk fallback. Implementasi tidak mengganti provider menjadi Gemini
secara otomatis; provider harus mendukung kontrak Chat Completions yang sudah ada.
Jangan menaruh key di repo.

- Docker memasang `requirements-local-ocr.txt` dengan `LOCAL_OCR=true` (default).
  RapidOCR 3.10.0 menyertakan model ONNX dalam paket; build memeriksa model dan
  mencoba inferensi. Startup menghangatkan ulang engine di proses service;
  bobot tidak diunduh saat upload. Setiap proses memiliki engine sendiri.
- `/health/ready` memeriksa kesiapan OCR jika mode ini aktif. Dependensi/model
  yang hilang membuat startup/readiness gagal, bukan diam-diam memakai AI.
- Foto JPG/PNG dibatasi dimensinya, dikoreksi orientasinya, lalu dibaca lokal.
  Satu engine memproses secara serial dengan thread CPU terbatas.
- Jalur tanpa AI sengaja sempit: vendor dan tanggal jelas, total IDR eksplisit,
  baris barang berbentuk `nama 2 x 25.000 50.000`, kategori dikenali, serta
  subtotal/pajak/diskon dan seluruh nominal cocok. Baris yang tidak dikenal
  tidak boleh diabaikan, terutama bukti barang yang dilarang.
- Teks yang jelas tetapi layout-nya belum didukung dikirim ke AI sebagai teks
  yang telah dimasking. Bacaan lemah/kosong memakai jalur vision lama.
  `LLM_IMAGE_PRIVACY_MODE=block` tetap melarang fallback eksternal.
- Cache maksimal 32 hasil OCR berupa baris teks berada hanya di memori proses,
  dengan TTL 120 detik yang diperiksa saat akses. Tidak ada cache gambar atau
  teks mentah di database, checkpoint, maupun log.
- PDF belum dirasterisasi oleh OCR lokal; perilaku live sebelumnya tetap berlaku.
  Skor OCR bukan angka akurasi yang sudah dikalibrasi. Validasi barang, kebijakan,
  nominal, dan keputusan backend tetap dijalankan.

`verify_local_ocr` membuat tiga varian nota sintetis, menguji inferensi CPU
sungguhan sampai hasil nominal/rincian, dan melaporkan waktu pemuatan awal,
pembacaan hangat, cache, serta nol panggilan model eksternal. Ini bukan pengukuran
akurasi nota nyata atau SLA produksi. Uji staging dengan fixture aman yang mewakili
nota pengguna dan CPU/RAM target sebelum rollout.

Rollback: set `RECEIPT_EXTRACTION_MODE=vision` dan restart backend. Library OCR
boleh tetap terpasang. Proses HTTP masih sinkron: nota yang membutuhkan fallback
AI tetap dapat mengalami timeout. Background queue/worker dan polling status
adalah pekerjaan terpisah, bukan bagian perubahan ini.

## Evaluasi offline dan live

Dari `backend/`, gunakan interpreter venv:

```powershell
python -m app.evaluate_agent --output data/local/evaluation/agent-readiness.json
python -m scripts.verify_live_agent --output data/local/evaluation/live-agent.json
```

Evaluator pertama menggunakan adaptor sintetis dan graph sesungguhnya. Evaluator kedua mengirim tepat satu nota PNG sintetis ke provider yang sudah dikonfigurasi, tanpa fallback mock, dengan storage memory terisolasi. Ia tidak mengubah `.env` atau database aplikasi. Model diminta membaca total Rp60.000; hasil diuji sampai keputusan dan usage bila provider menyediakannya. `live_verified=true` berlaku untuk skenario itu saja; bukan angka akurasi umum. Tidak tersedia biaya aktual tanpa tarif yang ditetapkan.

Hasil mencatat mode dan versi. `working_tree_dirty` pada evaluator offline menunjukkan adanya perubahan lokal, termasuk perubahan pengguna yang tidak termasuk implementasi ini. Jangan mengubah label sintetis atau mengabaikan error untuk memperbesar skor.

## Backup dan restore

Backup production harus mencakup seluruh database, termasuk schema domain, checkpoint, RAG, nota dan `operational_records` pada migrasi v4. Simpan backup dengan akses terbatas dan tentukan retensi organisasi. Jangan memulihkan sebagian schema dari waktu yang berbeda.

Alat berikut menguji mekanisme dump/restore tanpa menyentuh database aplikasi:

```powershell
$env:TEST_POSTGRES_URL='postgresql+psycopg://tera_test:test_only@127.0.0.1:55440/postgres'
python -m scripts.verify_restore --pg-bin 'C:/Program Files/PostgreSQL/18/bin'
```

Alat membuat dua database dengan nama acak `tera_restore_<uuid>_*` pada server tes, menyimpan klaim/nota/keputusan/checkpoint/notifikasi sintetis, baseline beserta kebijakan custom terbit dan probe schema vector, menjalankan pg_dump/pg_restore, memeriksa versi kebijakan efektif/readiness/replay, lalu hanya menghapus database yang dibuatnya sendiri. Tes ini membuktikan prosedur pada fixture tersebut; backup production nyata tetap harus dijadwalkan dan diuji sesuai lingkungan operasional.

## Demo lokal

Untuk QA, jalankan backend terpisah dengan `DEMO_MODE=true` pada loopback dan frontend yang menunjuk ke backend tersebut. Jalankan `python -m scripts.seed_workspace_demo --base-url http://127.0.0.1:5175/api` melalui proxy frontend; port harus sesuai origin frontend yang diizinkan backend. Alat hanya menerima loopback dan memastikan API melaporkan demo_mode=true sebelum membuat fixture. Tiga nota secara jelas bertanda sintetis. Mode demo memakai memory/mock, hilang setelah restart, dan ditolak pada ENVIRONMENT=production.

## Login dan UAT

Pengujian JWT sintetis memeriksa otorisasi, bukan keberhasilan login browser pada akun nyata. Login diselesaikan pengguna melalui form login di UI.

Gunakan [panduan UAT](agent-uat.md) untuk sesi karyawan dan finance. Sesi yang belum dilakukan tidak dicatat sebagai lulus. Pembayaran, akuntansi dan approval bertingkat tetap di luar scope.
