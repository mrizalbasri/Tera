# SRS (Software Requirements Specification) — Expense Agent

> **Fungsi dokumen:** spesifikasi kebutuhan level **software** yang terukur dan bisa diuji. Pembacanya: programmer & QA. Aturan emas: satu kebutuhan = satu pernyataan yang bisa dinyatakan LULUS/GAGAL saat testing.

| | |
|---|---|
| **Sistem** | Expense Agent (backend FastAPI + frontend SvelteKit) |
| **Berdasarkan** | [[05-brd|BRD v1.0]] dan [[06-prd|PRD v1.0]] |
| **Versi / tanggal** | v1.0 / 2026-10-05 |

## 1. Pendahuluan

- **Tujuan dokumen:** mendefinisikan kebutuhan fungsional dan non-fungsional Expense Agent secara terukur sehingga dapat diverifikasi lewat pengujian.
- **Scope sistem:** prototipe web untuk pemrosesan klaim reimbursement otonom — dari upload nota sampai keputusan, audit trail, dan laporan — mencakup FR-01 s.d. FR-15.
- **Definisi & singkatan:**
  - **Claim** — satu pengajuan reimbursement karyawan; dapat memuat satu atau lebih receipt.
  - **Receipt** — dokumen nota yang dilampirkan pada klaim; memiliki metadata file, hasil ekstraksi, dan informasi kualitas.
  - **Processing run** — satu percobaan pemrosesan klaim melalui pipeline; retry membuat run baru, bukan menimpa run lama.
  - **Policy** — kumpulan aturan bisnis yang ber-versi, dipakai untuk mengevaluasi klaim.
  - **Signal** — hasil terstruktur dari validasi, deteksi duplikat, atau skor anomali yang memengaruhi keputusan.
  - **Decision** — hasil akhir/berjalan untuk klaim: `approved`, `rejected`, `needs_clarification`, atau `escalated`.
  - **Clarification** — pertanyaan agent saat data nota/konteks tidak cukup untuk memutuskan dengan aman.
  - **Review** — aksi manusia atas klaim yang dieskalasi; dapat mengonfirmasi atau meng-override keputusan agent.
  - **Audit event** — catatan immutable atas langkah pemrosesan, pemanggilan tool, keputusan, atau aksi manusia.

## 2. Deskripsi Umum

- **Perspektif:** sistem baru (prototipe kompetisi), monorepo berisi backend FastAPI dan frontend SvelteKit yang belum terhubung penuh — integrasi FE↔BE bagian dari lingkup rilis ini.
- **Fungsi utama:**
  1. Intake klaim: upload nota JPG/PNG/PDF + pemeriksaan kualitas (FR-01).
  2. Ekstraksi field + retry/klarifikasi nota buruk (FR-02, FR-03).
  3. Validasi deterministik + evaluasi kebijakan via RAG (FR-04, FR-05).
  4. Deteksi duplikat + skor anomali ML + keputusan berprece konservatif (FR-06, FR-07, FR-08).
  5. Klarifikasi percakapan + eskalasi manusia + memori konteks (FR-09, FR-10, FR-15).
  6. Persistensi, audit trail, timeline langkah agent (FR-11, FR-12).
  7. Masking data sensitif sebelum provider eksternal (FR-13).
  8. Laporan ringkas + ekspor CSV (FR-14).
- **Karakteristik user:** salesman (non-teknis, mobile browser), admin/finance (semi-teknis, desktop), reviewer/manajer (desktop). Tidak diperlukan pelatihan khusus; antarmuka chat + dashboard.
- **Batasan:** tanpa autentikasi/otorisasi penuh (ID karyawan eksternal); LLM via API pihak ketiga; data sintetis/anonim saja; tenggat submit 10 Nov 2026.
- **Asumsi & dependensi:** ketersediaan API LLM (GLM vision via Z.ai, `PROVIDER_MODE=mock|live`); dataset nota publik (CORD) tersedia dengan atribusi; seluruh pengujian berjalan deterministik pada mode `mock`.

## 3. Kebutuhan Fungsional

| Kode | Deskripsi | Input | Proses | Output | Prioritas |
|------|-----------|-------|--------|--------|-----------|
| FR-01 | Menerima upload nota dan mengukur kualitas gambar | File JPG/PNG/PDF ≤ 10 MB | Validasi tipe/ukuran; simpan referensi aman + content hash; jalankan quality checker | Klaim+Receipt status `received`; skor kualitas + temuan; error eksplisit untuk file invalid | M |
| FR-02 | Ekstraksi field terstruktur dengan skor kepercayaan | Konten nota (termasking) | Ekstraksi via LLM (LangChain, GLM) → parsing ke skema Pydantic | vendor, tanggal, total, item, kategori + confidence per field; tersimpan per run | M |
| FR-03 | Pra-pemrosesan ulang & retry otomatis bila confidence rendah; minta foto ulang bila tetap gagal | Hasil ekstraksi confidence < 0,8 | Preprocessing hook + retry berbatas (≤ 2); bila tetap gagal → buat clarification request | Extraction attempt tercatat; pesan foto-ulang spesifik ke user | M |
| FR-04 | Validasi deterministik | Field hasil ekstraksi | Cek total = jumlah item, tanggal wajar (≤ 14 hari), format & mata uang valid, field wajib | ValidationFinding per aturan dengan reason code stabil | M |
| FR-05 | Pengecekan kebijakan lewat pencarian dokumen kebijakan (RAG) | Klaim + kategori + kata kunci | RagPolicyRetriever memilih Policy ber-versi (ChromaDB); evaluasi tetap deterministik; miss → fallback local store + audit | PolicyEvaluation per rule: nilai aktual, limit, pass/fail, penjelasan; versi policy tercatat di setiap keputusan | M |
| FR-06 | Deteksi duplikat | Content hash + field nota | Cek duplikat exact (hash) dan kemiripan vendor/tanggal/nominal | Signal duplikat dengan evidence; duplikat terkonfirmasi → `rejected` | M |
| FR-07 | Skor anomali dengan model ML | Data klaim historis (sintetis) + fitur klaim | Isolation Forest (sklearn) dengan random state & skema fitur tetap; fallback ke rules; riwayat kosong → netral | Signal anomali: skor + evidence + versi model; skor tinggi → eskalasi (tidak pernah approve) | M |
| FR-08 | Keputusan disertai alasan | Seluruh signal + hasil evaluasi | Precedence konservatif: data invalid → klarifikasi; duplikat/pelanggaran → tolak; risiko tinggi → eskalasi; hanya lolos semua cek → approve | Decision dengan reason codes, confidence, policy version, processing run | M |
| FR-09 | Klarifikasi lewat percakapan + hitung ulang | Pertanyaan agent (mis. jumlah peserta makan) | Simpan tanya-jawab; jawaban memicu ProcessingRun baru tanpa menghapus run lama | Klarifikasi tercatat; keputusan ulang dengan nilai terkoreksi | M |
| FR-10 | Eskalasi ke reviewer manusia | Klaim > Rp500.000, confidence < 0,8, atau skor anomali ≥ 0,7 | Klaim masuk antrean review; reviewer memutuskan/override sebagai Decision baru | Antrean review; aksi reviewer tercatat + dapat diaudit | M |
| FR-11 | Simpan klaim, keputusan, jejak langkah/tool ke database | Seluruh domain object | Persistensi atomik via repository (SQLAlchemy); idempotency untuk pembuatan klaim & retry | Klaim dapat direkonstruksi penuh dari timeline | M |
| FR-12 | Tampilkan langkah kerja agent berurutan | ProcessingRun + AuditEvent | Gabung & urutkan event per klaim (sequence stabil) | Timeline di antarmuka: langkah, status, durasi, metadata aman | M |
| FR-13 | Masking data sensitif sebelum dikirim ke LLM eksternal | Konten nota + konteks klaim | Klasifikasi field; SensitiveDataMasker berjalan di kode kita sebelum boundary provider | Payload termasking ke provider; bukti lewat masking test; metadata provider aman yang tersimpan | M |
| FR-14 | Laporan ringkas periodik + ekspor CSV | Filter periode/status/kategori/karyawan | Agregasi dari data klaim & keputusan tersimpan; estimasi waktu dihemat dengan rumus terdokumentasi | Metrik ringkas + CSV header stabil; failure ekspor eksplisit tanpa mengubah state klaim | M (CSV) / C (Sheets) |
| FR-15 | Memori riwayat klaim per karyawan/vendor + konteks percakapan | Klaim historis + percakapan | Query konteks dengan scope eksplisit per karyawan (tanpa campur antar karyawan) | Konteks tersedia bagi processing service; riwayat terlindungi privasi | M |

**Aturan bisnis:**

| Kode | Aturan | Contoh penerapan |
|------|--------|------------------|
| RB-01 | Makan dinas maks. Rp75.000/orang/hari; wajib nota; alkohol tidak boleh diklaim | Makan Rp60.000 → lolos; makan Rp240.000 untuk 4 orang → agent tanya jumlah peserta |
| RB-02 | BBM maks. Rp150.000/hari kerja; wajib nota SPBU | BBM Rp160.000 → pelanggaran limit → ditolak |
| RB-03 | Tol/parkir sesuai nominal nota; wajib nota | Parkir tanpa nota → `needs_clarification` |
| RB-04 | Hotel maks. Rp600.000/malam; wajib bukti perjalanan dinas | Hotel Rp700.000 → ditolak dengan alasan limit |
| RB-05 | Umur klaim maks. 14 hari sejak tanggal nota | Nota 20 hari lalu → ditolak/ditandai kedaluwarsa |
| RB-06 | Duplikat (vendor + tanggal + nominal sama) ditolak dan ditandai | Nota parkir identik dengan minggu lalu → `rejected` + signal duplikat |
| RB-07 | Auto-approve: nominal ≤ Rp500.000 DAN confidence ≥ 0,8 DAN tanpa signal pemblokir | Makan Rp60.000 valid → auto-approve |
| RB-08 | Eskalasi: nominal > Rp500.000 ATAU confidence < 0,8 ATAU skor anomali ≥ 0,7 | Hotel Rp800.000 → masuk antrean review |

Nilai ambang (Rp500.000, confidence 0,8, anomali 0,7, umur 14 hari) dapat dikonfigurasi via environment (`AUTO_APPROVE_AMOUNT_LIMIT`, `AUTO_APPROVE_MIN_CONFIDENCE`, `ANOMALY_ESCALATION_THRESHOLD`, `MAX_CLAIM_AGE_DAYS`).

## 4. Kebutuhan Non-Fungsional

| Kode | Kategori | Kebutuhan (terukur) | Cara verifikasi |
|------|----------|---------------------|-----------------|
| NFR-01 | Performa | Klaim standar selesai diproses < 30 detik (mode mock maupun live) | Pengukuran durasi pipeline pada test run |
| NFR-02 | Performa | Endpoint API non-pipeline (list, detail, timeline, report) merespons < 2 detik pada beban uji | API test + pengukuran |
| NFR-03 | Keamanan | Tidak ada nilai sensitif yang melewati boundary ke provider eksternal tanpa masking (0 kebocoran pada masking test) | Masking boundary test (M7 exit criteria) |
| NFR-04 | Keamanan | Kredensial hanya di `.env`; repo bebas nota asli/data pribadi; byte nota tidak pernah masuk log atau checkpointer | Review + scan repo + inspeksi log |
| NFR-05 | Reliabilitas | Kegagalan provider diklasifikasikan retryable/non-retryable; retry berbatas (≤ 2); langkah gagal tidak menghapus langkah sukses sebelumnya | Unit + API test skenario gagal |
| NFR-06 | Auditabilitas | 100% keputusan menyimpan alasan terstruktur + processing run terkait; klaim dapat direkonstruksi dari audit timeline | Replay test per klaim |
| NFR-07 | Konsistensi | Keputusan deterministik: input + policy version sama → keputusan sama | Property test vs fixture |
| NFR-08 | Integritas | Pengulangan `POST /claims` dan `POST /process` tidak menghasilkan klaim/run duplikat (idempotency atomik) | Concurrency + idempotency test |
| NFR-09 | Kompatibilitas | Chrome & Edge dua versi terakhir; kontrak API terdokumentasi untuk konsumen SvelteKit | Test matrix + contract test FE↔BE |
| NFR-10 | Kualitas | Seluruh suite pytest hijau (≥ 85 test pada garis dasar M6) sebelum rilis demo | Test run / CI |

## 5. Use Case / Skenario

### UC-01 — Ajukan klaim dan auto-approve

| | |
|---|---|
| **Aktor** | Salesman |
| **Pra-syarat** | Nota valid (JPG/PNG/PDF ≤ 10 MB), klaim belum pernah diajukan |
| **Alur utama** | 1. Salesman upload nota. 2. Sistem cek kualitas + simpan claim/receipt. 3. Pipeline ekstraksi → validasi → kebijakan → duplikat → anomali. 4. Semua cek lolos & nominal ≤ Rp500.000, confidence ≥ 0,8 → auto-approve. 5. Keputusan + alasan tersimpan; salesman melihat ringkasan dan timeline. |
| **Alur alternatif** | 2a. File invalid/buram → error eksplisit atau permintaan foto ulang (FR-03). 4a. Ada pelanggaran/duplikat → `rejected` dengan alasan. 4b. Berisiko → `escalated` (UC-02). |
| **Pasca-syarat** | Klaim, run, signal, decision, audit event tersimpan; laporan ter-update |

### UC-02 — Klarifikasi nota ambigu (makan multi-orang)

| | |
|---|---|
| **Aktor** | Salesman, Agent |
| **Pra-syarat** | Klaim makan dengan nilai melebihi limit per orang (mis. Rp240.000) |
| **Alur utama** | 1. Agent mendeteksi ambiguitas → `needs_clarification`, menanyakan jumlah peserta. 2. Salesman menjawab (mis. 4 orang). 3. Sistem membuat ProcessingRun baru dan menghitung ulang (Rp60.000/orang ≤ Rp75.000 → lolos). 4. Keputusan baru diterbitkan; run lama tetap tercatat. |
| **Alur alternatif** | 2a. Jawaban tidak valid → agent menanyakan ulang dengan pesan spesifik. |
| **Pasca-syarat** | Percakapan tersimpan sebagai konteks klaim; keputusan dapat diaudit |

### UC-03 — Eskalasi dan review manusia

| | |
|---|---|
| **Aktor** | Reviewer (manajer/admin) |
| **Pra-syarat** | Klaim `escalated` (nominal > Rp500.000, confidence < 0,8, atau anomali ≥ 0,7) |
| **Alur utama** | 1. Klaim muncul di antrean review. 2. Reviewer melihat timeline langkah agent + evidence signal. 3. Reviewer memutuskan (setuju/tolak/override) dengan alasan. 4. Keputusan reviewer tercatat sebagai Decision baru dengan identitas aktor. |
| **Alur alternatif** | 3a. Reviewer menunda → klaim tetap di antrean; keputusan terminal tidak pernah ditimpa diam-diam. |
| **Pasca-syarat** | Keputusan final immutable; override manusia dapat dibedakan dari keputusan agent |

### UC-04 — Laporan dan ekspor

| | |
|---|---|
| **Aktor** | Manajemen/Admin |
| **Pra-syarat** | Ada klaim tersimpan pada periode yang diminta |
| **Alur utama** | 1. Pengguna membuka laporan ringkas. 2. Sistem mengagregasi: jumlah klaim per status, otomatis vs manual, jumlah duplikat/anomali, durasi proses, estimasi waktu dihemat. 3. Pengguna mengekspor CSV dengan filter periode/status/kategori/karyawan. |
| **Alur alternatif** | 2a. Tidak ada data → laporan kosong yang eksplisit, bukan error. 3a. Ekspor gagal → error eksplisit; state klaim tidak berubah. |
| **Pasca-syarat** | Metrik laporan konsisten dengan data klaim/keputusan tersimpan |

## 6. Kriteria Penerimaan (Acceptance Criteria)

- [ ] Semua FR prioritas M terimplementasi dan lulus test.
- [ ] Enam skenario penerimaan BRD lulus sebagai fixture uji:
  1. Nota makan Rp60.000 valid → auto-approve, alasan tercatat.
  2. Nota makan Rp240.000 untuk beberapa orang → agent bertanya jumlah peserta, menghitung ulang, lalu memutuskan.
  3. Nota parkir identik dengan klaim sebelumnya → ditolak/ditandai duplikat.
  4. Foto buram, total tidak terbaca → retry, lalu minta foto ulang dengan pesan jelas.
  5. Klaim > Rp500.000 → dieskalasi ke reviewer manusia.
  6. Pola nominal tidak wajar → ditandai anomali dengan penjelasan.
- [ ] Semua NFR terverifikasi dengan cara verifikasi pada §4.
- [ ] Seluruh suite pytest hijau (≥ 85 test garis dasar + test milestone berikutnya).
- [ ] Live link demo aktif dan repo publik bebas data pribadi asli.

---

**Persetujuan:** analis: ______________ · user: ______________ · QA: ______________
