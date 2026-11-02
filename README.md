<p align="center">
  <img src="frontend/static/logo.webp" alt="Logo Tera" width="100" />
</p>

<h1 align="center">Tera</h1>

<p align="center">Agent reimbursement untuk membaca nota, memeriksa kebijakan,<br />dan membantu tim finance mengambil keputusan yang dapat ditelusuri.</p>

<p align="center"><a href="docs/README.md">Dokumentasi</a> · <a href="docs/development/local-development.md">Jalankan lokal</a> · <a href="docs/architecture/overview.md">Arsitektur</a> · <a href="CONTRIBUTING.md">Kontribusi</a></p>

![SvelteKit](https://img.shields.io/badge/SvelteKit-FF3E00?style=flat&logo=svelte&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langgraph&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)

## Tentang Tera

Pemeriksaan reimbursement melibatkan pembacaan nota, pencocokan nominal,
pemeriksaan kebijakan, dan pencarian klaim duplikat. Informasi yang kurang jelas
juga memerlukan tindak lanjut dari karyawan.

Tera menghubungkan langkah-langkah tersebut dalam satu alur: unggah nota,
ekstraksi data, validasi, evaluasi kebijakan, pemeriksaan risiko, lalu keputusan.
Klaim dapat dilanjutkan dengan klarifikasi atau diteruskan ke reviewer.
Bukti, temuan, dan alasan keputusan tersedia untuk ditelusuri.

## Untuk siapa?

| Pengguna | Yang dapat dilakukan |
| --- | --- |
| Karyawan | Mengunggah nota, mengikuti status klaim, dan menjawab klarifikasi |
| Finance / reviewer | Memeriksa bukti dan temuan, lalu menyetujui atau menolak dengan alasan |
| Admin | Mengakses antrean review, mengelola kebijakan, dan mengekspor laporan CSV |

## Kemampuan utama

- **Pembacaan nota:** ekstraksi vendor, tanggal, dan nominal melalui provider mock atau model vision.
- **Pemeriksaan klaim:** validasi data, evaluasi kebijakan, serta sinyal duplikasi dan anomali.
- **Tindak lanjut:** klarifikasi kepada karyawan dan eskalasi ke reviewer.
- **Jejak pemeriksaan:** bukti, alasan keputusan, riwayat pemrosesan, dan notifikasi.
- **Kebijakan dan laporan:** versi kebijakan dengan tanggal berlaku serta laporan dan ekspor CSV.
- **Integrasi opsional:** retrieval kebijakan berbasis pgvector dan skor anomali Isolation Forest.

Sinyal risiko membantu pemeriksaan; sinyal tersebut bukan bukti kecurangan.
Persetujuan klaim juga tidak berarti pembayaran sudah dilakukan.

## Mulai dari sini

| Kebutuhan | Panduan |
| --- | --- |
| Mencoba aplikasi di komputer sendiri | [Pengembangan lokal](docs/development/local-development.md) |
| Mengatur login, peran, dan mode demo | [Akses pengguna](docs/admin-login.md) |
| Memahami alur dan batas modul agent | [Alur agent](docs/architecture/agent-flow.md) · [Modul agent](docs/architecture/agent-modules.md) |
| Menyiapkan deployment | [Deployment](docs/development/agent-deployment.md) · [Operasional backend](docs/development/backend-operations.md) |
| Menemukan requirements dan dokumen teknis | [Indeks dokumentasi](docs/README.md) |
| Berkontribusi | [Kontribusi](CONTRIBUTING.md) · [Panduan tugas frontend](frontend/README.md) |

Mode demo lokal menggunakan penyimpanan memory dan provider mock tanpa API key
atau akun Clerk. Aktifkan `DEMO_MODE=true` dan `ENVIRONMENT=development` di
`backend/.env`, lalu ikuti panduan lokal untuk menjalankan kedua server.
Data demo bersifat sementara dan hilang saat backend direstart.

Setelah server berjalan, buka [aplikasi lokal](http://localhost:5173) dan
[referensi API lokal](http://127.0.0.1:8000/docs). URL deployment publik belum
dicantumkan di repository.

## Arsitektur dan teknologi

Browser mengakses SvelteKit, yang meneruskan permintaan `/api` ke FastAPI.
Service menjalankan workflow LangGraph; repository menyimpan klaim dan bukti,
sementara audit mencatat peristiwa pemrosesan.

| Bagian | Teknologi |
| --- | --- |
| Antarmuka | Svelte 5, SvelteKit, TypeScript, Vite |
| API dan kontrak | Python, FastAPI, Pydantic |
| Agent dan ekstraksi | LangChain, LangGraph, provider vision OpenAI-compatible |
| Penyimpanan | SQLAlchemy, PostgreSQL, checkpoint LangGraph |
| Retrieval dan anomali opsional | pgvector, SentenceTransformers, scikit-learn |
| Autentikasi | Clerk |
| Pengujian | pytest, Vitest, svelte-check |

```text
backend/   API, workflow agent, service, dan pengujian
frontend/  Antarmuka web dan transport API
data/      Skema dan sampel sintetis
docs/      Requirements, arsitektur, panduan, dan catatan validasi
```

Lihat [arsitektur sistem](docs/architecture/overview.md) untuk penjelasan komponen.

## Validasi dan batas kesiapan

Hasil pemeriksaan dicatat dengan tanggal dan ruang lingkupnya:

- [Rencana pengujian](docs/development/agent-readiness-test-plan.md)
- [Catatan validasi 23 Oktober 2026](docs/development/agent-readiness-validation-2026-10-23.md)
- [Verifikasi lanjutan 24 Oktober 2026](docs/development/production-follow-through-2026-10-24.md)
- [Panduan uji penerimaan pengguna](docs/development/agent-uat.md)

Catatan tersebut merupakan bukti pada waktu pengujian, bukan status CI terkini.
Deployment publik, verifikasi browser dengan akun nyata, dan penerimaan pengguna
tetap perlu dibuktikan. Hasil lokal atau sintetis tidak membuktikan akurasi
produksi, penghematan biaya, maupun pembayaran reimbursement.

## Kontribusi dan keamanan data

Baca [CONTRIBUTING.md](CONTRIBUTING.md) sebelum membuat branch atau commit.
Gunakan Conventional Commits dan jalankan pemeriksaan yang sesuai perubahan.

Gunakan data sintetis atau anonim. Jangan commit nota asli, informasi pribadi,
kredensial, atau file `.env`; simpan contoh konfigurasi dengan nilai placeholder.

Folder `docs/` juga dapat dibuka sebagai vault Obsidian. Mulai dari
[indeks dokumentasi](docs/README.md).
