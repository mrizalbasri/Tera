# Pemeriksaan konsistensi OCR — 17 Oktober 2026

Evaluator memiliki mode `hybrid`: memakai OCR + LLM teks bila bukti nominal
konsisten, lalu membaca foto dengan adapter vision bila bukti meragukan.
Mode ini belum dipasang sebagai jalur upload aplikasi.

Pemeriksaan tidak menerima label dataset sebagai input. Label digunakan hanya
untuk menghitung kecocokan setelah ekstraksi selesai. Tidak ada pelatihan ulang
atau perubahan jawaban acuan.

Pemicu pembacaan foto meliputi token TOTAL yang tidak terbaca, label total yang
bertentangan, subtotal berbeda tanpa penyesuaian yang dikenali, uang tunai
lebih kecil dari total, selisih uang tunai dan kembalian yang tidak sesuai,
serta jumlah nominal item yang berbeda. Selisih aritmetika hanya merupakan
alasan meninjau foto: unit price, diskon, atau daftar item yang tidak lengkap
dapat menimbulkan selisih yang sah. Sistem tidak mengganti total dengan hasil
penjumlahan atau memperbaiki digit secara tebakan.

Hasil LLM teks juga dibandingkan dengan nominal berlabel TOTAL. Pemilihan uang
tunai atau subtotal memicu satu pembacaan foto. Kegagalan grounding atau schema
teks dapat memicu pembacaan foto, tetapi timeout provider tidak diulang melalui
jalur vision. Maksimal satu panggilan teks dan satu panggilan foto per nota.
Jika pemeriksaan awal sudah menemukan masalah, panggilan teks dilewati.

Foto melewati sanitizer dan kebijakan privasi adapter yang sama dengan evaluasi
vision sebelumnya. OCR teks melewati masking. Tidak ada penulisan record klaim.

## Reproduksi

Dari direktori `backend`, dengan provider lokal aktif dan privasi gambar `send`:

```powershell
.venv\Scripts\python.exe scripts/evaluate_cord.py --mode hybrid --workers 3 --output ../data/local/cord-v2-test/ocr-hybrid-100-consistency-v1.json
```

Gunakan nama output baru untuk run berikutnya. Evaluator menolak menimpa hasil.
Laporan mencatat rute dan alasan review per nota, termasuk saat provider gagal.
Waktu total menjumlahkan OCR cache dengan seluruh panggilan adapter pada nota
tersebut. Startup model OCR tidak termasuk. Beban provider memengaruhi timing.

## Kasus yang direproduksi

- 0014: foto mencetak TOTAL 281,435; OCR membaca `281-435` sehingga kandidat
  total hilang dan LLM sebelumnya memilih subtotal 238000.
- 0035: foto mencetak TOTAL 54,000; OCR membaca 52,000, bertentangan dengan
  nominal item 18,000 + 11,000 + 13,000 + 12,000.
- 0077: foto mencetak GRAND TOTAL 17,000, CASH 22,000, CHANGE 5,000;
  OCR kehilangan angka total sehingga pasangan label/nominal bergeser.

25 tes evaluator lolos, termasuk regresi tiga pola di atas, jalur teks tanpa
gambar untuk OCR konsisten, salah memilih cash, diskon, dan larangan retry
timeout melalui gambar. Seluruh suite backend: 511 passed, 53 skipped.

## Hasil 100 nota

Laporan lokal: `data/local/cord-v2-test/ocr-hybrid-100-consistency-v1.json`.
Hash script pada laporan cocok dengan source yang diverifikasi. Provider dan
batas timeout sama dengan run teks v3: tiga worker, timeout 30 detik per
panggilan, retry nol. Timing tidak menjamin beban provider identik antarrun.

| Metrik | Teks v3 | Hybrid konsistensi v1 |
| --- | ---: | ---: |
| Nota diuji | 100 | 100 |
| Ekstraksi berhasil | 96 | 85 |
| Total cocok, termasuk kegagalan | 89/95 | 80/95 |
| Total berbeda pada hasil berhasil | 3 | 0 |
| Timeout provider | 2 | 15 |
| Ditolak grounding | 2 | 0 |
| Rata-rata detik, termasuk OCR | 15.32 | 22.88 |

25 nota menggunakan teks saja; 75 dialihkan ke vision oleh pemeriksaan awal.
Tidak ada tambahan fallback setelah panggilan teks pada run ini. Semua 15
timeout terjadi pada rute vision. Lima nota tanpa label total tetap tidak
dimasukkan ke denominator. Nol hasil berbeda tidak berarti akurasi 100%:
15 kegagalan tetap menurunkan skor menjadi 84,21%.

Kasus 0014, 0035, dan 0077 menghasilkan masing-masing 281435, 54000, dan 17000
melalui vision. Kasus 0064 tetap menghasilkan 16000 melalui teks.

Pemeriksaan memperbaiki tiga kegagalan yang ditelusuri, tetapi keseluruhan run
lebih lambat dan lebih banyak gagal daripada teks v3. Karena itu hybrid ini
tetap eksperimen, belum diaktifkan pada upload aplikasi. Langkah berikutnya
adalah mengurangi review yang tidak perlu melalui asosiasi label/nominal dari
posisi boks OCR, serta memeriksa keandalan provider vision. Jangan menaikkan
timeout atau mengubah label hanya untuk menaikkan skor.

Nota 0020 masih perlu audit label terpisah: foto sebelumnya tampak mencetak
377659, sedangkan label resmi 377859. Pada run ini nota tersebut timeout;
label tetap dipertahankan, bukan dikoreksi berdasarkan hasil model.
