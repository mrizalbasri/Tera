# Business Requirements Document (BRD)
## AI Agent Pengelolaan Klaim Biaya Operasional (Expense Reimbursement Agent)

| | |
|---|---|
| **Kompetisi** | GTNIC 2026, kategori AI Agent (sub-tema: Building Intelligent AI Agents for Enterprise Productivity) |
| **Judul kerja** | Expense Agent |
| **Versi / Status** | 0.1 / Draft |
| **Target industri** | Distribusi FMCG (tim sales lapangan) |

> Catatan: angka volume, waktu, dan biaya di dokumen ini adalah **asumsi** untuk perusahaan fiktif dan harus divalidasi (idealnya lewat wawancara singkat dengan staf finance/admin nyata).

---

## 1. Ringkasan
Expense Agent adalah AI agent yang memproses klaim reimbursement karyawan secara otonom: membaca foto nota, memvalidasi terhadap kebijakan perusahaan, mendeteksi duplikat/anomali, mengambil keputusan (setujui, tandai, atau minta klarifikasi), lalu mencatat hasilnya. Manusia hanya terlibat pada kasus pengecualian.

## 2. Latar Belakang & Masalah
Perusahaan distribusi dengan banyak salesman lapangan menerima ratusan hingga ribuan nota per bulan (BBM, tol, parkir, makan, hotel).

| Masalah | Dampak |
|---|---|
| Nota dikumpulkan fisik/difoto lewat chat lalu diinput manual | Lambat, rawan salah ketik |
| Admin memeriksa kebijakan satu per satu | Beban kerja tinggi, hasil tidak konsisten |
| Klaim ganda atau di luar kebijakan sulit terdeteksi | Kebocoran biaya |
| Nota buram/tidak lengkap baru ketahuan di akhir | Klaim tertunda, karyawan menunggu lama |

## 3. Tujuan & Metrik Keberhasilan

| Tujuan bisnis | Metrik | Target (asumsi) |
|---|---|---|
| Menghemat waktu proses | Waktu admin per klaim | dari ±5 menit menjadi <1 menit rata-rata |
| Mengurangi beban manual | Persentase klaim selesai tanpa intervensi | ≥ 70% |
| Mengurangi kebocoran biaya | Klaim ganda/melanggar yang tertangkap | ≥ 90% dari kasus uji |
| Menjaga akurasi data | Akurasi ekstraksi field (vendor, tanggal, total) | ≥ 90% pada set uji |
| Transparansi keputusan | Klaim dengan alasan keputusan tercatat | 100% |

**Estimasi dampak (asumsi):** 120 salesman × 15 klaim/bulan = ±1.800 klaim/bulan × 5 menit = ±150 jam/bulan. Dengan 70% klaim diproses otomatis, waktu manual turun menjadi ±45 jam/bulan, sehingga hemat ±105 jam kerja admin per bulan.

## 4. Ruang Lingkup

**Dalam lingkup (prototype):**
- Upload nota (foto/PDF) melalui antarmuka web berbasis chat dengan agent
- Ekstraksi field, validasi, pengecekan kebijakan, deteksi duplikat/anomali
- Keputusan otomatis, klarifikasi lewat percakapan, pencatatan ke database
- Jejak keputusan (audit trail) dan ringkasan laporan
- Ekspor data terstruktur (CSV/Google Sheets)

**Di luar lingkup (Future Development):** integrasi WhatsApp/email inbox, multi-peran penuh (manajer/finance dengan alur approval berjenjang), integrasi software akuntansi, canvas alur yang bisa diatur pengguna, model LLM on-premise.

## 5. Pemangku Kepentingan & Pengguna

| Peran | Kebutuhan |
|---|---|
| Karyawan (salesman) | Ajukan klaim cepat, tahu status dan alasan penolakan dengan jelas |
| Admin/Finance | Kurangi input manual, terima hanya kasus yang perlu ditinjau |
| Manajer | Klaim berisiko tinggi ditandai lengkap dengan alasan |
| Manajemen | Laporan biaya operasional dan kepatuhan kebijakan |

## 6. Proses Saat Ini vs Target

**Saat ini:** karyawan kumpulkan nota → kirim ke admin → admin input ke spreadsheet → cek kebijakan manual → tanya ulang jika bermasalah → persetujuan → pencatatan.

**Target:** karyawan upload nota → agent ekstrak dan validasi → cek kebijakan → cek duplikat/anomali → keputusan otomatis (atau tanya ulang / eskalasi) → tersimpan dengan alasan → laporan otomatis.

## 7. Kebutuhan Bisnis (BR)

| ID | Kebutuhan |
|---|---|
| BR-01 | Sistem harus mengurangi pekerjaan input dan pemeriksaan manual klaim |
| BR-02 | Sistem harus menegakkan kebijakan klaim perusahaan secara konsisten |
| BR-03 | Sistem harus mendeteksi klaim ganda dan pola tidak wajar |
| BR-04 | Setiap keputusan harus dapat ditelusuri dan dijelaskan |
| BR-05 | Data sensitif tidak boleh bocor ke pihak eksternal tanpa perlindungan |
| BR-06 | Kasus berisiko atau tidak pasti harus dieskalasi ke manusia |

## 8. Kebutuhan Fungsional (FR)

| ID | Kebutuhan | Terkait |
|---|---|---|
| FR-01 | Menerima upload nota (JPG/PNG/PDF) dan mengukur kualitas gambar | BR-01 |
| FR-02 | Ekstraksi field terstruktur (vendor, tanggal, total, item, kategori) beserta skor kepercayaan | BR-01 |
| FR-03 | Pra-pemrosesan ulang dan percobaan ulang otomatis bila kepercayaan rendah; bila tetap gagal, minta foto ulang dengan pesan spesifik | BR-01 |
| FR-04 | Validasi deterministik (total = jumlah item, tanggal wajar, format valid) | BR-02 |
| FR-05 | Pengecekan kebijakan lewat pencarian dokumen kebijakan (RAG): limit, kategori, syarat | BR-02 |
| FR-06 | Deteksi duplikat (hash gambar + kemiripan vendor/tanggal/nominal) | BR-03 |
| FR-07 | Skor anomali dengan model ML berdasarkan pola klaim historis | BR-03 |
| FR-08 | Keputusan: setujui / tandai / tolak / tanya ulang, disertai alasan | BR-02, BR-04 |
| FR-09 | Klarifikasi lewat percakapan ketika terdapat ambiguitas (misalnya nota untuk beberapa orang) dan hitung ulang setelah jawaban | BR-02 |
| FR-10 | Eskalasi ke reviewer manusia untuk klaim melewati ambang nominal atau kepercayaan rendah | BR-06 |
| FR-11 | Simpan klaim, keputusan, dan jejak langkah/pemanggilan tool ke database | BR-04 |
| FR-12 | Tampilkan langkah kerja agent secara berurutan di antarmuka | BR-04 |
| FR-13 | Masking data sensitif sebelum dikirim ke LLM eksternal | BR-05 |
| FR-14 | Laporan ringkas periodik (jumlah klaim, otomatis vs manual, anomali, estimasi waktu dihemat) dan ekspor CSV/Sheets | BR-01 |
| FR-15 | Memori: riwayat klaim per karyawan/vendor dan konteks percakapan klaim | BR-03 |

## 9. Aturan Bisnis (contoh kebijakan, dapat dikonfigurasi)

| Kategori | Aturan |
|---|---|
| Makan dinas | Maks. Rp75.000 per orang per hari; wajib nota; alkohol tidak boleh diklaim |
| BBM | Maks. Rp150.000 per hari kerja; wajib nota SPBU |
| Tol/parkir | Sesuai nominal nota; wajib nota |
| Hotel | Maks. Rp600.000 per malam; wajib perjalanan dinas |
| Batas waktu klaim | Maks. 14 hari sejak tanggal nota |
| Duplikat | Nota dengan vendor, tanggal, dan nominal sama ditolak dan ditandai |
| Auto-approve | Nominal ≤ Rp500.000, kepercayaan ≥ 0,8, tidak ada anomali |
| Eskalasi | Nominal > Rp500.000, kepercayaan < 0,8, atau skor anomali tinggi |

## 10. Kebutuhan Non-Fungsional

| Aspek | Kebutuhan |
|---|---|
| Keamanan | Masking data, pembatasan tool tulis (guardrail), kunci API tidak di repo, repo tanpa data pribadi asli |
| Keandalan | Retry, fallback, dan penanganan error di tiap langkah |
| Performa | Klaim standar diproses < 30 detik (target prototype) |
| Modularitas | Tiap tool terpisah dengan skema input/output tervalidasi |
| Auditabilitas | Semua keputusan dan pemanggilan tool tercatat |
| Aksesibilitas | Antarmuka publik (live link) dan repo publik sampai kompetisi berakhir |

## 11. Data
- **Nota uji:** dataset publik nota (misalnya CORD, dengan atribusi sesuai lisensi) + nota nyata yang datanya sudah disamarkan
- **Data klaim historis:** **sintetis** (klaim fiktif dengan kasus duplikat dan anomali yang disisipkan sengaja). Akurasi ML dilaporkan sebagai hasil pada data sintetis, bukan klaim performa dunia nyata
- **Dokumen kebijakan:** dibuat sendiri berdasarkan aturan bisnis pada bagian 9

## 12. Asumsi & Batasan
- Perusahaan, volume, dan kebijakan bersifat fiktif dan menjadi dasar estimasi dampak
- LLM diakses lewat API pihak ketiga; kualitas ekstraksi bergantung pada kualitas foto
- Prototype belum mencakup autentikasi/otorisasi penuh dan integrasi sistem akuntansi

## 13. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Halusinasi/salah ekstraksi | Validasi deterministik, skor kepercayaan, eskalasi ke manusia |
| Kebocoran data sensitif | Masking sebelum ke LLM, tanpa data asli di repo publik |
| Keputusan salah pada klaim bernilai besar | Ambang auto-approve, human-in-the-loop |
| OCR gagal pada nota buruk | Pra-pemrosesan, fallback engine, permintaan foto ulang |
| Akurasi ML tidak mewakili dunia nyata | Transparan bahwa data sintetis; rencana validasi dengan data nyata |
| Ketergantungan API/kuota | Fallback model, batasi panggilan, cache |

## 14. Skenario Penerimaan (untuk demo dan pengujian)

| # | Skenario | Hasil yang diharapkan |
|---|---|---|
| 1 | Nota makan Rp60.000, valid | Auto-approve, alasan tercatat |
| 2 | Nota makan Rp240.000 untuk beberapa orang | Agent bertanya jumlah peserta, menghitung ulang, lalu memutuskan |
| 3 | Nota parkir identik dengan klaim minggu lalu | Ditolak/ditandai sebagai duplikat |
| 4 | Foto buram, total tidak terbaca | Coba ulang, lalu minta foto ulang dengan pesan jelas |
| 5 | Klaim > Rp500.000 | Dieskalasi ke reviewer manusia |
| 6 | Pola nominal tidak wajar untuk karyawan tertentu | Ditandai anomali dengan penjelasan |

## 15. Pemetaan ke Kriteria Penilaian GTNIC

| Kriteria (bobot) | Dipenuhi oleh |
|---|---|
| Otonomi agen (25%) | Alur end-to-end tanpa intervensi; manusia hanya untuk pengecualian (FR-03, FR-08, FR-10) |
| Penalaran & keputusan (15%) | Klarifikasi ambiguitas, retry, konteks percakapan (FR-03, FR-09, FR-15) |
| Alat & eksekusi (15%) | Tool chaining tervalidasi + tulis DB/ekspor (FR-02 s.d. FR-14) |
| Arsitektur (15%) | Modular, skema DB, memori, masking, error handling (FR-11, FR-13, FR-15, bagian 10) |
| Inovasi (10%) | Kombinasi kepatuhan kebijakan (RAG), deteksi anomali (ML), dan keamanan data |
| Dampak & bisnis (10%) | Metrik pada bagian 3 |
| UX (5%) | Antarmuka chat dengan langkah kerja terlihat dan pesan error jelas (FR-12) |
| Demo & dokumentasi (5%) | Skenario pada bagian 14, repo dengan README |

## 16. Rencana Kerja Singkat
- **Sekarang - 16 Okt:** pendaftaran, kunci profil industri, susun dataset dan kebijakan, prototipe alur inti
- **18 Okt:** Technical Meeting
- **19 Okt - 4 Nov:** bangun alur lengkap, ML, keamanan, deploy publik
- **5 - 8 Nov:** proposal (maks. 15 halaman) dan video demo 3-5 menit
- **9 - 10 Nov:** buffer dan submit sebelum 10 Nov 23:59 WIB
