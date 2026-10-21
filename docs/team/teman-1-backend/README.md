> Rencana ini sudah digantikan setelah koreksi pembagian tim. Pemilik menangani backend; Sheren dan Nisa menangani frontend. Ikuti [README frontend](../../../frontend/README.md) sebagai acuan terbaru.

# Tugas Sheren: backend laporan dan verifikasi data

Baca [panduan tim](../README.md) dan [project plan](../PROJECT-PLAN.md) terlebih dahulu. Tujuanmu adalah membuat laporan dapat dipercaya dan dipakai frontend. Endpoint dan pipeline sudah tersedia; lanjutkan implementasi tersebut.

## File yang menjadi tanggung jawabmu

| File/area | Penggunaan |
| --- | --- |
| `backend/app/api/reports.py` | Endpoint, response model, filter dan CSV saat ini |
| `backend/app/services/` | Tempat logika agregasi/filter laporan agar route tetap tipis |
| `backend/app/repositories/protocols.py`, `memory.py`, `sql.py` | Akses claim, extraction, decision, run dan signal; ubah hanya bila diperlukan |
| `backend/tests/test_reports_and_receipts.py` | Tes laporan yang sudah ada |
| `backend/tests/test_auth.py`, `test_claim_access.py`, `test_demo_mode.py` | Regresi hak akses; pertahankan |
| `docs/superpowers/specs/2026-10-01-expense-agent-backend-m8-reporting-spec.md` | Spesifikasi M8 yang perlu disinkronkan |
| `backend/app/api/auth.py` | Baca dependency admin; perubahan auth dikoordinasikan pemilik |

## B1. Sepakati kontrak sebelum coding

Saat ditinjau, summary berada di `GET /reports/summary` dan ekspor di `GET /reports/claims.csv`. Keduanya menerima `period_from`, `period_to`, dan `employee_id`. Filter `category` dan `status` dari spec belum ada.

- [ ] Catat response sekarang, query parameter dan header CSV di PR.
- [ ] Pertahankan endpoint CSV sekarang; selaraskan spec yang masih menyebut `export.csv`.
- [ ] Sepakati tambahan `status` dan `category` dengan Nisa.
- [ ] Pakai enam status dari `ClaimStatus`. Kategori harus mengikuti kategori backend yang sudah didukung.
- [ ] Tentukan kategori untuk klaim multi-nota serta klaim tanpa extraction. Usulan: cocok bila salah satu extraction pada run relevan berkategori tersebut; tanpa extraction tidak cocok bila filter kategori aktif.
- [ ] Sepakati run relevan, timezone tanggal, definisi otomatis/manual dan satuan temuan sebelum menulis tes.

Usulan definisi awal untuk ditinjau: otomatis/manual menghitung klaim terminal approved/rejected menurut keputusan aktif; klaim received/processing/needs_clarification/escalated dihitung pending. Tambahkan hitungan klarifikasi/eskalasi tanpa menghapus field lama. Temuan duplikat/anomali menghitung klaim dengan sinyal relevan, bukan seluruh sinyal lintas retry; tentukan apakah anomali harus melewati threshold. Durasi memakai run pemrosesan yang valid, dengan aturan retry/review dinyatakan eksplisit.

Keluaran B1: kontrak yang dipahami Nisa, contoh respons, serta tabel fixture dan nilai harapan. Usulan di atas belum merupakan perilaku yang diimplementasikan.

## B2. Koreksi agregasi dan lengkapi filter

Temuan kode saat ditinjau: `automated_claims = total_claims - manual_claims` turut menghitung klaim belum selesai sebagai otomatis. Estimasi penghematan memakai nilai itu dikali lima menit. Sinyal dihitung lintas seluruh run; pastikan arti angka sesuai label.

- [ ] Pindahkan aturan agregasi/filter ke service laporan; API menangani input/output.
- [ ] Gunakan filter bersama untuk summary dan CSV.
- [ ] Implementasikan tanggal inklusif, employee, status dan kategori sesuai B1.
- [ ] Rentang tanggal terbalik dan nilai filter tidak valid memberi error validasi terstruktur.
- [ ] Otomatis/manual tidak mengklaim pekerjaan selesai untuk klaim yang masih received.
- [ ] Retry atau keputusan reviewer tidak menggandakan jumlah klaim.
- [ ] Dataset kosong menghasilkan total nol; durasi tanpa data tetap null.
- [ ] Dokumentasikan estimasi waktu sebagai asumsi, bukan penghematan yang telah diukur.

Selesai bila tes membuktikan nilai expected untuk klaim received, processing, clarification, escalated, approved/rejected otomatis, dan approved/rejected reviewer, termasuk retry.

## B3. Perkuat ekspor dan tes regresi

- [ ] Pertahankan header CSV lama kecuali perubahan kontrak disepakati.
- [ ] Uji koma, kutip, newline, Unicode, nominal nol dan nominal kosong.
- [ ] Netralisasi nilai teks yang bisa dieksekusi sebagai formula spreadsheet; uji prefix berbahaya seperti =, +, -, @ dan karakter kontrol yang relevan.
- [ ] Pastikan kegagalan ekspor tidak mengubah claim, decision atau audit pemrosesan.
- [ ] Uji summary dan CSV tanpa sesi, dengan karyawan, dengan admin dan pada mode demo.
- [ ] Di mode normal, laporan/CSV tetap khusus admin; jangan membuka akses karyawan untuk menyelesaikan tombol UI.
- [ ] Uji kesamaan himpunan hasil summary/CSV pada kombinasi filter.

Buat tes terfokus baru bila file lama terlalu campur. Gunakan fixture sintetis dan repository terisolasi. Tambahkan tes failure yang dapat membuktikan data tidak berubah.

## Q1. Verifikasi storage

Jalankan suite rutin dengan mock dan memory/SQLite. Untuk PostgreSQL, koordinasikan server tes terpisah dan `TEST_POSTGRES_URL` dengan pemilik. Fixture membuat database unik `tera_test_*`; jangan mengganti fixture agar menulis ke database aplikasi.

Uji laporan pada repository SQL, restart/resume saat menunggu klarifikasi/review sesuai cakupan yang tersedia, dan catat hasil. Jika database belum tersedia, laporkan skip sebagai blocker validasi SQL.

## Urutan PR

1. PR B2: kontrak yang disepakati, service/filter/metrik dan regresi.
2. PR B3: CSV dan cakupan akses/failure.
3. Bukti Q1 serta dokumentasi backend pada PR terpisah jika lebih jelas.

Jalankan `python -m pytest` dari `backend/` dengan virtual environment aktif. Cantumkan hasil aktual dan skip pada PR. Serahkan kepada Nisa contoh JSON sintetis, query filter dan contoh CSV. Pipeline agent, model, konfigurasi auth dan deployment tetap dikoordinasikan pemilik.

