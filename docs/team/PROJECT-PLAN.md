> Rencana ini sudah digantikan setelah koreksi pembagian tim. Pemilik menangani backend; Sheren dan Nisa menangani frontend. Ikuti [README frontend](../../frontend/README.md) sebagai acuan terbaru.

# Project Plan Tera: penyelesaian laporan dan kesiapan demo

| Atribut | Rencana |
| --- | --- |
| Proyek | Tera / Expense Agent |
| Koordinator | Pemilik proyek; nama PIC belum diberikan |
| Tim | Pemilik proyek + Sheren + Nisa |
| Durasi | Usulan 10 hari kerja efektif sejak baseline siap; bukan janji tanggal |
| Status | Draft pembagian kerja, 14 Oktober 2026 |

## 1. Tujuan & Ringkasan

Menyelesaikan laporan operasional di atas pipeline yang sudah ada, membuat frontend memakai kontrak yang sama, dan membuktikan alur reimbursement dengan data sintetis. Teman baru memperoleh tugas terbatas yang dapat dikerjakan dan ditinjau tanpa menulis ulang agent.

## 2. Scope

In-scope: koreksi metrik laporan, filter summary/CSV, CSV aman, UI filter, akses ekspor sesuai peran, pengujian regresi, bukti demo dan sinkronisasi dokumentasi.

Di luar paket dua teman: perubahan topology/checkpoint agent, penggantian model, multi-tenant, WhatsApp, integrasi akuntansi, Google Sheets, dan deployment publik. Pemilik menentukan tindak lanjut bagian ini secara terpisah.

## 3. Deliverables

| ID | Deliverable | Fase | Format |
| --- | --- | --- | --- |
| D1 | Baseline bersama dan kontrak reporting | Persiapan/desain | Commit acuan + catatan kontrak di PR |
| D2 | Backend laporan dengan filter dan agregasi teruji | Implementasi | PR backend + tes |
| D3 | Frontend filter, metrik dan unduhan yang konsisten | Implementasi | PR frontend + screenshot + tes |
| D4 | Matriks QA, hasil smoke test dan panduan demo | Validasi | Markdown + bukti sintetis |
| D5 | README dan spesifikasi sesuai perilaku akhir | Dokumentasi | PR dokumentasi |

## 4. Work Breakdown Structure & Jadwal

Hari dihitung sejak baseline Git siap dan kedua teman dapat menjalankan aplikasi. Estimasi berikut perlu disesuaikan dengan kemampuan/waktu luang anggota.

| WBS | Task | Fase | PIC | Estimasi | Target |
| --- | --- | --- | --- | --- | --- |
| P0 | Bagikan baseline yang memuat perubahan lokal relevan | Persiapan | Pemilik | 0,5 hari | H1 |
| B1 | Inventaris kontrak, fixture dan definisi metrik | Analisis | Sheren + pemilik | 0,5 hari | H1 |
| F1 | Jalankan alur sekarang dan catat QA awal | Analisis | Nisa | 1 hari | H1 |
| B2 | Perbaiki agregasi dan tambah filter bersama | Implementasi | Sheren | 2 hari | H2–H3 |
| F2 | Bangun kontrol filter dan state dengan mock kontrak B1 | Implementasi | Nisa | 2 hari | H2–H3 |
| B3 | Perkuat CSV dan tes akses/failure | Implementasi | Sheren | 1 hari | H4 |
| F3 | Integrasikan metrik, filter dan ekspor; periksa role | Implementasi | Nisa | 1 hari | H4 |
| I1 | Gabungkan PR backend lalu frontend, jalankan tes | Integrasi | Pemilik + keduanya | 1 hari | H5 |
| Q1 | Jalankan matriks QA dan uji PostgreSQL terisolasi | Validasi | Keduanya | 2 hari | H6–H7 |
| D1 | Perbarui dokumentasi dan rekam bukti demo | Dokumentasi | Keduanya + pemilik | 1 hari | H8 |
| R1 | Perbaiki temuan, review akhir, buffer | Validasi | Semua | 2 hari | H9–H10 |

Nisa dapat mengerjakan F1 sambil Sheren menyusun B1. F2 hanya memakai mock dengan bentuk respons yang telah disepakati pada B1. F3 memerlukan B2/B3; Q1 memerlukan integrasi I1.

## 5. Tim & Peran

| Peran | PIC | Tanggung jawab |
| --- | --- | --- |
| Koordinator/reviewer | Pemilik proyek | Baseline, prioritas, kontrak, merge dan keputusan rilis |
| Backend | Sheren | Agregasi, filter, ekspor, fixture dan verifikasi database |
| Frontend/QA | Nisa | UI, transport, akses tampilan dan bukti alur pengguna |

Pemilik tetap menangani konfigurasi Clerk, pemeriksaan akun nyata, evaluasi live model dan pemilihan hosting. Teman tidak perlu menerima secret milik pemilik untuk mengerjakan tugas inti.

## 6. Milestone

| Target | Milestone | Bukti selesai |
| --- | --- | --- |
| H1 | Onboarding dan kontrak selesai | Dua komputer dapat menjalankan demo; filter dan definisi metrik tercatat |
| H4 | Dua paket implementasi siap ditinjau | PR dengan tes dan screenshot |
| H5 | Integrasi selesai | Summary dan CSV menerima filter sama melalui proxy frontend |
| H7 | QA selesai | Setiap kasus memiliki hasil aktual; blocker ditangani |
| H10 | Paket demo diserahkan | Dokumentasi sesuai kode, demo sintetis dan hasil pemeriksaan akhir |

Dokumen BRD internal menyebut tenggat GTNIC 10 November 2026 pukul 23:59 WIB. Itu konteks dari dokumen repository, belum diverifikasi terhadap pengumuman kompetisi. Koordinator perlu memastikan tenggat dan menyesuaikan jadwal sebelum menjadikannya komitmen tim.

## 7. Risiko

| Risiko | Probabilitas | Dampak | Mitigasi |
| --- | --- | --- | --- |
| Fitur lokal belum masuk cabang bersama | Tinggi, terlihat pada working tree | Tinggi | P0 wajib sebelum implementasi |
| README/spec tertinggal dari kode | Tinggi, perbedaan ditemukan | Sedang | Pakai kode/OpenAPI baseline; sinkronkan D5 |
| Definisi otomatis/manual berbeda antar anggota | Sedang | Tinggi | Tulis rumus dan contoh dataset pada B1 |
| Tes database dilewati karena konfigurasi belum ada | Sedang | Tinggi | Siapkan server tes terpisah; laporkan skip secara eksplisit |
| Dua orang mengubah kontrak/file yang sama | Sedang | Sedang | Pembagian file dan kontrak B1; PR kecil |
| Demo memory dianggap persistensi SQL | Sedang | Tinggi | Pisahkan uji demo dan SQL; uji restart pada SQL |
| Alur akun nyata belum terbukti | Sedang | Sedang | Jadwalkan dengan pemilik; tes JWT sintetis tetap berjalan |

## 8. Komunikasi & Pelaporan

Usulan: setiap selesai sesi kerja, kirim status berisi ID tugas, hasil, blocker, langkah berikutnya dan tautan PR. Kanal komunikasi mengikuti pilihan tim yang belum diberikan. Review bersama dilakukan pada H1, H5, dan H8.

Format status: `B2 | filter tanggal selesai | kategori masih menunggu aturan multi-nota | berikutnya tes CSV | PR: ...`.

## 9. Prosedur Perubahan Scope

Catat kebutuhan baru, alasan, dampak ke kontrak/file/jadwal, lalu sepakati dengan koordinator sebelum memasukkannya ke sprint. Perbarui rencana dan kedua README jika pembagian berubah. Fitur tambahan tidak menjadi syarat selesai paket ini tanpa keputusan tim.

## Kriteria selesai bersama

- [ ] Baseline dapat di-clone dan dijalankan teman tanpa menyalin secret.
- [ ] Summary dan CSV menghasilkan himpunan klaim yang sama untuk filter sama.
- [ ] Rumus metrik memiliki fixture dengan hasil yang diketahui.
- [ ] Backend dan frontend lulus pemeriksaan yang relevan; skip dicatat.
- [ ] Matriks QA memuat hasil aktual untuk happy path dan failure path.
- [ ] Dokumentasi sesuai mode demo dan normal.
- [ ] Tidak ada blocker pada pengajuan, klarifikasi, review dan ekspor admin.

