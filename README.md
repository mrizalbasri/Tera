<a id="readme-top"></a>

<p align="center">
  <img src="frontend/static/logo.webp" alt="Logo Tera" width="100" />
</p>

<h1 align="center">Tera</h1>

<p align="center">
  <strong>AI Agent untuk Pemeriksaan Reimbursement Karyawan</strong><br />
  Membaca bukti nota, mengevaluasi kebijakan, mendeteksi sinyal risiko, memandu klarifikasi interaktif,<br />
  dan membantu tim finance mengambil keputusan yang dapat ditelusuri.
</p>

<p align="center">
  <a href="#panduan-uji-cepat">Uji Cepat</a> &bull;
  <a href="docs/README.md">Dokumentasi</a> &bull;
  <a href="docs/development/local-development.md">Jalankan Lokal</a> &bull;
  <a href="docs/architecture/overview.md">Arsitektur</a> &bull;
  <a href="CONTRIBUTING.md">Kontribusi</a> &bull;
  <a href="LICENSE">Lisensi (MIT)</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/SvelteKit-FF3E00?style=flat&logo=svelte&logoColor=white" alt="SvelteKit" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langgraph&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white" alt="TypeScript" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-2ea44f?style=flat" alt="MIT License" /></a>
</p>

---

<details>
  <summary><strong>Daftar Isi</strong></summary>
  <ol>
    <li><a href="#tentang-tera">Tentang Tera</a></li>
    <li><a href="#untuk-siapa">Untuk Siapa?</a></li>
    <li><a href="#kemampuan-utama">Kemampuan Utama</a></li>
    <li><a href="#panduan-uji-cepat">Panduan Uji Cepat</a></li>
    <li>
      <a href="#arsitektur-dan-alur-agen">Arsitektur dan Alur Agen</a>
      <ul>
        <li><a href="#alur-pemrosesan-klaim">Alur Pemrosesan Klaim</a></li>
        <li><a href="#stack-teknologi">Stack Teknologi</a></li>
        <li><a href="#struktur-repositori">Struktur Repositori</a></li>
      </ul>
    </li>
    <li>
      <a href="#cara-menjalankan-aplikasi">Cara Menjalankan Aplikasi</a>
      <ul>
        <li><a href="#prasyarat">Prasyarat</a></li>
        <li><a href="#1-jalankan-backend-fastapi">1. Jalankan Backend (FastAPI)</a></li>
        <li><a href="#2-jalankan-frontend-sveltekit">2. Jalankan Frontend (SvelteKit)</a></li>
      </ul>
    </li>
    <li><a href="#batasan-sistem-dan-mitigasi-risiko">Batasan Sistem dan Mitigasi Risiko</a></li>
    <li><a href="#pengujian-dan-validasi">Pengujian dan Validasi</a></li>
    <li><a href="#kontribusi-dan-lisensi">Kontribusi dan Lisensi</a></li>
  </ol>
</details>

---

## Tentang Tera

Pemeriksaan reimbursement melibatkan pembacaan nota, pencocokan nominal, pemeriksaan kebijakan, dan pencarian klaim duplikat. Ketika foto buram atau informasi kurang jelas, tim finance juga memerlukan tindak lanjut klarifikasi dari karyawan.

Tera menyatukan langkah-langkah tersebut dalam satu alur kerja agen yang terstruktur: unggah nota, ekstraksi data, validasi, evaluasi kebijakan, pemeriksaan risiko, hingga keputusan akhir. Klaim yang belum lengkap dapat dilanjutkan melalui klarifikasi interaktif, sedangkan kasus yang membutuhkan pertimbangan manusia diteruskan ke tim finance. Setiap klaim menyimpan bukti, temuan, dan jejak audit agar alasan di balik keputusan dapat ditelusuri.

## Untuk Siapa?

| Pengguna | Yang Dapat Dilakukan |
| --- | --- |
| **Karyawan** | Mengunggah nota lewat antarmuka percakapan (`/pengajuan`), memantau riwayat & status klaim (`/riwayat`), dan menjawab permintaan klarifikasi |
| **Tim Finance** | Memeriksa bukti nota dan memutuskan antrean review (`/reviews`), memantau ringkasan klaim (`/dashboard`), mengelola kebijakan reimbursement (`/admin/policies`), serta mengekspor laporan CSV (`/reports`) |

## Kemampuan Utama

- **Pembacaan nota (*Receipt Extraction*):** Ekstraksi vendor, tanggal transaksi, kategori, item, dan total nominal melalui provider *mock* atau model *vision* live beserta tingkat keyakinan (*confidence score*).
- **Pemeriksaan klaim berlapis:** Validasi kelengkapan dan konsistensi data, evaluasi kepatuhan kebijakan, deteksi indikasi duplikasi, serta penilaian anomali.
- **Tindak lanjut adaptif (*Human-in-the-Loop*):** Menjeda eksekusi pada *checkpoint* (`needs_clarification` atau `escalated`) dan melanjutkan proses otomatis dengan konteks tersimpan setelah karyawan menjawab klarifikasi atau tim finance memberikan keputusan.
- **Jejak pemeriksaan (*Audit Trail*):** Pencatatan bukti, alasan keputusan, riwayat pemrosesan per tahap (*step trace*), dan notifikasi status.
- **Manajemen kebijakan & laporan:** Pengelolaan kebijakan berversi dengan tanggal efektif serta ringkasan laporan dan ekspor CSV.
- **Integrasi AI lanjutan opsional:** Retrieval kebijakan berbasis vektor (`pgvector` + `SentenceTransformers` + *cross-encoder reranker* opsional) dan deteksi anomali berbasis *machine learning* (`Isolation Forest`).

---

## Panduan Uji Cepat

Seluruh alur aplikasi dapat diuji langsung melalui antarmuka web menggunakan akun evaluasi bawaan:

### 1. Akun Evaluasi Bawaan

Pada halaman `/login`, gunakan salah satu kredensial berikut:

| Peran Pengguna | Email Login | Password | Akses Halaman Utama |
| --- | --- | --- | --- |
| **Karyawan** | `karyawan@tera.id` | `demo123` | `/pengajuan`, `/riwayat`, `/claims/{id}` |
| **Tim Finance** | `finance@tera.id` | `demo123` | `/reviews`, `/dashboard`, `/reports`, `/admin/policies`, `/admin/claims`, `/admin/checkpoints` |

> [!NOTE]
> **Mode Demo Lokal:** Jika backend dijalankan dengan `DEMO_MODE=true` dan `ENVIRONMENT=development` di `backend/.env`, aplikasi mengaktifkan sesi peninjau otomatis (`demo-reviewer`) menggunakan penyimpanan *in-memory* dan provider *mock* tanpa memerlukan API key eksternal.

### 2. Skenario Pengujian

1. **Pengajuan & Pemeriksaan Klaim (`/pengajuan`):**
   - Masuk sebagai **Karyawan** (`karyawan@tera.id` / `demo123`), unggah gambar nota pada antarmuka percakapan, lalu kirim klaim.
   - Amati tahapan pembacaan nota, hasil ekstraksi field, evaluasi kebijakan perusahaan, serta status keputusan beserta alasannya.
2. **Klarifikasi Interaktif:**
   - Pada klaim dengan informasi yang belum lengkap atau meragukan (status `Perlu Klarifikasi`), kirim jawaban klarifikasi atau bukti tambahan langsung pada ruang percakapan/detail klaim.
   - Tera akan melanjutkan *checkpoint* workflow dan memperbarui hasil pemeriksaan tanpa kehilangan riwayat sebelumnya.
3. **Eskalasi & Review Tim Finance (`/reviews`):**
   - Masuk sebagai **Tim Finance** (`finance@tera.id` / `demo123`), buka antrean review, dan pilih klaim yang dieskalasi.
   - Periksa gambar nota (mendukung *zoom* & rotasi), hasil ekstraksi, temuan kebijakan, serta sinyal risiko/anomali, lalu catat keputusan **Setujui** atau **Tolak** beserta alasannya.

---

## Arsitektur dan Alur Agen

Browser mengakses antarmuka **SvelteKit**, yang meneruskan permintaan `/api` ke backend **FastAPI**. `ClaimProcessingService` mengoordinasikan eksekusi node pada **LangGraph**, menyimpan rekaman domain serta peristiwa audit ke **PostgreSQL**, dan mengelola *checkpoint* untuk klaim yang menunggu tindak lanjut manusia.

<p align="center">
  <img src="docs/diagrams/architecture.svg" alt="Diagram Arsitektur Sistem Tera" width="760" />
</p>

### Alur Pemrosesan Klaim

<p align="center">
  <img src="docs/diagrams/flow-claim-processing.svg" alt="Diagram Alur Pemrosesan Klaim Tera" width="760" />
</p>

Diagram lengkap lainnya tersedia di folder [`docs/diagrams/`](docs/diagrams/):
- [Arsitektur Sistem (`architecture.svg`)](docs/diagrams/architecture.svg)
- [Alur Pemrosesan Klaim (`flow-claim-processing.svg`)](docs/diagrams/flow-claim-processing.svg)
- [Siklus Hidup Status Klaim (`state-claim-lifecycle.svg`)](docs/diagrams/state-claim-lifecycle.svg)
- [Skema Basis Data / ERD (`erd.svg`)](docs/diagrams/erd.svg)

### Stack Teknologi

| Bagian | Teknologi |
| --- | --- |
| **Antarmuka Web** | Svelte 5, SvelteKit, TypeScript, Vite |
| **API & Kontrak Data** | Python, FastAPI, Pydantic |
| **Orkestrasi Agen & LLM** | LangGraph, LangChain, OpenAI-compatible Vision API (mode *mock* & *live*) |
| **Penyimpanan & Checkpoint** | SQLAlchemy, PostgreSQL, LangGraph Checkpoint (`langgraph` schema) |
| **RAG Kebijakan (Opsional)** | PostgreSQL `pgvector`, `SentenceTransformers`, Cross-Encoder Reranker |
| **Anomali ML (Opsional)** | `scikit-learn` (Isolation Forest) |
| **Autentikasi & Keamanan** | Native Auth JWT (HMAC-SHA256), `HttpOnly` Cookie, Role-Based Access Control (`member` / `admin`) |
| **Pengujian & Kualitas Kode** | `pytest`, `Vitest`, `svelte-check`, `Ruff` |
| **Lisensi** | [MIT License](LICENSE) |

### Struktur Repositori

```text
backend/   Layanan API FastAPI, workflow LangGraph, integrasi RAG/ML, repository SQL/memory, dan pengujian pytest
frontend/  Aplikasi web SvelteKit, komponen antarmuka, proxy server /api, dan pengujian Vitest
data/      Skema data dan sampel nota sintetis untuk evaluasi
docker/    Konfigurasi kontainer pendukung pengembangan
docs/      Dokumentasi arsitektur, diagram (SVG/Mermaid), spesifikasi SDLC, dan laporan validasi
LICENSE    Berkas lisensi open-source proyek (MIT License)
```

---

## Cara Menjalankan Aplikasi

Panduan lengkap konfigurasi dan arsitektur tersedia di [Dokumentasi Pengembangan Lokal](docs/development/local-development.md).

### Prasyarat

- **Python 3.11+**
- **Node.js 18+** & **pnpm**
- **PostgreSQL** (opsional; hanya jika menggunakan mode penyimpanan SQL)

### 1. Jalankan Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Opsional: set DEMO_MODE=true dan ENVIRONMENT=development di backend/.env untuk mode demo instan tanpa database/API key eksternal.
uvicorn app.main:app --reload
```

### 2. Jalankan Frontend (SvelteKit)

Buka terminal baru dari root repositori:

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env
pnpm dev
```

Setelah kedua server aktif:
- **Aplikasi Web:** `http://localhost:5173`
- **Dokumentasi OpenAPI / Swagger:** `http://127.0.0.1:8000/docs`
- **Health Check Backend:** `http://127.0.0.1:8000/health`

> [!TIP]
> Data pada mode penyimpanan *memory* bersifat sementara dan akan direset saat backend dimulai ulang. Untuk penyimpanan persisten PostgreSQL, aktivasi RAG `pgvector`, atau pelatihan model anomali ML, ikuti panduan pada tabel navigasi di bawah.

### Navigasi Dokumentasi

| Kebutuhan | Panduan |
| --- | --- |
| Konfigurasi lengkap `.env` & penyimpanan SQL | [Pengembangan lokal](docs/development/local-development.md) |
| Mengatur login, peran pengguna, dan mode demo | [Autentikasi & akses pengguna](docs/admin-login.md) |
| Memahami alur kerja dan batas modul agen | [Alur agen](docs/architecture/agent-flow.md) &bull; [Modul agen](docs/architecture/agent-modules.md) |
| Mengaktifkan PostgreSQL & RAG `pgvector` | [Panduan pgvector](docs/development/pgvector.md) |
| Melatih & mengaktifkan skor anomali ML | [Panduan ML anomaly](docs/development/ml-anomaly.md) |
| Menyiapkan deployment & operasional | [Deployment agen](docs/development/agent-deployment.md) &bull; [Operasional backend](docs/development/backend-operations.md) |
| Menelusuri dokumen SDLC (BRD, PRD, SRS, SDD, DB) | [Indeks dokumentasi](docs/README.md) |

---

## Batasan Sistem dan Mitigasi Risiko

### 1. Mitigasi Halusinasi AI & Konsistensi Keputusan
- **Keputusan Deterministik di Backend:** Model *vision*/LLM hanya bertugas mengekstrak field dari gambar nota beserta tingkat keyakinannya (*confidence*). Evaluasi kepatuhan kebijakan, perhitungan batas nominal, dan penetapan status klaim dijalankan secara deterministik oleh layanan backend—model AI tidak diizinkan membuat aturan kebijakan sendiri atau menyetujui klaim secara sepihak.
- **Penanganan Ambiguitas & Kegagalan Ekstraksi:** Jika hasil ekstraksi tidak lengkap, nominal tidak konsisten, atau tingkat keyakinan di bawah ambang batas, klaim otomatis diarahkan ke status `needs_clarification` (meminta konfirmasi karyawan) atau `escalated` (diteruskan ke tim finance).
- **Fallback Terkontrol:** Kegagalan pemanggilan provider eksternal, indeks RAG, atau artefak model ML ditangani dengan batas *retry* dan *fallback* aman ke evaluator aturan lokal yang tercatat di jejak audit.

### 2. Mitigasi Kebocoran Data & Keamanan Privasi
- **Perlindungan Batas Keluar (*Outbound Privacy Boundary*):** Pembuatan pesan multimodal dan *masking* informasi sensitif dikelola secara terpusat di `backend/app/integrations/llm_prompt.py` sebelum dikirim ke provider model.
- **Isolasi State Checkpoint:** *Checkpoint* LangGraph hanya menyimpan identitas rekaman, versi pipeline, dan tahapan kontrol. Byte gambar nota, kredensial, dan teks bebas jawaban pengguna disimpan terpisah di luar *state checkpoint*.
- **Otorisasi Berbasis Peran:** Sesi pengguna dilindungi dengan JWT bertanda tangan HMAC-SHA256 pada cookie `HttpOnly`. Penentuan peran (`member` atau `admin`) selalu dievaluasi oleh backend, dan mode demo dilarang aktif ketika `ENVIRONMENT=production`.
- **Data Sintetis:** Seluruh contoh pengujian di repositori menggunakan data sintetis atau anonim. Jangan pernah melakukan *commit* nota transaksi asli, data pribadi (PII), kredensial, atau file `.env`.

### 3. Batasan Ruang Lingkup Sistem (*System Boundaries*)
- **Persetujuan Administratif (Bukan Pencairan Bank):** Status klaim `approved` menandakan klaim telah disetujui dalam alur pemeriksaan reimbursement; transfer dana perbankan (*payment disbursement*), payroll, perpajakan, dan penjurnalan ERP/akuntansi eksternal berada di luar ruang lingkup sistem.
- **Sinyal Risiko sebagai Pendukung Keputusan:** Indikasi duplikasi dan skor anomali berfungsi sebagai sinyal bantu bagi tim finance untuk memprioritaskan pemeriksaan bukti, bukan penentu tunggal terjadinya kecurangan (*fraud*).
- **Lingkup Organisasi & Hirarki Persetujuan:** Sistem dirancang untuk operasional satu organisasi dengan dua peran pengguna (`member` untuk karyawan dan `admin` untuk tim finance), tanpa *multi-tenancy* lintas perusahaan maupun persetujuan berjenjang multi-level (*multi-tier approval*).
- **Kualitas Bukti Dokumen:** Akurasi pembacaan field bergantung pada keterbacaan foto/dokumen nota yang diunggah; bukti yang buram atau terpotong akan dialihkan ke alur klarifikasi atau review manual.

---

## Pengujian dan Validasi

Kualitas kode dan keandalan alur agen diverifikasi melalui rangkaian pengujian otomatis serta evaluasi terukur:

- **Backend (`pytest`):** Menguji kontrak API, alur node LangGraph, *checkpoint* & *resume* klarifikasi/review, deteksi duplikasi, skor anomali, RAG kebijakan, serta batas keamanan autentikasi.
- **Frontend (`Vitest` & `svelte-check`):** Menguji komponen antarmuka, transportasi API, alur pengajuan/klarifikasi, dan pemeriksaan tipe TypeScript/Svelte.
- **Dokumentasi Validasi & Evaluasi:**
  - [Rencana Pengujian Kesiapan Agen](docs/development/agent-readiness-test-plan.md)
  - [Catatan Validasi Kesiapan Agen](docs/development/agent-readiness-validation-2026-10-23.md)
  - [Verifikasi Kesiapan Produksi](docs/development/production-follow-through-2026-10-24.md)
  - [Evaluasi Konsistensi OCR & Normalisasi Nominal Nota](docs/development/receipt-ocr-evaluation-results-2026-10-17.md)
  - [Panduan Uji Penerimaan Pengguna (UAT)](docs/development/agent-uat.md)

---

## Kontribusi dan Lisensi

Baca [CONTRIBUTING.md](CONTRIBUTING.md) sebelum membuat *branch* atau *commit*. Gunakan format *Conventional Commits* dan jalankan pemeriksaan kualitas kode (`pytest`, `pnpm check`, `pnpm test`) sebelum mengajukan perubahan. Folder `docs/` juga dapat dibuka langsung sebagai *vault* Obsidian melalui [Indeks Dokumentasi](docs/README.md).

Proyek **Tera** dilisensikan di bawah **[MIT License](LICENSE)** (Hak Cipta &copy; 2026 M. Rizal Basri). Lisensi pustaka dan komponen pihak ketiga yang digunakan mengikuti ketentuan masing-masing pemiliknya.

<p align="right">(<a href="#readme-top">kembali ke atas &uarr;</a>)</p>
