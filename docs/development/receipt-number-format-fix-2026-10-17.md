# Perbaikan penafsiran nominal OCR — 17 Oktober 2026

Kasus 0064: OCR membaca `16.000`, sedangkan keluaran terstruktur lama menjadi `16`.
Respons mentah lama tidak disimpan; belum bisa membedakan kesalahan generasi LLM
dari konversi string lokal `"16.000"` oleh parser Decimal. Perbaikan ditempatkan
di batas OCR ke LLM/validasi hasil, bukan dengan melatih ulang PaddleOCR.

## Perubahan

- Teks OCR asli dipertahankan. Kandidat nominal dinormalisasi dari format nota
  Indonesia, termasuk `16.000`, `Rp50.000`, dan `RP38. 000`.
- Model menerima kandidat numerik dan konteks format angka. Total hasil harus
  sesuai dengan kandidat; angka tidak dikalikan 1000 secara otomatis.
- Input tanggal, ID alfanumerik, dan token masking tidak dijadikan kandidat nominal.
- Mata uang tidak ditebak dari format angka. Currency yang tidak diketahui memakai
  marker `XXX` dan warning, sesuai kontrak string tiga huruf. Ini bukan mata uang
  yang didukung untuk persetujuan klaim.
- Mode ini masih eksperimen evaluator, belum mengganti jalur utama aplikasi.

## Verifikasi

18 tes evaluator lolos, termasuk nilai dict dan output Pydantic yang sudah
mengubah `"16.000"` menjadi Decimal 16, serta masking dan pengiriman tanpa gambar.
Seluruh 100 nota diuji ulang. 95 memiliki label total yang sama dengan run lama;
lima tanpa label dikeluarkan dari denominator, bukan diisi jawaban tebakan.

| Metrik | OCR + LLM lama | Versi final normalisasi |
| --- | ---: | ---: |
| Ekstraksi berhasil | 96 | 96 |
| Total cocok | 90/95 | 89/95 |
| Timeout | 4 | 2 |
| Ditolak validasi nominal | 0 | 2 |
| Total berbeda pada hasil yang lolos | 1 | 3 |
| Rata-rata detik, termasuk OCR | 19.09 | 15.32 |

Kasus 0064 berhasil pada run final dengan total `16000` dan currency `XXX`.
Waktu eksperimen membaik pada run ini, tetapi jumlah kecocokan total sedikit
menurun. Karena itu, hasil ini bukan bukti bahwa pipeline secara keseluruhan
lebih akurat atau siap menggantikan vision langsung. Kondisi provider dapat
mengubah timing; run tidak dilakukan serentak dengan beban identik.

## Temuan lanjutan

- Validasi kandidat memastikan angka berasal dari OCR, tetapi belum memastikan
  perannya TOTAL. Model masih bisa memilih subtotal atau angka lain yang valid.
- Contoh 0014: total OCR terpecah/berubah tanda, dan model memilih subtotal 238000
  ketimbang label 281435. Perlu pemeriksaan layout/peran field, bukan perkalian angka.
- Contoh 0035: OCR mencatat TOTAL 52000, sementara label 54000. Ini masalah yang
  berbeda dari separator kasus 0064; kandidat saja tidak memperbaiki digit salah.
- Total yang hanya bisa diturunkan lewat arithmetic atau terpecah antarboks bisa
  ditolak validasi. Penolakan tidak membuktikan nilai lama salah; perlu fallback
  vision atau review dengan bukti tambahan.
- Vendor/tanggal yang disamarkan CORD tetap null. Ekstraksi yang lolos parser
  bukan bukti semua field lengkap atau klaim layak disetujui.

Run v2 yang gagal tidak dihapus: diagnosis satu respons membuktikan currency null
ditolak schema meskipun total sudah benar. Instruksi v3 meminta marker XXX untuk
kasus tersebut. Probe hanya menampilkan tipe dan lokasi field, tanpa raw output.

## Artifak lokal

- `data/local/cord-v2-test/ocr-text-0064-contract-v3.json`: regresi targeted.
- `data/local/cord-v2-test/ocr-text-100-number-format-v3.json`: hasil final 100 nota.
- `data/local/cord-v2-test/ocr-text-100-number-format-v2.json`: run sebelum koreksi kontrak currency.
- `data/local/cord-v2-test/ocr-text-100.json`: baseline sebelum perubahan nominal.

[Panduan menjalankan evaluasi](receipt-ocr-evaluation.md). Dataset dan laporan lokal
diabaikan Git. Tidak ada perubahan `.env`, model OCR, dataset label, atau database aplikasi.
