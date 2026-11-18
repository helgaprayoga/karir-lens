# PRD per Task — KarirLens

Dokumen ini memecah [PRD KarirLens](../PRD.md) menjadi PRD per task yang lebih kecil. Setiap task PRD memuat konteks, tujuan, scope, requirement, acceptance criteria, dependensi, test plan, dan out of scope.

## Daftar Task

| ID | Task | Prioritas | Milestone | Dependensi |
|---|---|---|---|---|
| [PRD-01](./PRD-01-fondasi-proyek.md) | Fondasi Proyek | P0 | M1 | — |
| [PRD-02](./PRD-02-data-ingestion.md) | Data Ingestion | P0 | M2 | PRD-01 |
| [PRD-03](./PRD-03-normalisasi-deduplikasi.md) | Normalisasi dan Deduplikasi | P0 | M2 | PRD-01, PRD-02 |
| [PRD-04](./PRD-04-katalog-publik.md) | Katalog Publik | P0 | M3 | PRD-01, PRD-03 |
| [PRD-05](./PRD-05-perusahaan-insight.md) | Perusahaan dan Insight | P0 | M4 | PRD-03, PRD-04 |
| [PRD-06](./PRD-06-akun-bookmark.md) | Akun dan Bookmark | P0 | M5 | PRD-01, PRD-04 |
| [PRD-07](./PRD-07-cv-rekomendasi.md) | CV dan Rekomendasi | P0 | M6 | PRD-03, PRD-04, PRD-06 |
| [PRD-08](./PRD-08-asisten-ai.md) | Asisten AI | P1 | M7 | PRD-03, PRD-05, PRD-06 |
| [PRD-09](./PRD-09-admin-api.md) | Admin dan API | P0 | M7 | PRD-04 s.d. PRD-08 |
| [PRD-10](./PRD-10-kualitas-rilis.md) | Kualitas dan Rilis | P0 | M8 | PRD-01 s.d. PRD-09 |

## Urutan Pengerjaan

```text
PRD-01 Fondasi
   |
   v
PRD-02 Data ingestion --> PRD-03 Normalisasi & deduplikasi
   |                          |
   v                          v
PRD-04 Katalog publik --> PRD-05 Perusahaan & insight
   |
   v
PRD-06 Akun & bookmark
   |
   v
PRD-07 CV & rekomendasi --> PRD-08 Asisten AI
                              |
                              v
                        PRD-09 Admin & API
                              |
                              v
                        PRD-10 Kualitas & rilis
```

Urutan mengikuti dependensi: fondasi, data pipeline, katalog publik, insight, fitur pengguna, AI, admin/API, lalu rilis.

## Konvensi

- Setiap PRD memakai pola nama `PRD-XX-nama-task.md`.
- Requirement diberi ID `R-XX-NN` agar dapat ditelusuri pada implementasi dan pengujian.
- Acceptance criteria ditulis sebagai checklist yang harus terbukti terpenuhi.
- Test plan membedakan pengujian otomatis (`pytest`) dan pengujian manual.
- Out of scope merujuk batasan pada PRD induk, terutama tracker lamaran, prediksi gaji, dan penyimpanan CV.
- Setiap PRD punya bagian **Referensi Proyek** yang menyebut berkas konkret dari proyek sebelumnya.
- Spesifikasi visual (token, anatomi komponen, state, aksesibilitas) berada di [Design System KarirLens](../design-system.md), bukan di PRD task. PRD menyebut requirement; design system menyebut cara membangun komponennya.
- Penempatan kode, arah dependensi antar lapisan, dan struktur direktori mengikuti [Arsitektur Kode KarirLens](../ARCHITECTURE.md). Sebelum menambah berkas pada task mana pun, periksa §9 dokumen itu untuk menentukan lokasinya.

## Referensi Proyek Sebelumnya

Fitur KarirLens mengacu pada proyek yang sudah dikerjakan di `D:\Semester 5\Praktik Aplikasi Web` dan `D:\Semester 5\Praktik Scripting`. Hanya proyek yang konsepnya benar-benar sama yang direferensikan.

| Proyek | Lokasi | Konsep yang sama |
|---|---|---|
| Bot Rekap Lowongan Dealls | `Praktik Scripting\Pertemuan 9` | Scraping Dealls, `robots.txt`, retry/backoff, `scrape_runs`, normalisasi skill, dashboard Flask dengan pencarian/filter/pagination, JSON API, pytest + fixture HTML |
| Bot Utang-Piutang | `Praktik Scripting\Pertemuan 8` | Application factory Flask, sesi dan cookie aman, decorator pembatas akses, data per pengguna, dashboard Chart.js, `pytest.ini` |
| BengkelBot | `Praktik Aplikasi Web\Pertemuan 8\bengkelbot` | Admin dashboard berbasis statistik, REST API JSON + format error, UI chat, kamus berbasis aturan dan evaluasi akurasi |
| Dashboard Analisis PLN | `Praktik Aplikasi Web\pln_analysis` | TF-IDF, PCA, KMeans, kata kunci per cluster, pesan data terbatas |

### Pemetaan per task

| Task | Proyek referensi utama | Bagian yang diambil |
|---|---|---|
| [PRD-01](./PRD-01-fondasi-proyek.md) | Bot Utang-Piutang, BengkelBot, Bot Rekap Lowongan Dealls | Application factory, konfigurasi environment, header keamanan, error handler, migrasi bertahap |
| [PRD-02](./PRD-02-data-ingestion.md) | Bot Rekap Lowongan Dealls | Adapter scraper, `robots.txt`, retry/backoff, isolasi kegagalan sumber, `scrape_runs`, CLI, fixture parser |
| [PRD-03](./PRD-03-normalisasi-deduplikasi.md) | Bot Rekap Lowongan Dealls | Insert-or-update idempoten, penyimpanan skill sebagai JSON, utilitas pembersihan teks, klasifikasi baris meta |
| [PRD-04](./PRD-04-katalog-publik.md) | Bot Rekap Lowongan Dealls | Query dinamis + filter, pagination, halaman detail, filter Jinja, endpoint JSON, fixture test web |
| [PRD-05](./PRD-05-perusahaan-insight.md) | Dashboard Analisis PLN, Bot Utang-Piutang | TF-IDF/PCA/KMeans, kata kunci cluster, pesan data terbatas, Chart.js, agregasi grafik |
| [PRD-06](./PRD-06-akun-bookmark.md) | Bot Utang-Piutang, Bot Rekap Lowongan Dealls | Decorator pembatas akses, sesi dari server, upsert idempoten, data per pengguna |
| [PRD-07](./PRD-07-cv-rekomendasi.md) | BengkelBot | Kamus normalisasi skill, pemisahan praproses, pengukuran akurasi kamus, penanda ambigu |
| [PRD-08](./PRD-08-asisten-ai.md) | BengkelBot | Kontrak `POST /api/chat`, helper error JSON, bentuk respons, pola ambang, UI chat, pengujian dengan mock |
| [PRD-09](./PRD-09-admin-api.md) | BengkelBot, Bot Rekap Lowongan Dealls | Dashboard admin, pengecekan akses admin, agregasi statistik, pemisahan JSON vs HTML, pagination API |
| [PRD-10](./PRD-10-kualitas-rilis.md) | Bot Utang-Piutang, Bot Rekap Lowongan Dealls | `pytest.ini`, test tanpa jaringan, struktur README, konfigurasi terpusat |

### Fitur KarirLens yang tidak punya acuan

Fitur berikut tidak ada padanannya di kedua folder, sehingga PRD-nya tetap seperti semula tanpa referensi:

| Fitur | Task | Alasan |
|---|---|---|
| Registrasi/login email-password, hash password, CSRF | PRD-01, PRD-06 | Kedua proyek memakai identitas bot Telegram, bukan akun web |
| Ekstraksi teks CV PDF/DOCX dan penghapusan berkas sementara | PRD-07 | Tidak ada proyek yang memakai `pypdf`/`pdfplumber` |
| Rekomendasi berbasis skill terkonfirmasi | PRD-07 | Tidak ada sistem rekomendasi di proyek sebelumnya |
| Panggilan DeepSeek API dan grounding konteks | PRD-08 | BengkelBot berbasis aturan tanpa LLM |
| GitHub Actions terjadwal, Render, `render.yaml` | PRD-10 | Tidak ada konfigurasi CI/deployment di proyek sebelumnya |
| Statistik gaji (median/P25/P75) | PRD-05 | Proyek referensi tidak mengolah data gaji |
| Deduplikasi lintas sumber (`dedup_hash`) | PRD-03 | Semua proyek referensi hanya memakai satu sumber |

## Status

Semua task masih **Belum dimulai**. Status pada masing-masing dokumen diperbarui saat implementasi berjalan.
