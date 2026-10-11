# PRD (Product Requirements Document) — Expense Agent

> **Fungsi dokumen:** mendefinisikan **produk** yang akan dibangun — untuk siapa, fitur apa, dengan prioritas apa. Jembatan antara [[05-brd|BRD]] (bisnis) dan [[07-srs|SRS]] (spesifikasi teknis). Pembacanya: tim produk & developer.

| | |
|---|---|
| **Produk** | Expense Agent |
| **One-liner** | Untuk tim finance perusahaan distribusi dengan salesman lapangan, Expense Agent adalah AI agent yang memproses klaim reimbursement dari foto nota secara otonom — mengekstrak, memvalidasi, memutuskan, dan mendokumentasikan — sehingga manusia hanya menangani pengecualian. |
| **Versi / tanggal** | v1.0 / 2026-10-05 |
| **Status** | draft — menunggu persetujuan |

## 1. Problem Statement

Admin/finance perusahaan distribusi memeriksa ratusan nota klaim per bulan secara manual: menginput ke spreadsheet, mengecek kebijakan satu per satu, dan menanyakan ulang bila nota bermasalah. Proses ini memakan ±150 jam/bulan, hasilnya tidak konsisten, klaim ganda sulit terdeteksi, dan karyawan menunggu lama tanpa kejelasan status klaimnya.

## 2. Target User & Persona

| Persona | Deskripsi | Tujuan utama | Pain point |
|---------|-----------|--------------|------------|
| Andi — Salesman | Karyawan lapangan yang mengklaim BBM, makan, tol, hotel | Ajukan klaim cepat dan tahu status/alasan penolakannya | Kumpulkan nota fisik/kirim chat, input manual, menunggu tanpa kabar |
| Sari — Admin/Finance | Memproses ratusan klaim per bulan | Hanya menangani kasus yang benar-benar perlu ditinjau | Input manual, cek kebijakan satu per satu, hasil tidak konsisten |
| Pak Budi — Manajer/Reviewer | Menyetujui klaim bernilai besar/berisiko | Klaim berisiko ditandai lengkap dengan alasan objektif | Tidak punya dasar objektif (bukti duplikat/anomali) untuk memutuskan |
| Manajemen | Pemilik anggaran operasional | Laporan biaya & kepatuhan periodik otomatis | Data tersebar di spreadsheet, tidak real-time |

## 3. User Stories & Fitur

> Prioritas: **M** = Must, **S** = Should, **C** = Could, **W** = Won't (rilis ini). Kode FR merujuk ke [[07-srs|SRS]] §3.

| Kode | User story | Fitur terkait | Prioritas |
|------|-----------|---------------|-----------|
| US-01 | Sebagai salesman, saya ingin mengunggah foto/PDF nota lewat antarmuka web, sehingga saya tidak perlu mengantar nota atau mengisi form manual. | FR-01 | M |
| US-02 | Sebagai salesman, saya ingin sistem membaca isi nota secara otomatis (vendor, tanggal, total, item) beserta tingkat kepercayaan, sehingga saya tidak mengetik data klaim. | FR-02 | M |
| US-03 | Sebagai salesman, saya ingin diminta foto ulang dengan pesan spesifik bila nota buram, sehingga klaim saya tidak menggantung tanpa kabar. | FR-03 | M |
| US-04 | Sebagai admin, saya ingin validasi deterministik (total = jumlah item, tanggal wajar, format valid) berjalan sebelum keputusan, sehingga kesalahan data tertangkap dini. | FR-04 | M |
| US-05 | Sebagai admin, saya ingin setiap klaim diperiksa terhadap dokumen kebijakan perusahaan lewat pencarian (RAG), sehingga penegakan aturan konsisten untuk semua karyawan. | FR-05 | M |
| US-06 | Sebagai admin, saya ingin klaim ganda terdeteksi otomatis (hash gambar + kemiripan vendor/tanggal/nominal), sehingga tidak ada penggandaan klaim. | FR-06 | M |
| US-07 | Sebagai manajer, saya ingin pola klaim tidak wajar diberi skor anomali oleh model ML disertai bukti, sehingga penilaian risiko objektif dan dapat dijelaskan. | FR-07 | M |
| US-08 | Sebagai salesman, saya ingin keputusan (setujui/tandai/tolak/tanya ulang) selalu disertai alasan, sehingga saya tahu apa yang harus dilakukan berikutnya. | FR-08 | M |
| US-09 | Sebagai salesman, saya ingin agent bertanya bila nota ambigu (mis. makan untuk beberapa orang) dan menghitung ulang setelah saya menjawab, sehingga klaim tetap bisa diproses. | FR-09 | M |
| US-10 | Sebagai reviewer, saya ingin klaim bernilai besar atau kepercayaan rendah dieskalasi ke antrean review, sehingga keputusan berisiko tetap di tangan manusia. | FR-10 | M |
| US-11 | Sebagai admin, saya ingin klaim, keputusan, dan jejak langkah/pemanggilan tool tersimpan di database, sehingga semuanya dapat diaudit. | FR-11 | M |
| US-12 | Sebagai salesman/reviewer, saya ingin melihat langkah kerja agent secara berurutan di antarmuka, sehingga keputusan transparan dan dapat dipercaya. | FR-12 | M |
| US-13 | Sebagai admin/kepatuhan, saya ingin data sensitif dimasking sebelum dikirim ke LLM eksternal, sehingga data pribadi tidak bocor. | FR-13 | M |
| US-14 | Sebagai manajemen, saya ingin laporan ringkas periodik (jumlah klaim, otomatis vs manual, anomali, estimasi waktu dihemat) dan ekspor CSV, sehingga biaya dan kepatuhan terpantau. | FR-14 | M (CSV) / C (Google Sheets) |
| US-15 | Sebagai admin, saya ingin agent mempertimbangkan riwayat klaim per karyawan/vendor dan konteks percakapan klaim, sehingga keputusan menggunakan konteks historis yang relevan. | FR-15 | M |

## 4. Alur Utama (Happy Path)

1. Andi mengunggah foto nota makan Rp60.000 melalui antarmuka web.
2. Agent memeriksa kualitas gambar, lalu mengekstrak field (vendor, tanggal, total, item, kategori) dengan skor kepercayaan.
3. Validasi deterministik lolos (total = jumlah item, tanggal ≤ 14 hari, format valid).
4. Pengecekan kebijakan (RAG): makan ≤ Rp75.000/orang/hari → lolos.
5. Deteksi duplikat: hash dan kemiripan tidak menemukan klaim sebelumnya.
6. Skor anomali rendah berdasarkan pola historis.
7. Keputusan engine: nominal ≤ Rp500.000 + confidence ≥ 0,8 + tanpa sinyal pemblokir → **auto-approve**.
8. Klaim, keputusan, dan seluruh jejak langkah tersimpan; Andi melihat ringkasan keputusan beserta alasan; admin melihat klaim pada laporan periodik.

## 5. Lingkup Rilis (MVP)

- **MVP (Must):** US-01 s.d. US-13 dan US-15 — pipeline otonom penuh (intake → ekstraksi → validasi → kebijakan → duplikat → anomali → keputusan → klarifikasi/eskalasi → persistensi/audit), transparansi langkah agent, masking data, dan memori konteks.
- **Rilis ini (Should/Could):** US-14 — laporan ringkas + ekspor CSV (Should); adapter Google Sheets (Could, di belakang boundary adapter).
- **Tidak dibangun (Won't):** integrasi WhatsApp/email, approval berjenjang multi-peran, integrasi software akuntansi, canvas alur, LLM on-premise (lihat [[05-brd|BRD]] §7).

## 6. Kebutuhan Non-Fungsional Ringkas

| Aspek | Target |
|-------|--------|
| Performa | Klaim standar diproses < 30 detik (target prototipe); endpoint API non-pipeline < 2 detik |
| Perangkat | Web desktop & browser mobile (Chrome/Edge dua versi terakhir) |
| Keamanan | Masking sebelum LLM eksternal; kunci API hanya di `.env`; repo bebas data pribadi asli |
| Auditabilitas | 100% keputusan dengan alasan terstruktur + jejak langkah; append-only |
| Reliabilitas | Retry berbatas, fallback provider, kegagalan eksplisit per langkah |

Detail terukur dan cara verifikasi: lihat [[07-srs|SRS]] §4.

## 7. Metrik Sukses

| Metrik | Target | Cara ukur |
|--------|--------|-----------|
| Waktu admin per klaim | < 1 menit | Perbandingan durasi pipeline vs proses manual pada demo |
| Klaim tanpa intervensi | ≥ 70% | Agregat status keputusan pada `/reports/summary` (set uji sintetis) |
| Duplikat/pelanggaran tertangkap | ≥ 90% | Kasus uji yang disisipkan sengaja pada set uji |
| Akurasi ekstraksi field | ≥ 90% | Field-level confidence vs ground truth pada set uji nota |
| Alasan keputusan tercatat | 100% | Inspeksi tabel keputusan + audit trail |
| Skenario penerimaan | 6/6 lulus | Fixture uji skenario BRD (lihat [[07-srs|SRS]] §6) |

## 8. Asumsi & Terbuka

- **Asumsi:**
  - LLM provider: GLM vision via Z.ai (endpoint OpenAI-compatible) melalui LangChain, dengan `PROVIDER_MODE=mock|live` — mode `mock` menjaga seluruh pengujian deterministik (ADR 0002).
  - Data uji sintetis/anonim; dataset nota publik (CORD) dengan atribusi lisensi.
  - Tanpa autentikasi penuh: identitas karyawan berupa ID eksternal (batasan prototipe yang dinyatakan eksplisit).
- **Pertanyaan terbuka yang harus dijawab sebelum rilis demo:**
  - Host deploy publik untuk live link juri (rekomendasi: PaaS berbasis container — Render/Railway/Fly.io; perlu diputuskan sebelum 4 Nov).
  - Kuota & latensi API LLM pada volume demo, dan cadangan fallback model.
  - Cakupan akhir set uji nota (jumlah dan variasi kualitas gambar).
