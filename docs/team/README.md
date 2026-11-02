> Rencana ini sudah digantikan setelah koreksi pembagian tim. Pemilik menangani backend; Sheren dan Nisa menangani frontend. Ikuti [README frontend](../../frontend/README.md) sebagai acuan terbaru.

# Panduan kerja tim Tera

Tanggal peninjauan: 14 Oktober 2026. Anggota tim: **Sheren dan Nisa**. Usulan awal: Sheren menangani backend/laporan, Nisa menangani frontend/QA. Kemampuan dan waktu luang masing-masing belum diberikan; sesuaikan pembagian peran dan estimasi bersama sebelum mulai.

Tera adalah prototipe pemrosesan reimbursement: karyawan mengunggah nota, agent membaca dan memeriksa kebijakan, lalu klaim disetujui, ditolak, diminta klarifikasi, atau diteruskan ke reviewer.

## Mulai dari sini

1. Baca [aturan kontribusi](../../CONTRIBUTING.md), [README proyek](../../README.md), dan [ringkasan arsitektur](../architecture/overview.md).
2. Baca [project plan](PROJECT-PLAN.md) untuk urutan, dependensi, dan kriteria selesai.
3. Sheren mengikuti [README backend dan laporan](teman-1-backend/README.md).
4. Nisa mengikuti [README frontend dan QA](teman-2-frontend/README.md).
5. Pemilik proyek menyiapkan baseline Git yang dapat di-clone, meninjau kontrak, dan menggabungkan PR.

## Kondisi proyek yang ditemukan

Status di bawah berasal dari struktur, kode, spesifikasi, dan tes yang dibaca pada working tree lokal. "Sudah ada" berarti implementasinya ditemukan; bukan pernyataan bahwa seluruh alur sudah diuji ulang atau siap produksi.

| Bagian | Kondisi saat ditinjau | Implikasi tugas |
| --- | --- | --- |
| Intake dan ekstraksi | Upload, pemeriksaan file, mock/live provider, retry dan klarifikasi sudah ada | Pertahankan; uji regresi saat integrasi |
| Validasi dan keputusan | Validasi deterministik, kebijakan, duplikat, anomali, keputusan dan alasan sudah ada | Jangan membangun ulang pipeline |
| Orkestrasi | LangGraph dengan checkpoint dan resume klarifikasi/review sudah ada | Perubahan graph tetap dikoordinasikan pemilik |
| Penyimpanan | Memory, SQL/PostgreSQL dan kompatibilitas SQLite sudah ada | Memory untuk onboarding; PostgreSQL diuji terpisah |
| RAG dan ML | Modul retrieval pgvector dan pelatihan anomali sintetis sudah ada | Opsional untuk onboarding; evaluasi live milik pemilik |
| Review dan audit | Antrean review, keputusan manusia, timeline dan audit sudah ada | Uji bukti, konfirmasi dan persistensi keputusan |
| Login dan kepemilikan | Implementasi Clerk, admin, pembatasan klaim dan mode demo ditemukan pada perubahan lokal | Harus masuk baseline sebelum teman mulai |
| Laporan | Summary, CSV dan halaman laporan sudah ada | Lengkapi filter, definisi metrik dan pengujian |
| Frontend | Landing, pengajuan, riwayat/detail, dashboard, review dan laporan sudah ada | Lengkapi interaksi berdasarkan API yang nyata |
| Dokumentasi | BRD/PRD/SRS/SDD dan panduan teknis sudah ada | Beberapa status/route/asumsi lama perlu diselaraskan |

Contoh perbedaan konkret: spesifikasi M8 menyebut `/reports/export.csv`, sedangkan kode menggunakan `/reports/claims.csv`. README lama menyebut laporan masih direncanakan dan identitas belum diautentikasi; working tree sudah memiliki implementasi laporan dan akses berbasis sesi.

## Pembagian tanggung jawab

| PIC | Fokus | Hasil utama |
| --- | --- | --- |
| Sheren | Backend reporting, kontrak API, tes agregasi dan CSV | Laporan benar, filter konsisten, regresi teruji |
| Nisa | Frontend laporan, konsistensi akses pengguna, QA dan bukti demo | Filter dapat dipakai, error jelas, alur pengguna terdokumentasi |
| Pemilik proyek | Baseline Git, review desain/kontrak, agent/RAG/ML, konfigurasi akun, integrasi dan keputusan deployment | Cabang acuan yang lengkap dan demo terintegrasi |

## Menjalankan proyek pertama kali

Gunakan dua terminal PowerShell. Jalankan dari root repository hasil clone.

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Untuk onboarding tanpa akun/API key, atur file lokal `backend/.env`:

```dotenv
ENVIRONMENT=development
DEMO_MODE=true
STORAGE_BACKEND=memory
PROVIDER_MODE=mock
POLICY_MODE=local
ANOMALY_MODE=rules
```

Lalu jalankan `uvicorn app.main:app --reload`. Cek `http://127.0.0.1:8000/health`; kontrak aktual tersedia di `http://127.0.0.1:8000/docs`.

Frontend, terminal kedua:

```powershell
cd frontend
pnpm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
pnpm dev
```

Pastikan `BACKEND_URL=http://127.0.0.1:8000` pada `frontend/.env`. Buka URL yang dicetak Vite. Untuk uji Clerk normal, gunakan `DEMO_MODE=false` dan ikuti [panduan login](../admin-login.md) bersama pemilik proyek.

Mode demo memaksa memory/mock/local/rules; restart backend menghapus klaim demo. Mode demo tidak membuktikan pembatasan akses normal. Jangan memakai mode ini untuk deployment publik.

## Aturan kerja bersama

- Mulai dari baseline yang ditentukan pemilik, bukan salinan folder dengan perubahan lokal yang belum dibagikan.
- Ikuti pola cabang `feat/<deskripsi>`, `fix/<deskripsi>`, atau `docs/<deskripsi>` sesuai CONTRIBUTING.
- Satu PR untuk satu tugas yang dapat ditinjau. Contoh commit: `fix(backend): correct report outcome counts`.
- Backend menjadi sumber keputusan dan hak akses. Frontend menampilkan data dan menyampaikan aksi pengguna.
- Sheren memiliki endpoint/tes laporan; Nisa memiliki client/types/frontend. Perubahan kontrak disepakati sebelum dua sisi mengimplementasikannya.
- Gunakan data sintetis. Jangan commit `.env`, token, nota asli, cache model, atau kredensial.
- Jika memakai agen pada repository ini, ikuti AGENTS.md dan gunakan CodeGraph terlebih dahulu ketika index tersedia.

## Pemeriksaan sebelum PR

Backend: `cd backend`, aktifkan virtual environment, lalu `python -m pytest`.

Frontend: `cd frontend`, lalu `pnpm test`, `pnpm check`, dan `pnpm build`.

Catat perintah, hasil aktual, serta tes yang dilewati. Tes PostgreSQL memerlukan `TEST_POSTGRES_URL` dan akun yang dapat membuat database tes terpisah; lihat fixture dan [panduan pgvector](../development/pgvector.md). Jangan mengarahkan pengujian ke database aplikasi.

Untuk perubahan UI, sertakan screenshot dan hasil pemeriksaan browser. Jangan menyalin jumlah tes dari laporan validasi lama sebagai hasil PR baru.

