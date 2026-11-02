# Evaluasi pembacaan nota CORD

Dataset: [NAVER CLOVA CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2),
split test, 100 gambar. Foto dan label diekstrak dari file Parquet ke
`data/local/cord-v2-test/`. Dataset, cache model, teks OCR, dan laporan lokal
tidak dimasukkan ke Git. Model OCR sudah dilatih oleh pembuatnya; label CORD
test hanya dipakai untuk evaluasi, bukan training atau input provider.

## Perbaikan ekstraksi

Vendor dan tanggal yang tidak terbaca boleh bernilai `null`. Prompt melarang
tanggal tebakan/default. Bila respons mengakui tanggal atau vendor buram,
tidak terbaca, atau hasil estimasi, adapter mengubah field itu menjadi `null`
dengan confidence nol. Tanggal yang tidak kosong dan tidak diakui sebagai
tebakan tetap harus valid ISO; angka ekstrem dan respons malformed tetap gagal.
Ini bukan jaminan mendeteksi semua halusinasi: respons bisa salah tanpa mengakuinya.

Service menyimpan hasil parsial dan langsung meminta klarifikasi untuk field
yang hilang, tanpa mengulang gambar yang sama tiga kali. Pengguna dapat
mengunggah nota lebih jelas melalui alur klarifikasi yang ada. Nilai total yang
terbaca tidak dibuang. Klaim tersebut tidak otomatis disetujui.

## Menjalankan OCR lokal

Environment backend menggunakan Python 3.14. Eksperimen OCR memakai Python
3.12 terpisah agar runtime Paddle dan dependency eksperimen tidak mengubahnya.
Dengan interpreter Python 3.12 yang tersedia, jalankan dari root repository:

```powershell
python3.12 -m venv data/local/ocr-env/.venv
data/local/ocr-env/.venv/Scripts/python.exe -m pip install -r backend/requirements-ocr.txt
data/local/ocr-env/.venv/Scripts/python.exe backend/scripts/cache_cord_ocr.py
```

Sesuaikan `python3.12` dengan path interpreter di mesin. Model resmi
`PP-OCRv5_mobile_det` dan `latin_PP-OCRv5_mobile_rec` diunduh pada pemakaian
pertama. Cache berada di `data/local/paddle-model-cache/`. Inference memakai
CPU dengan empat thread, tanpa klasifikasi orientasi, unwarping atau MKLDNN.
Pilihan model dibekukan sebelum hasil benchmark dibandingkan.

Script membaca semua gambar manifest dan menyimpan teks, confidence, koordinat,
serta waktu per gambar ke `ocr/<id>.json`. File yang sudah ada digunakan kembali.
`ocr-summary.json` merangkum waktu dan kegagalan eksekusi. Jumlah OCR yang berhasil
tidak berarti tulisan atau total sudah benar. Waktu startup/download dipisahkan
dari waktu tiap gambar; pengukuran pertama masih dapat mengandung warm-up.

## Evaluasi LLM pada semua nota

Jalankan dari `backend/`, dengan provider lokal yang dikonfigurasi sudah aktif:

```powershell
.venv/Scripts/python.exe scripts/evaluate_cord.py --mode vision --workers 3 --output ../data/local/cord-v2-test/vision-fixed-100-new.json
.venv/Scripts/python.exe scripts/evaluate_cord.py --mode text --workers 3 --output ../data/local/cord-v2-test/ocr-text-100.json
```

Gunakan nama laporan baru pada setiap run. Script menolak menimpa laporan lama.
Kedua mode memakai model dan timeout dari konfigurasi lokal; fallback mock dan
retry dimatikan hanya untuk evaluasi. `.env` tidak diubah. Script memeriksa
koneksi provider sebelum mengirim dataset. Pemanggilan memakai adapter ekstraksi
dan validasi output yang sama, tanpa membuat klaim di database aplikasi.

Mode vision mengirim foto melalui batas privasi adapter. Mode text mengirim
teks OCR yang dimasking, tanpa mengirim gambar ke provider. Gold labels tidak
masuk prompt. Ekstraksi item belum didukung adapter ini: satu line item yang
dihasilkan adalah ringkasan nota, sehingga ketepatan item tidak diklaim.

Mode teks kini menyertakan kandidat nominal yang dinormalisasi dari OCR, dengan
konteks format angka nota Indonesia. Contoh: `16.000` menjadi kandidat `16000`,
`Rp50.000` menjadi `50000`, dan `RP38. 000` menjadi `38000`. Teks asli tetap
disertakan; digit tidak ditambah atau diganti. Konteks pemisah angka bukan bukti
bahwa mata uangnya pasti IDR.
Kontrak saat ini tetap mewajibkan currency berupa teks tiga huruf. Mode OCR
meminta penanda `XXX` dan warning `currency_unknown` bila mata uang tidak
diketahui, bukan null atau IDR yang dipaksakan. Penanda ini bukan mata uang
yang didukung untuk persetujuan klaim; evaluasi hanya menilai total.

Total keluaran LLM harus sesuai dengan salah satu kandidat angka yang terbaca.
Jika tidak, evaluasi mencatat `malformed_extraction` dengan stage
`ocr_amount_grounding`, tanpa mengalikan nilai dengan 1000 secara otomatis.
Ini memeriksa bukti numerik, bukan menjamin model memilih TOTAL ketimbang CASH
atau quantity. Total yang terpecah antarboks atau hanya bisa diturunkan lewat
penjumlahan item dapat ditolak; perlu perbaikan layout/fallback atau review,
bukan asumsi bahwa semua hasil lama pasti salah.

Regresi tertentu bisa dijalankan memakai `--sample-id 0064`; tanpa opsi itu,
script tetap memproses seluruh manifest. Setiap laporan mencatat hash script
agar protokol lama dan baru tidak tertukar. Run targeted yang berhasil bukan
bukti ketepatan pada 100 nota; gunakan laporan lengkap yang selesai untuk itu.

Respons mentah pada run awal tidak disimpan. Karena itu, untuk kasus `0064`
yang pasti benar adalah OCR `16.000` dan keluaran terstruktur lama `16`;
belum bisa dipastikan apakah model menulis angka 16 atau parser mengonversi
string lokal `"16.000"` menjadi Decimal 16. Tes regresi melindungi keduanya.
Probe terbatas pada run normalisasi v2 membuktikan satu kegagalan parsing
berasal dari currency null yang ditolak schema, sementara total sudah benar.
Probe hanya menampilkan tipe/lokasi field, tanpa menyimpan raw output.

Metrik membandingkan total numerik dengan `gt_parse.total.total_price`. Format
rupiah dan pemisah ribuan/desimal dinormalisasi. Nota tanpa label total tetap
diproses tetapi tidak masuk denominator; tidak ada label yang ditebak dari
cash/change. Kegagalan ekstraksi pada nota berlabel tetap menurunkan tingkat
keberhasilan. Jika seluruh provider gagal, akurasi tidak dilaporkan sebagai nol.

Tiga request berjalan bersamaan; latency ini tidak langsung setara dengan
pilot 10 nota sebelumnya yang berurutan. Mode text menambahkan waktu OCR yang
tercatat ke waktu adapter, tetapi tidak memasukkan startup/download model atau
waktu tunggu antrean sebagai latency per nota. Ini simulasi tahap berurutan dari
cache, bukan pengukuran request HTTP aplikasi yang sudah diintegrasikan.
Pada run awal 100 nota, cache OCR dibuat bersamaan dengan evaluasi vision;
kontensi CPU dapat memengaruhi preprocessing lokal. Angka waktu adalah bukti
eksperimen lokal, bukan jaminan latency deployment.

CORD menyamarkan banyak nama toko dan tanggal. Label itu tidak digunakan sebagai
pembanding field pada evaluasi ini. Tanggal kosong/klarifikasi bukan kegagalan
pembacaan total. Hasil tidak mengukur ketepatan approve/reject, autentikasi,
policy, atau ML anomali.

Pemeriksaan visual sampel `0020` menunjukkan kemungkinan kesalahan anotasi:
foto tampak bertotal `377,659`, sementara label asli menyebut `377859`.
Vision menghasilkan `377659`. Temuan ini memerlukan review manual dan tidak
digunakan untuk mengubah label, memilih ulang sampel, atau menaikkan skor.
Kecocokan dengan label tidak selalu sama dengan kebenaran pada foto.

## Validasi kode

Tes regresi memeriksa tanggal null/kosong, penolakan placeholder yang diakui,
penyimpanan bukti parsial, dan klarifikasi tanpa pemanggilan model berulang.
Tes evaluasi memeriksa variasi format nominal dan perlakuan label yang hilang.
Laporan live hanya boleh dipakai untuk membandingkan model bila provider benar-benar
merespons; kegagalan koneksi harus dilaporkan terpisah.
