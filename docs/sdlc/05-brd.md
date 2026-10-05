# BRD (Business Requirements Document) — Expense Agent

> **Fungsi dokumen:** mendefinisikan kebutuhan level **bisnis** — masalah apa yang diselesaikan dan tujuan apa yang dicapai. TANPA detail fitur teknis. Pembacanya: manajemen/sponsor. Fitur detail masuk [[06-prd|PRD]] dan [[07-srs|SRS]].

| | |
|---|---|
| **Proyek** | Expense Agent — AI Agent Pengelolaan Klaim Biaya Operasional |
| **Pemilik kebutuhan** | Tim Expense Agent (peserta GTNIC 2026, kategori AI Agent) — perusahaan target: distributor FMCG fiktif dengan tim sales lapangan |
| **Versi / tanggal** | v1.0 / 2026-10-05 |
| **Sumber** | Diselaraskan dari `docs/BRD_Expense_Reimbursement_Agent.md` v0.1 Draft |

## 1. Latar Belakang

Perusahaan distribusi FMCG dengan 120 salesman lapangan menerima ratusan hingga ribuan nota klaim per bulan (BBM, tol, parkir, makan, hotel). Proses yang berjalan saat ini masih manual: nota dikumpulkan fisik atau difoto lewat chat, kemudian admin menginputnya ke spreadsheet, memeriksa kebijakan satu per satu, dan bertanya ulang ke karyawan bila ada masalah.

Konsekuensinya terukur langsung pada biaya dan waktu: proses ini menelan sekitar **150 jam kerja admin per bulan** (±1.800 klaim/bulan × 5 menit), rawan salah ketik, tidak konsisten dalam menegakkan kebijakan, dan kebocoran akibat klaim ganda atau di luar kebijakan sulit terdeteksi. Nota buram baru diketahui bermasalah di akhir proses sehingga klaim tertunda dan karyawan menunggu lama tanpa kejelasan.

Expense Agent mengusulkan AI agent yang memproses klaim reimbursement secara otonom: membaca foto nota, memvalidasi terhadap kebijakan perusahaan, mendeteksi duplikat/anomali, mengambil keputusan, dan mencatat hasilnya — manusia hanya terlibat pada kasus pengecualian.

## 2. Tujuan Bisnis

> Terukur dan berbatas waktu. Target diukur pada set uji sintetis milik proyek sebelum tenggat submit GTNIC 2026.

1. **Mengurangi** waktu proses admin per klaim **dari ±5 menit menjadi < 1 menit** pada demo GTNIC (sebelum 10 November 2026).
2. **Mencapai ≥ 70% klaim** selesai tanpa intervensi manusia pada set uji sintetis (sebelum 10 November 2026).
3. **Menangkap ≥ 90%** kasus klaim ganda/pelanggaran kebijakan yang disisipkan sengaja pada set uji (sebelum 10 November 2026).
4. **Mencapai akurasi ekstraksi field** (vendor, tanggal, total) **≥ 90%** pada set uji nota (sebelum 10 November 2026).
5. **Mencatat alasan keputusan untuk 100% klaim** — setiap keputusan dapat ditelusuri melalui audit trail (sebelum 10 November 2026).

**Estimasi dampak (asumsi perusahaan fiktif):** 120 salesman × 15 klaim/bulan = ±1.800 klaim/bulan × 5 menit = ±150 jam/bulan. Dengan 70% klaim diproses otomatis, waktu manual turun menjadi ±45 jam/bulan — hemat **±105 jam kerja admin per bulan**.

## 3. Stakeholder

| Stakeholder | Peran | Ketertarikan/Pengaruh |
|-------------|-------|------------------------|
| Karyawan (salesman) | Pengaju klaim | Ajukan klaim cepat; tahu status dan alasan penolakan dengan jelas |
| Admin/Finance | Pemroses klaim | Kurangi input manual; hanya menerima kasus yang perlu ditinjau |
| Manajer/Reviewer | Penyetuju kasus berisiko | Klaim berisiko tinggi ditandai lengkap dengan alasan objektif |
| Manajemen | Pemilik anggaran | Laporan biaya operasional dan kepatuhan kebijakan |
| Tim Expense Agent | Pengembang & pemilik kebutuhan | Prototipe lulus kriteria penilaian GTNIC 2026 |
| Panitia & juri GTNIC | Evaluator | Bukti otonomi agen, arsitektur, inovasi, dan dampak bisnis |

## 4. Kebutuhan Bisnis

| Kode | Kebutuhan | Alasan/Metrik |
|------|-----------|---------------|
| BR-01 | Sistem harus mengurangi pekerjaan input dan pemeriksaan manual klaim | Waktu admin per klaim turun dari ±5 menit menjadi < 1 menit; ≥ 70% klaim tanpa intervensi |
| BR-02 | Sistem harus menegakkan kebijakan klaim perusahaan secara konsisten | Aturan kebijakan diterapkan seragam pada 100% klaim, bukan berdasarkan penilaian manual |
| BR-03 | Sistem harus mendeteksi klaim ganda dan pola tidak wajar | ≥ 90% kasus duplikat/anomali pada set uji tertangkap |
| BR-04 | Setiap keputusan harus dapat ditelusuri dan dijelaskan | 100% keputusan menyimpan alasan terstruktur + jejak langkah agent |
| BR-05 | Data sensitif tidak boleh bocor ke pihak eksternal tanpa perlindungan | Data dimasking sebelum dikirim ke LLM eksternal; tanpa data pribadi asli di repo publik |
| BR-06 | Kasus berisiko atau tidak pasti harus dieskalasi ke manusia | Klaim bernilai besar, kepercayaan rendah, atau anomali tinggi selalu melewati reviewer manusia |

## 5. Kriteria Keberhasilan (Success Criteria)

| Kriteria | Ukuran | Target | Kapan diukur |
|----------|--------|--------|--------------|
| Penghematan waktu proses | Waktu admin per klaim | < 1 menit (dari ±5 menit) | Demo akhir, sebelum submit 10 Nov 2026 |
| Otomasi penuh | Klaim selesai tanpa intervensi | ≥ 70% dari set uji | Uji set sintetis, sebelum submit |
| Pencegahan kebocoran | Duplikat/pelanggaran tertangkap | ≥ 90% dari kasus uji | Uji set sintetis, sebelum submit |
| Akurasi data | Akurasi ekstraksi field | ≥ 90% pada set uji nota | Uji set sintetis, sebelum submit |
| Transparansi | Klaim dengan alasan keputusan tercatat | 100% | Audit trail, sebelum submit |
| Kesiapan demo | Live link publik + repo publik aktif | Aktif saat penilaian | 9–10 Nov 2026 |

## 6. Batasan & Asumsi

- **Batasan:**
  - Tenggat kompetisi: proposal (maks. 15 halaman) + video demo 3–5 menit disubmit **sebelum 10 November 2026, 23:59 WIB**.
  - Prototipe **belum mencakup autentikasi/otorisasi penuh** — karyawan diidentifikasi lewat ID eksternal.
  - LLM diakses lewat **API pihak ketiga** (GLM vision via Z.ai, endpoint OpenAI-compatible; kualitas ekstraksi bergantung kualitas foto).
  - Antarmuka publik (live link) dan repo publik selama kompetisi → **dilarang memuat data pribadi asli**.
- **Asumsi:**
  - Perusahaan, volume, dan kebijakan bersifat **fiktif** dan menjadi dasar estimasi dampak; angka wajib divalidasi dengan wawancara staf finance/admin nyata bila memungkinkan.
  - Nota uji berasal dari dataset publik (mis. CORD, dengan atribusi lisensi) + nota nyata yang datanya sudah disamarkan.
  - Data klaim historis untuk model ML bersifat **sintetis**; akurasi ML dilaporkan sebagai hasil pada data sintetis, bukan klaim performa dunia nyata.

## 7. Out of Scope

- Integrasi WhatsApp/email inbox.
- Multi-peran penuh dengan alur approval berjenjang (manajer → finance).
- Integrasi software akuntansi.
- Canvas alur yang bisa diatur pengguna.
- Model LLM on-premise.

---

**Persetujuan:** sponsor: ______________ (ttd, tanggal)

## Lampiran — Pemetaan ke Kriteria Penilaian GTNIC 2026

| Kriteria (bobot) | Dipenuhi oleh |
|---|---|
| Otonomi agen (25%) | Alur end-to-end tanpa intervensi; manusia hanya untuk pengecualian (BR-01, BR-06) |
| Penalaran & keputusan (15%) | Klarifikasi ambiguitas, retry, konteks percakapan (BR-02, BR-04) |
| Alat & eksekusi (15%) | Tool chaining tervalidasi + tulis DB/ekspor (seluruh FR, lihat [[07-srs|SRS]]) |
| Arsitektur (15%) | Modular, skema DB, memori, masking, error handling (lihat [[08-system-design-sdd|SDD]]) |
| Inovasi (10%) | Kombinasi kepatuhan kebijakan berbasis RAG + deteksi anomali ML + keamanan data |
| Dampak & bisnis (10%) | Metrik pada bagian 2 dan 5 |
| UX (5%) | Antarmuka chat dengan langkah kerja terlihat dan pesan error jelas |
| Demo & dokumentasi (5%) | Skenario penerimaan (lihat [[07-srs|SRS]] §6) + repo dengan README |

## Rencana Kerja Singkat (dari BRD awal)

- **Sekarang – 16 Okt:** pendaftaran, kunci profil industri, susun dataset dan kebijakan, prototipe alur inti.
- **18 Okt:** Technical Meeting.
- **19 Okt – 4 Nov:** bangun alur lengkap, ML, keamanan, deploy publik.
- **5 – 8 Nov:** proposal (maks. 15 halaman) dan video demo 3–5 menit.
- **9 – 10 Nov:** buffer dan submit sebelum 10 Nov 23:59 WIB.
