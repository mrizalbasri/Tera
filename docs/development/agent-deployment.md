# Menjalankan dan memverifikasi paket deployment Tera

Paket ini mempertahankan SvelteKit 2 dengan adapter-node 5.5.7, FastAPI dan PostgreSQL. Pemilihan adapter mengikuti [dokumentasi server Node SvelteKit](https://svelte.dev/docs/kit/adapter-node). Model live tetap digunakan melalui adaptor LangChain; [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) mengatur state, branching, interrupt/resume dan recovery.

## Build dan staging

1. Siapkan PostgreSQL terpisah serta host/domain HTTPS. Tujuan hosting publik belum diberikan pada pekerjaan ini.
2. Salin `docker/backend.production.env.example` menjadi `docker/backend.production.env`, lalu isi konfigurasi sendiri. File hasil salinan diabaikan Git. Jangan menaruh secret di perintah shell atau commit.
3. Tentukan `VITE_CLERK_PUBLISHABLE_KEY` dan `FRONTEND_ORIGIN` di environment proses Compose. Publishable key adalah konfigurasi publik yang tertanam saat build; secret key Clerk tidak digunakan aplikasi ini.
4. Jalankan `docker compose -f docker/compose.app.yaml build`, lalu `docker compose -f docker/compose.app.yaml up -d`. Job migrate menyelesaikan migrasi sebelum backend berjalan. Frontend menunggu backend sehat.
5. Reverse proxy HTTPS mengarah ke frontend pada loopback port 3000. Backend loopback port 8000 dapat dipakai untuk monitor internal; jangan mengekspos database ke publik. Origin frontend, proxy, dan Clerk harus sesuai.
6. Verifikasi `/api/health/ready`, login pengguna, hak karyawan/admin, unggah, klarifikasi, review, notifikasi, pengelolaan kebijakan dan CSV. HTTP/build berhasil belum membuktikan login akun nyata atau seluruh alur production.

Image backend default memasang `requirements-runtime.txt` untuk mode kebijakan local dan anomali rules. Instalasi pengembangan `pip install -r requirements.txt` tetap menyertakan pytest dan model lokal seperti sebelumnya. Untuk RAG/ML lokal pada image, build dengan `--build-arg LOCAL_MODELS=true`, siapkan model/indeks secara eksplisit, lalu konfigurasikan mode dan cache. Volume `/app/data/local` menyimpan artefak lokal. Mengaktifkan RAG/ML tanpa model/index tidak dianggap deployment siap. Image default tidak mengunduh model saat request.

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

Pengujian JWT sintetis memeriksa otorisasi, bukan keberhasilan login browser pada akun nyata. Login/OTP diselesaikan pemilik akun di UI. Pengujian otomatis Clerk yang membutuhkan sesi memakai test instance dan token pengujian sesuai [panduan Clerk](https://clerk.com/docs/guides/development/testing/overview); jangan menyalin sesi production ke fixture.

Gunakan [panduan UAT](agent-uat.md) untuk sesi karyawan dan finance. Sesi yang belum dilakukan tidak dicatat sebagai lulus. Pembayaran, akuntansi dan approval bertingkat tetap di luar scope.
