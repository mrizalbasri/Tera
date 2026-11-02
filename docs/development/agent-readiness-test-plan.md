# Test Plan — Penguatan Tera

| | |
|---|---|
| Sistem | Tera, workflow AI agent reimbursement |
| Versi yang diuji | Implementasi `64768a7`; hasil akhir dicatat pada laporan validasi |
| Pelaksana | Pengujian otomatis dan browser pada workspace; UAT oleh pengguna masih terpisah |

## 1. Strategi Pengujian Bertingkat

| Tingkat | Cakupan | Pelaksanaan |
|---|---|---|
| Unit | Nominal, term kebijakan, interval waktu dan aturan keputusan | pytest dan Vitest |
| Integrasi | API, graph, memory/SQLite/PostgreSQL, migrasi, privacy dan persistence | Suite backend dengan PostgreSQL pgvector disposable |
| Sistem | Editor kebijakan, inbox, review, CSV, viewport dan container | Browser lokal dan HTTP melalui proxy container |
| UAT | Penyelesaian tugas oleh karyawan/finance nyata | Panduan agent-uat.md; belum dianggap lulus tanpa sesi |

## 2. Lingkup

Uji mencakup semua paket kode yang disetujui: agent, nominal, evaluasi, notifikasi, kebijakan berversi, metrik, CI, packaging dan restore. Uji provider menggunakan satu nota sintetis live dan matriks terpisah dengan provider mock. Public hosting, real-account login/logout, beban production dan dampak bisnis belum dibuktikan hanya oleh tes lokal.

## 3. Test Environment

| Item | Nilai |
|---|---|
| Backend/browser QA | Loopback port 8011 / frontend 5175, mode demo terisolasi |
| Login normal | Backend memory 8012 / frontend 5176, Clerk nyata, menunggu pemilik akun |
| Database integrasi | Container PostgreSQL 18 dengan pgvector, loopback 55440, database fixture disposable |
| Container aplikasi | Loopback frontend 5177, backend internal, fixture memory/demo |
| Data | Nota/identitas sintetis; tidak ada nota asli di fixture atau commit |
| Browser | In-app browser, viewport 375×812 dan 1440×1000 |

## 4. Test Case

| Kode | Skenario | Langkah dan hasil yang diharapkan | Prioritas |
|---|---|---|---|
| TC-01 | Batas nominal dan ketidakpastian | Total ambigu/breakdown tidak cocok tidak auto-approve; angka numeric 16 tidak dikali 1000 | Tinggi |
| TC-02 | Tanggal setelah persistence | Serialize/restore JSON lalu validasi tanggal masa depan; tetap ada finding pemblokir | Tinggi |
| TC-03 | Agent lanjut/berhenti | Klarifikasi dapat dilanjutkan; batas putaran mengeskalasi; replay tidak mengulang keputusan | Tinggi |
| TC-04 | Provider live | PNG sintetis total 60000 diproses tanpa fallback mock sampai keputusan; usage dicatat bila tersedia | Tinggi |
| TC-05 | Kebijakan | Draft/CAS, publish bersamaan, immutable, interval, supersession dan import baseline tidak melemahkan custom | Tinggi |
| TC-06 | Kebijakan tidak berlaku | Gap tanggal masuk review dengan policy_version null; tidak mengarang versi | Tinggi |
| TC-07 | Notifikasi | Idempotent, read persistent, reminder 24 jam, resolved sesuai status, akses asing 404, inbox tetap terbuka ketika klaim busy | Tinggi |
| TC-08 | Otorisasi | Tanpa sesi 401/redirect; member tidak dapat mengelola kebijakan; ID browser tidak menambah kewenangan | Tinggi |
| TC-09 | Metrik | Interval overlap tidak dihitung dua kali; waktu manusia dipisah; token dari callback, biaya tidak dikarang | Tinggi |
| TC-10 | Browser | Import, simpan/publish/audit; tanda baca inbox; review dari notif; refresh; CSV; menu Escape; mobile tanpa overflow | Tinggi |
| TC-11 | Operasi | Build Node/container; readiness; mutasi API melalui proxy; dump/restore domain/file/checkpoint/operational/vector probe | Tinggi |
| TC-12 | Penerimaan eksternal | Login/logout akun nyata, deployment HTTPS, UAT pengguna | Tinggi; membutuhkan lingkungan/pengguna |

Status aktual dan jumlah tes tidak disalin sebagai target lulus; lihat laporan validasi akhir.

## 5. Bug Tracking

Temuan review selama implementasi meliputi term kebijakan tidak dinormalisasi, kebijakan tanpa tanggal akhir tidak bisa diganti, baseline import mengalahkan custom, gap tanggal gagal tanpa review, dan inbox tertahan claim lock. Semuanya mendapat koreksi dan tes regresi. Kesalahan fixture tes lama juga diperbaiki: kredensial PostgreSQL mengikuti fixture, dan simulasi migrasi v2 menghapus marker versi setelah v2.

Tidak ada issue eksternal yang dibuat otomatis dari daftar ini; hasil review dan pengujian menjadi bukti pada PR.

## 6. Kriteria Lulus

Kode dapat direview setelah seluruh tes relevan lulus, tidak ada temuan pemblokir yang diketahui pada paket implementasi, dan batas verifikasi ditulis. Go-live tetap membutuhkan TC-12 dan pemeriksaan konfigurasi actual. Tes skipped harus disertai alasan; conditional skip pada server yang sudah memiliki pgvector berbeda dari integrasi yang belum tersedia.

## 7. Strategi Konversi / Cutover

Gunakan pilot satu perusahaan setelah staging lolos. Backup seluruh database, jalankan migrasi v4 sebelum worker, bangun frontend dengan public key/domain yang sesuai, lalu jalankan smoke test dengan akun uji. Jadwal publik belum ditentukan karena host/domain belum diberikan. Jangan menganggap container lokal sebagai URL publik atau menyalin data demo sebagai data pelanggan.

## 8. Rollback Plan

Hentikan mutasi, simpan backup baru, kemudian tentukan kembali versi frontend/backend yang kompatibel. Migrasi v4 bersifat additive, tetapi payload JSON baru memakai extra=forbid pada aplikasi lama; rollback backend dapat gagal membaca field tambahan. Hindari downgrade kode tanpa migrasi kompatibilitas yang diuji. Untuk pemulihan penuh, gunakan backup domain/checkpoint/RAG dari waktu yang sama ke database terpisah, verifikasi readiness dan replay, baru arahkan traffic. Keputusan reviewer yang sudah commit tidak dibatalkan diam-diam.
