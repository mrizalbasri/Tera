# Dokumentasi Tera

[Ringkasan proyek](../README.md) · [Kontribusi](../CONTRIBUTING.md)

Panduan untuk memahami produk, menjalankan aplikasi, dan menelusuri keputusan
teknis. Tautan di halaman ini dapat dibuka di GitHub maupun Obsidian.

## Mulai sesuai kebutuhan

| Saya ingin… | Mulai di sini |
| --- | --- |
| Memahami produk | [Tentang Tera](../README.md#tentang-tera) · [Business requirements](BRD_Expense_Reimbursement_Agent.md) |
| Menjalankan aplikasi lokal | [Setup, konfigurasi, dan pengujian](development/local-development.md) |
| Mengatur akun dan peran | [Login, akses pengguna, dan demo](admin-login.md) |
| Memahami cara agent bekerja | [Alur agent](architecture/agent-flow.md) |
| Menyiapkan rilis | [Deployment](development/agent-deployment.md) · [Uji penerimaan pengguna](development/agent-uat.md) |
| Mengerjakan frontend | [Panduan tugas frontend](../frontend/README.md) |

## Arsitektur dan keputusan teknis

| Dokumen | Isi |
| --- | --- |
| [Arsitektur sistem](architecture/overview.md) | Komponen utama dan hubungan antarbagian |
| [Alur agent](architecture/agent-flow.md) | Tahapan pemrosesan klaim dan tindak lanjut |
| [Batas modul agent](architecture/agent-modules.md) | Pembagian tanggung jawab dan dependensi |
| [ADR: monorepo](decisions/0001-monorepo.md) | Alasan backend dan frontend berada dalam satu repo |
| [ADR: stack agent](decisions/0002-langchain-langgraph-stack.md) | Keputusan penggunaan LangChain, LangGraph, RAG, dan ML |

### Diagram

| Diagram | Tampilan | Sumber Mermaid |
| --- | --- | --- |
| Arsitektur | [SVG](diagrams/architecture.svg) | [Mermaid](diagrams/architecture.mmd) |
| Pemrosesan klaim | [SVG](diagrams/flow-claim-processing.svg) | [Mermaid](diagrams/flow-claim-processing.mmd) |
| Siklus hidup klaim | [SVG](diagrams/state-claim-lifecycle.svg) | [Mermaid](diagrams/state-claim-lifecycle.mmd) |
| Model data | [SVG](diagrams/erd.svg) | [Mermaid](diagrams/erd.mmd) |

## Pengembangan dan operasional

- [Pengembangan lokal](development/local-development.md) — struktur repo, environment, backend/frontend, dan tes.
- [Login dan akses](admin-login.md) — Sesi JWT, peran, dan mode demo.
- [PostgreSQL dan pgvector](development/pgvector.md) — instalasi lokal, seed kebijakan, dan verifikasi.
- [ML anomaly scoring](development/ml-anomaly.md) — training sintetis, evaluasi, dan aktivasi.
- [Operasional backend](development/backend-operations.md) — migrasi, recovery, batas layanan, dan monitoring.
- [Deployment agent](development/agent-deployment.md) — konfigurasi dan langkah deployment.

## Pengujian dan bukti validasi

Mulai dari rencana pengujian dan UAT untuk pemeriksaan baru. Catatan bertanggal
di bawah menggambarkan hasil saat dijalankan; hasil tersebut bukan status
produksi atau CI terkini.

| Dokumen | Kegunaan |
| --- | --- |
| [Rencana pengujian agent](development/agent-readiness-test-plan.md) | Cakupan dan skenario verifikasi |
| [Panduan UAT](development/agent-uat.md) | Pemeriksaan penerimaan oleh pengguna |
| [Validasi 23 Oktober 2026](development/agent-readiness-validation-2026-10-23.md) | Hasil dan batas pemeriksaan yang dicatat |
| [Verifikasi lanjutan 24 Oktober 2026](development/production-follow-through-2026-10-24.md) | Perbaikan konfigurasi, regresi, dan batas kesiapan rilis |
| [Validasi workspace peran](development/role-workspaces-validation-2026-10-21.md) | Pemeriksaan alur karyawan dan finance |
| [Evaluasi OCR](development/receipt-ocr-evaluation.md) | Metode evaluasi pembacaan nota |

## Requirements dan perancangan

Dokumen SDLC mendukung perencanaan produk dan proposal GTNIC 2026.
Target, asumsi, serta rancangan di dalamnya perlu dibedakan dari kemampuan yang
sudah diimplementasikan dan hasil yang sudah diuji.

| Dokumen | Fokus |
| --- | --- |
| [Business requirements awal](BRD_Expense_Reimbursement_Agent.md) | Masalah, pengguna, dan kebutuhan bisnis |
| [BRD](sdlc/05-brd.md) | Kebutuhan bisnis terstruktur |
| [PRD](sdlc/06-prd.md) | Kebutuhan produk |
| [SRS](sdlc/07-srs.md) | Spesifikasi perangkat lunak |
| [System design](sdlc/08-system-design-sdd.md) | Perancangan sistem |
| [Database design](sdlc/10-database-design.md) | Struktur data dan penyimpanan |

Rancangan per fitur dan riwayat spesifikasi tersedia di
[folder spesifikasi](superpowers/specs/). Gunakan sebagai konteks keputusan;
cocokkan dengan kode dan panduan operasional sebelum menerapkannya.

## Membaca di Obsidian

Buka folder `docs/` sebagai vault, lalu buka halaman ini.
Dokumen internal lainnya tetap memiliki wikilink untuk Graph View.
Diagram tersedia sebagai SVG untuk dibaca langsung dan `.mmd` untuk diedit.
