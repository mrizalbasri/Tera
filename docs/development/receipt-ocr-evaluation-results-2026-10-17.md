# Hasil evaluasi nota CORD — 17 Oktober 2026

Seluruh 100 nota pada split test diproses pada dua jalur. Ada 95 label total
numerik dan lima nota tanpa label total. Label tidak dikirim ke model atau diubah
untuk menyesuaikan prediksi. Tidak ada training ulang model.

| Pengukuran | Vision langsung | PaddleOCR + LLM teks |
| --- | ---: | ---: |
| Nota diproses | 100 | 100 |
| Ekstraksi berhasil | 89 | 96 |
| Timeout provider | 11 | 4 |
| Total cocok dengan label | 84/95 | 90/95 |
| Tingkat kecocokan, termasuk kegagalan | 88.42% | 94.74% |
| Total berbeda pada ekstraksi berhasil | 1 | 1 |
| Rata-rata detik per nota | 17.75 | 19.09 |
| Median detik per nota | 15.56 | 17.02 |
| P95 detik per nota | 30.34 | 33.70 |

Model LLM yang dikonfigurasi: `ag/gemini-3.8-flash-medium`. Kedua jalur memakai tiga request
bersamaan, timeout 30.0 detik pada provider, tanpa retry atau
fallback mock. Waktu OCR + LLM adalah waktu adapter ditambah OCR tiap gambar,
bukan hanya waktu panggilan LLM.

PaddleOCR 3.3.2 / PaddlePaddle 3.2.2 menjalankan
`PP-OCRv5_mobile_det` dan `latin_PP-OCRv5_mobile_rec` pada CPU, empat thread.
Semua 100 gambar menghasilkan teks nonkosong. OCR rata-rata 6.65
detik dan median 4.79 detik, di luar startup/download model.

## Interpretasi

OCR + LLM menghasilkan lebih banyak ekstraksi yang selesai dan lebih sedikit
timeout dalam eksperimen ini, tetapi rata-rata waktunya lebih lama. Hasil ini
belum mendukung klaim bahwa OCR membuat Tera lebih cepat. Jalur OCR tetap terpisah
dari aplikasi utama; tidak ada perubahan mode provider pada `.env`.

Perbaikan backend yang berlaku pada pemrosesan baru: vendor/tanggal yang hilang
atau diakui tidak terbaca dipertahankan sebagai null, hasil parsial disimpan, dan
klarifikasi diminta tanpa mengulang gambar yang sama sampai tiga kali. Tanggal
tebakan yang diakui lewat warning tidak diperlakukan sebagai bukti observasi.
Ini tidak menjamin mendeteksi kesalahan yang tidak diakui model.

## Batas dan kasus yang perlu diperiksa

- Banyak vendor/tanggal CORD sengaja disamarkan. Ekstraksi berhasil pada tabel
  berarti output dapat diparse, bukan semua field lengkap atau klaim layak approve.
  Ketepatan vendor, tanggal, item, kebijakan, dan keputusan tidak diukur.
- Sampel 0020: foto tampak bertotal 377,659; label asli 377859; vision 377659.
  OCR + LLM cocok dengan label 377859. Ini kandidat kesalahan anotasi, bukan
  alasan mengganti label secara otomatis; skor tetap dihitung dengan label asli.
- Sampel 0064: label 16000, hasil OCR + LLM 16. Kasus ini tetap dihitung sebagai
  ketidakcocokan dan menunjukkan risiko kesalahan digit/pemisah pada jalur OCR.
- Vision diukur ketika OCR lokal juga berjalan. Kontensi CPU dapat memengaruhi
  preprocessing. Jalur teks memakai cache OCR; penjumlahan waktu merupakan simulasi
  tahap berurutan, bukan latency request HTTP aplikasi yang sudah terintegrasi.
- Ini satu run lokal pada dataset publik, bukan estimasi akurasi dunia nyata atau
  jaminan perbaikan kecepatan pada server lain. Dataset test tidak dipakai training.

## Bukti lokal dan pengujian kode

Laporan rinci berada di `data/local/cord-v2-test/vision-fixed-100-run2.json`,
`ocr-text-100.json`, dan `ocr-summary.json`. Dataset/cache/laporan diabaikan Git.
Prosedur pengulangan ada di [panduan evaluasi](receipt-ocr-evaluation.md).

- Suite backend setelah perbaikan: 486 passed, 53 skipped. Integrasi yang skip
  belum terbukti pada run ini.
- Sepuluh tes evaluator tambahan lolos, termasuk format nominal, denominator
  label hilang, dan pengiriman teks tanpa gambar serta masking email.
- Regresi klarifikasi/replay lolos: input wajib tidak dilewati dan provider hanya
  dipanggil sekali ketika tanggal hilang.
- Frontend: 51 tes lolos; check 0 errors/0 warnings; build berhasil.
- `git diff --check` lolos. Main disinkronkan ke 1478007; perubahan lokal
  sebelumnya dikembalikan tanpa konflik, dengan stash tetap tersedia sebagai cadangan.
