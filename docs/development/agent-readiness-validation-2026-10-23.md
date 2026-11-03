# Hasil validasi penguatan Tera, 23 Oktober 2026

Implementasi aplikasi: `64768a7d89da7e28c630ee398ecf40ba7b078760`. Perluasan verifier restore untuk kebijakan terbit: `9d338e4`. Branch `feat/agent-readiness` bergantung pada `fix/role-workspaces` (PR #34). Hasil di bawah adalah pelaksanaan aktual pada workspace, bukan target atau proyeksi.

## Hasil

| Pemeriksaan | Hasil aktual | Batas bukti |
|---|---|---|
| Backend penuh | **624 passed, 1 skipped**, 215,21 detik | Skip hanya tes untuk server tanpa pgvector; server tes ini memiliki extension |
| Frontend | **83 tes lulus**, check **0 error/0 warning**, build adapter-node berhasil | Pemeriksaan otomatis lokal |
| Evaluasi graph | **18/18**, **0 false approvals** | Provider mock, kebijakan local, anomaly rules, dataset sintetis berlabel |
| Live agent | **approved**, total **60000**, 1 provider call, **12253 ms**, tanpa fallback mock | Satu PNG sintetis, storage memory terisolasi; bukan ukuran akurasi umum |
| Token live | Input **4574**, output **128**, total **4702** | Usage callback provider; tarif/biaya aktual tidak tersedia |
| Dump/restore | **passed**, 2 klaim; nota, keputusan, checkpoint, notifikasi, 6 versi kebijakan dan vector-schema probe pulih | Dua database disposable; versi custom efektif tetap v2; replay tidak menduplikasi keputusan |
| Docker | Kedua image berhasil dibangun; backend **healthy** | Default runtime local/rules; model ML/RAG opsional memerlukan provisioning sendiri |
| Smoke container akhir | Readiness dan halaman notifikasi/kebijakan/laporan HTTP **200**; 3 fixture berakhir approved/needs_clarification/escalated melalui proxy frontend | Demo memory pada loopback 5177, bukan deployment publik |
| Audit antarmuka | **0 temuan baru** pada scope yang diperiksa | [Audit after](./ui-audit-2026-10-23.md), viewport 1440×1000 dan 375×812 |

Evaluator offline mencatat revision `64768a7` dan `working_tree_dirty=true` karena dokumen/perubahan lokal masih ada. Latensi mock p50 11 ms dan p95 117 ms pada run tersebut tidak mewakili latensi provider live. Dua kasus error yang diharapkan termasuk dalam 18 kasus, bukan dihapus dari denominator. Output JSON rinci ada pada `backend/data/local/evaluation/` yang diabaikan Git.

Provider live melaporkan identitas model konfigurasi `ag/gemini-3.8-flash-medium`. Nama tersebut adalah identifier endpoint, bukan verifikasi independen model di balik provider. Hasil live dicatat 02:28:50 UTC; restore terakhir 02:43:47 UTC. Endpoint sempat tidak tersedia sebelum pengguna menyalakannya kembali; run sukses dilakukan setelah itu.

## Perilaku agent yang dibuktikan

Workflow menggunakan LangGraph untuk ekstraksi, validasi, pengambilan kebijakan, anomali, keputusan, interrupt/resume klarifikasi dan recovery. Evaluasi mencakup ambiguitas total, aritmetika independen, tanggal masa depan, kebijakan tidak tersedia, provider timeout, klarifikasi berulang, duplikasi, anomali dan replay. Nilai numeric yang sudah diparse tidak dikali seribu; bukti line item turunan tidak dianggap pemeriksaan independen.

Notifikasi dan versi kebijakan disimpan di migrasi additive v4. Pengujian memory/SQLite/PostgreSQL memeriksa akses pengguna, CAS, publikasi bersamaan, immutability, supersession, gap tanggal, idempotent baseline import, reminder/read state dan claim lock. Reviewer standards/spec menemukan masalah normalisasi term, pemilihan baseline, interval kebijakan dan konkurensi inbox selama pengerjaan; semuanya diperbaiki dengan regresi sebelum suite akhir.

Browser lokal menjalankan import baseline, simpan draft, konfirmasi terbit dua langkah, audit, tambah/hapus/ganti aturan, tandai dibaca dan refresh, navigasi ke review beserta gambar nota, alasan wajib, keputusan tersimpan, notifikasi terselesaikan, laporan serta unduh CSV tiga baris sintetis. Jalur backend mati/pulih, retry dan inbox kosong juga diuji. Screenshot hanya menampilkan data sintetis.

## Yang belum selesai di lingkungan eksternal

- **Deployment publik:** host/domain HTTPS belum ditentukan. Image, Compose, migrasi dan [runbook](agent-deployment.md) tersedia; tidak ada URL production yang diklaim aktif.
- **Akun nyata:** halaman login normal tersedia lokal pada `http://127.0.0.1:5176/login`, menunggu pemilik akun menyelesaikan login. Tes JWT dan demo tidak menggantikan bukti browser login/logout akun nyata.
- **UAT:** [panduan sesi](agent-uat.md) dan [test plan](agent-readiness-test-plan.md) tersedia, tetapi sesi karyawan/finance belum dilakukan dan hasilnya tidak direkayasa.
- **Operasi nyata:** jadwal backup, retensi, alerting dan load staging harus disesuaikan dengan lingkungan yang dipilih. Durasi/biaya/penghematan bisnis nyata belum diukur.

Tidak ada nota pribadi atau secret dimasukkan ke Git. `.env` dan database aplikasi tidak diubah untuk pengujian ini. Perubahan pengguna pada `docs/admin-login.md`, `.codex/`, `.impeccable/` dan `PRODUCT.md` tidak termasuk commit implementasi. Migrasi v4 additive, tetapi downgrade backend lama memerlukan pemeriksaan kompatibilitas payload JSON baru; lihat rollback pada test plan.
