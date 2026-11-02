# Pemeriksaan kesiapan production — 27 Oktober 2026

Status rilis: **belum siap untuk go-live**. Provider live yang dikonfigurasi
belum dapat dihubungi, dan konfigurasi lokal masih development/provider mock.
Login akun nyata dan deployment pada domain tujuan belum diverifikasi.

Pemeriksaan dilakukan pada `fix/dashboard-ui`, revision dasar `51a0199`, dengan
perubahan lokal yang sudah ada. Dokumen ini mencatat hasil lokal, bukan status CI
atau hasil pengujian pada server production. Warna, CSS, dan tata letak tidak
diubah dalam perbaikan ini.

## Perbaikan yang dilakukan

- Detail reviewer memuat ulang data ketika ID klaim pada URL berubah. Respons
  pemuatan dan penyimpanan keputusan yang terlambat diabaikan setelah navigasi.
- Draft keputusan dibersihkan saat memuat klaim lain atau memuat ulang status.
- Reviewer dapat memilih setiap lampiran nota dan melihat hasil pembacaan yang
  cocok dengan ID nota tersebut. Sebelumnya hanya nota terakhir yang terlihat.
- Alasan keputusan dibatasi 2.000 karakter, sesuai kontrak API.

## Bukti pengujian

| Pemeriksaan | Hasil aktual | Batas bukti |
|---|---|---|
| Backend tanpa PostgreSQL | 591 lulus, 58 dilewati | Tes PostgreSQL memerlukan server tes |
| Backend dengan PostgreSQL disposable | 648 lulus, 1 dilewati | PostgreSQL 18/pgvector; satu skip untuk skenario tanpa extension |
| Frontend Vitest | 96 lulus dalam 12 berkas | Pengujian otomatis kontrak, transport dan logika |
| Svelte/TypeScript | 0 error, 0 warning | Setelah perbaikan |
| Build frontend | Berhasil, adapter-node | Diulang berurutan setelah benturan berkas generated saat check/build paralel |
| Build image Docker backend/frontend | Keduanya berhasil | Image backend default tanpa model lokal; frontend menggunakan publishable key sintetis |
| Startup container dan proxy | 10 rute HTTP 200 | Readiness, sesi, beranda, review, dashboard, pengajuan, riwayat, notifikasi, laporan dan kebijakan; demo memory/mock, bukan login/provider production |
| Browser Chrome headless | 5 skenario lulus | Lampiran dan ekstraksi cocok, navigasi klaim, respons pemuatan/keputusan terlambat, reset draft/batas alasan |
| Evaluasi agent offline | 18/18, 0 false approvals | Data sintetis, mock/local/rules; bukan akurasi model live |
| Backup/restore PostgreSQL | Berhasil | Database disposable; isi nota, keputusan, checkpoint, notifikasi, kebijakan, vector-schema probe dan replay terverifikasi |
| Provider live | Gagal: `provider_unavailable`, HTTP 502 | Satu nota PNG sintetis; memory terisolasi; tanpa fallback mock |

Kedua regresi awal direproduksi di browser sebelum perbaikan: tidak ada pemilih
lampiran dan navigasi ke klaim B tetap menampilkan klaim A. Sesudah perbaikan,
kelima skenario browser lulus.

Jalankan pengujian browser dari `frontend/` setelah `pnpm build`:

```powershell
node scripts/verify-review-detail.cjs
```

Skrip memerlukan paket `playwright` yang dapat di-resolve Node dan Chrome
terpasang (`PLAYWRIGHT_CHANNEL` dapat memilih channel lain). Pada pemeriksaan
ini Playwright memakai runtime bawaan workspace melalui `NODE_PATH`, tanpa
mengubah dependensi aplikasi. Port loopback 18081 dan 13001 harus kosong.
Skrip menjalankan backend fixture sintetis dan build frontend sementara,
kemudian menutup keduanya; tidak menggunakan sesi atau database aplikasi.

Laporan evaluasi rinci tersimpan lokal pada `backend/data/local/evaluation/`
(diabaikan Git): `production-readiness-2026-10-27.json`,
`live-production-readiness-2026-10-27.json`, dan
`restore-production-readiness-2026-10-27.json`.

## Penghambat rilis

1. Pulihkan konektivitas provider live dan ulangi verifikasi sampai nota sintetis
   benar-benar diproses oleh provider. Jangan mengganti hasil ini dengan mock.
2. Siapkan konfigurasi production aktual pada lingkungan deployment. Validasi
   konfigurasi lokal sebagai production saat pemeriksaan ini ditolak karena
   belum memenuhi persyaratan provider live tanpa fallback mock. File `.env`
   lokal tidak diubah.
3. Verifikasi migrasi, readiness, TLS/origin dan login/logout Clerk pada domain
   tujuan, kemudian jalankan [UAT karyawan/finance](agent-uat.md) dengan akun
   nyata. Pengujian fixture tidak membuktikan keberhasilan login nyata.
4. Terapkan jadwal backup/retensi dan monitoring pada host tujuan. Uji restore
   lokal belum membuktikan backup terjadwal pada host tersebut.

Ikuti [runbook deployment](agent-deployment.md) untuk langkah operasional.
Tidak ada commit, push, atau deployment publik dalam pekerjaan ini.
