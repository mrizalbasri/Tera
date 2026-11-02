# Rencana Penguatan Tera untuk Lomba AI Agent

Tanggal penyusunan: 18 Oktober 2026.

Dokumen ini merangkum rekomendasi dari pembahasan scope, persyaratan teknis, dan kriteria penilaian GTNIC 2026 yang dibagikan. Isinya merupakan usulan pengembangan, bukan daftar fitur yang semuanya sudah selesai atau jaminan hasil lomba. Belum ada perubahan kode aplikasi berdasarkan rencana ini.

## 1. Fokus utama

**Perkuat Tera sebagai agent pemeriksa reimbursement yang mampu menangani kendala, melanjutkan pekerjaan, dan menunjukkan dasar keputusannya.**

Kategori utama Tera adalah **AI Finance Assistant**, dengan pemrosesan dokumen sebagai kemampuan pendukung. Target penggunanya adalah karyawan yang mengajukan reimbursement dan tim keuangan yang memeriksa klaim.

Masalah yang diselesaikan: membaca nota, memeriksa data dan kebijakan, mencari indikasi duplikasi atau anomali, serta meminta informasi tambahan ketika bukti belum cukup.

### Rumusan scope untuk proposal

> Tera adalah AI Agent untuk pemeriksaan reimbursement karyawan yang mengoordinasikan ekstraksi bukti pengeluaran, validasi data, pencarian kebijakan, dan pemeriksaan risiko. Sistem menentukan tindak lanjut berdasarkan hasil pemeriksaan, meminta klarifikasi ketika informasi belum lengkap, serta mengeskalasi kasus yang membutuhkan pertimbangan manusia. Setiap tahap menghasilkan status, alasan, dan jejak audit yang dapat ditinjau oleh karyawan maupun tim keuangan.

Pembayaran melalui bank, perpajakan, payroll, dan akuntansi perusahaan secara menyeluruh berada di luar scope usulan ini.

## 2. Dasar yang sudah dimiliki

Berdasarkan README, kode workflow, dan laporan pengujian yang diperiksa dalam percakapan:

| Kemampuan | Status yang perlu dipahami |
| --- | --- |
| Ekstraksi nota | Tersedia provider mock dan vision live; kesiapan demo bergantung pada konfigurasi yang digunakan |
| Validasi dan evaluasi kebijakan | Sudah menjadi bagian alur pemeriksaan |
| Klarifikasi dan review manusia | Sudah memiliki tahap tunggu dan kelanjutan proses melalui LangGraph |
| Penyimpanan dan audit | Tersedia; laporan backend mencatat pengujian persistence dan recovery |
| RAG kebijakan | Opsional; perlu model, indeks, konfigurasi, dan bukti retrieval yang berjalan |
| ML anomali | Opsional; perlu model hasil training lokal; metrik sintetis bukan akurasi fraud dunia nyata |
| OCR + LLM teks | Masih jalur eksperimen evaluator; belum menggantikan jalur utama aplikasi |
| Deployment publik | Belum terbukti dalam laporan yang diperiksa |
| Analytics | README menyebut masih ada metrik prototipe yang perlu diselaraskan |

Laporan lama tidak otomatis membuktikan kondisi working tree terbaru. Pengujian perlu dijalankan kembali pada versi yang akan digunakan untuk demo.

## 3. Hubungan dengan penilaian lomba

Bobot berikut berasal dari slide penilaian yang dibagikan pengguna.

| Kriteria | Bobot | Fokus penguatan Tera |
| --- | ---: | --- |
| Kapabilitas dan otonomi agen | 25% | Menangani kendala sesuai kondisi dan melanjutkan proses setelah klarifikasi |
| Penalaran, perencanaan, dan keputusan | 15% | Menghubungkan data, aturan, dan temuan dengan tindak lanjut yang dapat diperiksa |
| Penggunaan alat dan eksekusi tindakan | 15% | Memperlihatkan pemanggilan ekstraksi, retrieval, pemeriksaan risiko, dan perubahan status |
| Arsitektur teknis dan rekayasa sistem | 15% | Menunjukkan checkpoint, recovery, batas retry, persistence, keamanan, dan hasil pengujian |
| Inovasi dan kreativitas | 10% | Penanganan kasus reimbursement sulit dengan bukti keputusan yang jelas |
| Dampak masalah dan nilai bisnis | 10% | Mengukur waktu pemeriksaan dan kebutuhan intervensi manusia |
| Pengalaman dan kemudahan pengguna | 5% | Memudahkan karyawan menjawab klarifikasi dan reviewer memahami temuan |
| Demonstrasi, presentasi, dan dokumentasi | 5% | Menyediakan demo publik serta dokumentasi yang sesuai versi aplikasi |

Sebanyak 70% bobot berada pada empat kriteria pertama. Karena itu, kemampuan agent dan bukti perilakunya menjadi prioritas pengerjaan.

## 4. Perbaikan sebelum menambah fitur

### A. Buktikan demo publik dengan provider live

- [ ] Web dan backend dapat diakses melalui URL demo.
- [ ] Login karyawan dan reviewer berfungsi dengan hak akses yang sesuai.
- [ ] Nota sintetis diproses menggunakan provider live.
- [ ] Klarifikasi dan review dapat diselesaikan melalui antarmuka.
- [ ] Data tetap tersedia setelah restart jika demo memakai penyimpanan SQL.
- [ ] Kegagalan provider menghasilkan status dan tindakan lanjutan yang jelas.
- [ ] Repository dan panduan akses tersedia sesuai ketentuan lomba.

Audit UI terakhir menggunakan provider mock. Hasil tersebut membuktikan bagian alur UI yang diuji, tetapi belum membuktikan integrasi live di deployment publik.

### B. Perkuat pemeriksaan nominal

Evaluasi eksperimen menemukan risiko pemisah ribuan, digit yang salah, dan pemilihan subtotal sebagai total.

- [ ] Uji total, subtotal, pajak, diskon, dan format nominal Indonesia.
- [ ] Simpan temuan ketidaksesuaian agar reviewer dapat memeriksanya.
- [ ] Arahkan nominal ambigu ke klarifikasi atau review.
- [ ] Jangan menganggap angka yang muncul dalam OCR pasti merupakan total.

### C. Selaraskan metrik dan dokumentasi

- [ ] Ganti metrik prototipe dengan data aktual atau beri label contoh.
- [ ] Bedakan fitur aktif, opsional, dan eksperimen di proposal.
- [ ] Catat versi Git dan konfigurasi nonrahasia yang digunakan untuk demo.
- [ ] Jalankan kembali pengujian yang relevan pada versi tersebut.

## 5. Tambahan yang direkomendasikan

### Prioritas 1: Penanganan kendala secara adaptif

**Tujuan:** Tera memilih tindakan lanjutan berdasarkan masalah yang ditemukan. Pengembangan ini memperluas klarifikasi dan retry yang sudah tersedia.

| Kondisi | Perilaku yang diusulkan | Batasnya |
| --- | --- | --- |
| Tanggal tidak terbaca | Meminta tanggal atau bukti pengganti sesuai kebutuhan kebijakan | Jangan mengubah jawaban karyawan menjadi bukti yang sudah terverifikasi |
| Total dan item tidak cocok | Memeriksa ulang bagian nominal dan mencatat perbedaan | Hasil ambigu tetap membutuhkan klarifikasi/review |
| Hasil vision ambigu | Mencoba OCR sebagai pemeriksaan tambahan setelah integrasinya diuji | Dua hasil berbeda tidak boleh dipilih sembarangan |
| Kebijakan tidak tersedia | Menyimpan alasan dan meneruskan ke reviewer | Jangan menyetujui klaim tanpa dasar kebijakan yang diperlukan |
| Provider timeout | Retry terbatas lalu menyimpan kegagalan untuk tindakan lanjutan | Hindari pengulangan tanpa batas dan keputusan ganda |

Kriteria selesai:

- [ ] Setiap kondisi memiliki tindakan dan alasan yang terlihat.
- [ ] Batas retry dan klarifikasi ditentukan secara eksplisit.
- [ ] Proses dapat dilanjutkan setelah informasi tersedia.
- [ ] Tahap yang sudah selesai tidak menimbulkan efek ganda ketika diulang.
- [ ] Jalur gagal menghasilkan status akhir atau eskalasi yang jelas.

LangGraph mengatur alur proses. Klaim perencanaan dinamis hanya digunakan jika implementasi memang memilih atau menyusun langkah berdasarkan kondisi, dan perilaku tersebut dapat dibuktikan.

### Prioritas 2: Tampilan bukti keputusan

**Tujuan:** karyawan, reviewer, dan juri dapat memahami dasar tindak lanjut tanpa membaca seluruh log teknis.

Ringkasan setiap klaim memuat:

- Data relevan hasil ekstraksi dan pengajuan.
- Aturan yang digunakan, sumber, dan versi kebijakan.
- Temuan validasi atau indikasi risiko.
- Tindakan yang diambil dan alasannya.
- Informasi yang masih dibutuhkan.
- Penanda asal data: ekstraksi model, jawaban karyawan, atau konfirmasi reviewer.

Contoh ilustrasi, bukan hasil klaim nyata:

> **Temuan:** nominal klaim melampaui batas kebijakan yang berlaku.
>
> **Bukti:** total hasil ekstraksi dan nominal pengajuan.
>
> **Aturan:** tampilkan aturan, sumber, dan versinya.
>
> **Tindakan:** tampilkan keputusan sesuai aturan dan kewenangan yang dikonfigurasi.

Penjelasan harus bersumber dari hasil pemeriksaan terstruktur. Jika model membantu menyusun kalimat, model tidak boleh menambahkan aturan atau alasan baru. Yang ditampilkan adalah bukti dan alasan keputusan, bukan proses berpikir internal model.

### Prioritas 3: Paket evaluasi yang dapat diulang

**Tujuan:** membuktikan kualitas keputusan dan manfaat operasional Tera.

Siapkan kasus sintetis berlabel untuk klaim valid, melampaui batas, duplikat, nota buram, informasi kurang, nominal ambigu, kebijakan tidak tersedia, dan provider gagal. Tentukan hasil yang diharapkan sebelum menjalankan evaluasi.

| Metrik | Cara membaca |
| --- | --- |
| Kesesuaian keputusan | Keputusan yang sesuai label dibanding seluruh kasus berlabel; kegagalan dilaporkan terpisah dan tetap terlihat |
| Salah approve | Kasus yang seharusnya tidak disetujui tetapi mendapat persetujuan |
| Intervensi manusia | Jumlah kasus dan jumlah tindakan yang membutuhkan karyawan/reviewer |
| Waktu pemeriksaan | Pisahkan waktu komputasi aktif dari waktu menunggu manusia; laporkan median dan kasus lambat |
| Keberhasilan kelanjutan proses | Kasus yang selesai setelah klarifikasi atau kegagalan sementara |
| Biaya pemrosesan | Catat penggunaan provider bila tersedia dan jelaskan metode estimasinya |

Bandingkan waktu manual dan Tera menggunakan kasus yang sama. Catat jumlah kasus, kondisi pengujian, versi aplikasi, dan konfigurasi. Hasil dataset sintetis harus diberi label sebagai hasil pengujian sintetis.

Evaluasi CORD yang sudah ada mengukur ekstraksi dan kecocokan total. Angkanya tidak boleh disebut sebagai akurasi keputusan reimbursement.

## 6. Skenario demo

### Skenario utama: klaim membutuhkan informasi tambahan

1. Karyawan mengunggah nota sintetis yang sengaja memiliki informasi kurang jelas.
2. Tera mengekstrak data dan menunjukkan informasi yang belum cukup.
3. Tera meminta klarifikasi yang sesuai masalah.
4. Karyawan mengirim jawaban atau bukti tambahan.
5. Tera melanjutkan proses dan memeriksa kebijakan serta risiko.
6. Antarmuka menampilkan keputusan/tindak lanjut beserta buktinya.

Skenario ini memperlihatkan tujuan, kendala, tindakan agent, interaksi manusia, dan hasil akhir.

### Skenario pendukung

- Klaim lengkap dan sesuai kebijakan: menunjukkan pemrosesan rutin sampai keputusan.
- Klaim dengan indikasi duplikasi: menunjukkan temuan dan penanganan sesuai aturan.
- Gangguan provider: menunjukkan retry berbatas dan pemulihan tanpa duplikasi keputusan.

Pilih skenario pendukung sesuai durasi video. Jika kegagalan disimulasikan, beri label simulasi saat presentasi.

## 7. Urutan pengerjaan

| Urutan | Hasil yang dituju |
| --- | --- |
| 1 | Demo publik dengan provider live dan akses pengguna yang berfungsi |
| 2 | Tampilan bukti keputusan dari data yang sudah tersedia |
| 3 | Penanganan kendala adaptif, dimulai dari satu kasus yang paling relevan |
| 4 | Evaluasi keputusan, intervensi manusia, dan waktu pemeriksaan |
| 5 | Penyelarasan dashboard, README, proposal, dan video demo |

Jika waktu terbatas, dahulukan deployment live dan bukti keputusan. Tambahkan pemeriksaan OCR kedua setelah hasil pengujian mendukungnya.

## 8. Pengembangan yang ditunda

Untuk menjaga fokus, tunda pembayaran bank, integrasi ERP besar, voice assistant, serta penambahan banyak agent tanpa pembagian tugas yang jelas. Integrasi sistem keuangan bisa menjadi tahap berikutnya setelah pemeriksaan klaim terbukti konsisten.

## 9. Pesan utama presentasi

> Tera membantu tim keuangan menyelesaikan pemeriksaan reimbursement, menangani informasi yang kurang, dan memusatkan review manusia pada klaim yang membutuhkan pertimbangan.

Tunjukkan perilaku aplikasi dan hasil pengukuran sebagai bukti. Gunakan istilah otonomi, reasoning, RAG, dan tool calling sesuai kemampuan yang benar-benar aktif pada demo.

## 10. Referensi proyek

- [README Tera](../README.md): scope, fitur, mode konfigurasi, dan batas sistem.
- [Validasi kesiapan backend](development/backend-readiness-validation.md): bukti pengujian persistence, recovery, transaksi, dan akses.
- [Evaluasi ekstraksi nota](development/receipt-ocr-evaluation-results-2026-10-17.md): perbandingan vision dan OCR + LLM serta batas pengukuran.
- [Evaluasi normalisasi nominal](development/receipt-number-format-fix-2026-10-17.md): kesalahan separator, pemilihan subtotal, dan hasil eksperimen lanjutan.
- [Audit UI](development/ui-audit-2026-10-18.md): alur yang diuji melalui browser dengan provider mock.

Panduan lomba dan slide yang dibagikan pengguna menjadi referensi persyaratan serta bobot penilaian. Ketentuannya diperlakukan sebagai bahan analisis; dokumen ini tidak melakukan submission atau publikasi.
