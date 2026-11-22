# PRD per Task — KarirLens

Dokumen ini memecah [PRD KarirLens](../PRD.md) menjadi PRD per task yang lebih kecil. Setiap PRD memuat konteks, tujuan, scope, requirement, acceptance criteria, dependensi, test plan, dan out of scope.

## Dua Track

Pengerjaan dibagi menjadi **dua track berurutan**: seluruh antarmuka diselesaikan lebih dulu, baru logika backend diisi.

```text
TRACK A — Frontend (duluan)
  PRD-F01 Design system & kerangka UI
      |
      v
  PRD-F02 Katalog publik
      |
      +--> PRD-F03 Auth, profil, tersimpan
      |
      +--> PRD-F04 CV & asisten AI
      |
      +--> PRD-F05 Insight & admin
      |
      v
  PRD-F06 State, responsif, aksesibilitas
      |
      v
TRACK B — Backend (menyusul)
  PRD-01 Fondasi  (selesai)
      |
      v
  PRD-02 Ingestion --> PRD-03 Normalisasi & dedup
      |                    |
      v                    v
  PRD-04 Katalog    --> PRD-05 Insight
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

**Aturan pembagian yang mengikat:**

| Track | Memiliki | Tidak memiliki |
|---|---|---|
| A — Frontend | Template Jinja, CSS, JavaScript, komponen, state tampilan, aksesibilitas | Query database, aturan bisnis, panggilan AI, akses Supabase |
| B — Backend | Repository, service, aturan bisnis, pipeline data, API, skema | Markup, warna, layout, animasi |

Satu-satunya titik temu keduanya adalah **kontrak template**: nama variabel konteks yang diharapkan sebuah template. Track A menetapkannya, Track B memenuhinya. Kontrak itu ditulis pada masing-masing PRD-F (bagian "Kontrak Template") dan dirujuk oleh PRD backend yang bersangkutan.

## Daftar Task Frontend (Track A)

| ID | Task | Prioritas | Dependensi | Halaman |
|---|---|---|---|---|
| [PRD-F01](./PRD-F01-design-system.md) | Design System & Kerangka UI | P0 | — | `base.html`, `/styleguide` |
| [PRD-F02](./PRD-F02-katalog-publik.md) | Katalog Publik | P0 | F01 | `/`, `/jobs`, `/jobs/<id>`, `/companies/<slug>` |
| [PRD-F03](./PRD-F03-auth-profil.md) | Auth, Profil, Tersimpan | P0 | F01 | `/preview/profile`, `/preview/saved`, `/auth/*` |
| [PRD-F04](./PRD-F04-cv-asisten.md) | CV & Asisten AI | P0 | F01, F02 | `/preview/cv`, `/preview/assistant` |
| [PRD-F05](./PRD-F05-insight-admin.md) | Insight & Admin | P0 | F01, F02 | `/preview/insights`, `/preview/admin/*` |
| [PRD-F06](./PRD-F06-state-aksesibilitas.md) | State, Responsif, Aksesibilitas | P0 | F01 s.d. F05 | audit seluruh halaman |

## Daftar Task Backend (Track B)

| ID | Task | Prioritas | Milestone | Dependensi | Status |
|---|---|---|---|---|---|
| [PRD-01](./PRD-01-fondasi-proyek.md) | Fondasi Proyek | P0 | M1 | — | Selesai |
| [PRD-02](./PRD-02-data-ingestion.md) | Data Ingestion | P0 | M2 | PRD-01 | Selesai |
| [PRD-03](./PRD-03-normalisasi-deduplikasi.md) | Normalisasi dan Deduplikasi | P0 | M2 | PRD-01, PRD-02 | Selesai |
| [PRD-04](./PRD-04-katalog-publik.md) | Katalog Publik (backend) | P0 | M3 | PRD-01, PRD-03, F02 | Selesai |
| [PRD-05](./PRD-05-perusahaan-insight.md) | Perusahaan dan Insight (backend) | P0 | M4 | PRD-03, PRD-04, F05 | Selesai |
| [PRD-06](./PRD-06-akun-bookmark.md) | Akun dan Bookmark (backend) | P0 | M5 | PRD-01, PRD-04, F03 | Selesai |
| [PRD-07](./PRD-07-cv-rekomendasi.md) | CV dan Rekomendasi (backend) | P0 | M6 | PRD-03, PRD-04, PRD-06, F04 | Selesai |
| [PRD-08](./PRD-08-asisten-ai.md) | Asisten AI (backend) | P1 | M7 | PRD-03, PRD-05, PRD-06, F04 | Belum dimulai |
| [PRD-09](./PRD-09-admin-api.md) | Admin dan API (backend) | P0 | M7 | PRD-04 s.d. PRD-08, F05 | Belum dimulai |
| [PRD-10](./PRD-10-kualitas-rilis.md) | Kualitas dan Rilis | P0 | M8 | PRD-01 s.d. PRD-09 | Belum dimulai |

## Cara Frontend Dikerjakan Tanpa Backend

Track A tidak menunggu Track B. Tiga mekanisme membuatnya mungkin:

1. **Preview blueprint.** `app/preview/` hanya diregistrasi ketika `PREVIEW_UI=true`. Blueprint ini merender setiap template dengan data contoh dari `tests/fixtures/ui/*.json`, sehingga semua halaman dapat dibuka di browser dan ditinjau pada 360/768/1024/1280 px sebelum satu query pun ditulis.
2. **Fixture sebagai kontrak.** Berkas JSON di `tests/fixtures/ui/` adalah bentuk data yang disepakati. Track A memakai JSON itu untuk merender; Track B wajib menghasilkan `dict` dengan bentuk yang sama dari `service`.
3. **Test render.** Setiap halaman diuji `200 OK` + memuat komponen wajibnya, memakai fixture yang sama. Test ini tetap berlaku setelah backend terpasang, sebagai jaring pengaman bahwa perubahan service tidak merusak tampilan.

Ketika Track B selesai untuk sebuah modul, route produksi mengambil alih dan preview untuk halaman itu dipertahankan sebagai alat audit visual.

## Konvensi

- Setiap PRD memakai pola nama `PRD-XX-nama-task.md` (backend) atau `PRD-FXX-nama-task.md` (frontend).
- Requirement diberi ID `R-XX-NN` (backend) atau `R-FXX-NN` (frontend) agar dapat ditelusuri pada implementasi dan pengujian.
- Acceptance criteria ditulis sebagai checklist yang harus terbukti terpenuhi.
- Test plan membedakan pengujian otomatis (`pytest`) dan pengujian manual.
- Out of scope merujuk batasan pada PRD induk, terutama tracker lamaran, prediksi gaji, dan penyimpanan CV.
- Setiap PRD punya bagian **Referensi Proyek** yang menyebut berkas konkret dari proyek sebelumnya.
- Spesifikasi visual (token, anatomi komponen, state, aksesibilitas) berada di [Design System KarirLens](../design-system.md). Track A wajib mengikutinya; Track B tidak menyentuh tampilan.
- Penempatan kode, arah dependensi antar lapisan, dan struktur direktori mengikuti [Arsitektur Kode KarirLens](../ARCHITECTURE.md).
- Pratinjau visual acuan ada di [design-preview.html](../design-preview.html). Setiap halaman baru harus memakai bahasa visual yang sama.

## Status

- **Track A**: PRD-F01 s.d. PRD-F06 **selesai**. Track A siap menerima Track B.
- **Track B**: PRD-01 s.d. PRD-07 **selesai**. PRD-08 s.d. PRD-10 **Belum dimulai**.

`/insights` sudah hidup: 363 lowongan dalam 6 cluster, skill populer, dan
statistik gaji per mata uang dan periode. Clustering dijalankan lewat
`python -m scraper cluster`, tidak pernah dari request web.

Bookmark juga sudah persisten: `/profile` dan `/saved` memakai data pengguna
sungguhan, tombol simpan mengirim POST, dan menyimpan dua kali tidak membuat
duplikat.

`/cv` menerima PDF dan DOCX, mengekstrak teks secara lokal, mencocokkan skill
dengan kamus, dan menghitung rekomendasi deterministik tanpa AI. Berkas dan teks
CV dihapus di blok `finally` — pada jalur sukses maupun gagal.

### Pemfokusan produk: hanya lowongan IT

Sejak PRD-04, KarirLens **hanya menyimpan lowongan IT**. Alasannya bukan
preferensi: tiga sumber ini memuat semua jenis pekerjaan, dan 96% hasil
scraping Dealls adalah non-IT (860 dari 900). Katalog yang 96% berisi "Head
Chef" dan "Host Live" bukan katalog karir teknologi.

Aturannya ada di `core/tech.py`, diuji terhadap 30 judul nyata di
`tests/unit/test_tech_filter.py`. Bukti yang dipakai, dari terkuat:

| Sumber | Sinyal | Contoh |
|---|---|---|
| Kalibrr | field `function` | "IT and Software" |
| Remotive | kategori di URL | `/remote-jobs/software-development` |
| Dealls | judul dan skill | "Data Engineer", "Cyber Security Engineer" |

Dealls tidak punya kategori yang dapat dipercaya (`categoryId` kosong pada 17
dari 18 lowongan yang diperiksa), sehingga judul menjadi satu-satunya sinyal.
Pencocokan memakai batas kata — tanpa itu `"it staff"` cocok di dalam
**"audit staff"**, dan "Tax & Audit Staff" masuk sebagai lowongan IT.

Hasil pengambilan penuh (`python -m scraper run --source all --pages 0 --replace`):

| Sumber | Diambil | IT | Disaring |
|---|---|---|---|
| dealls | 900 | 40 | 860 |
| kalibrr | 2290 | 253 | 0 (disaring server) |
| remotive | 171 | 65 | 105 |
| **total** | **3361** | **358** | **965** |

Kalibrr memakai tombol "Load more" yang memanggil endpoint `/kjs/job_board/search`
dengan filter `function=IT+and+Software` — ditemukan dengan merekam panggilan
jaringan saat tombolnya diklik, bukan dengan menebak parameter URL. Playwright
tidak diperlukan: yang dijalankan tombol itu hanyalah satu permintaan HTTP.
Rincian di [PRD-04 §14](./PRD-04-katalog-publik.md).

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
| [PRD-F01](./PRD-F01-design-system.md) | design-preview.html | Struktur shell, header, navpill, anatomi kartu, token |
| [PRD-F02](./PRD-F02-katalog-publik.md) | design-preview.html, Bot Rekap Lowongan Dealls | Kartu lowongan, bar filter, pagination, filter Jinja `tanggal`/`angka` |
| [PRD-F03](./PRD-F03-auth-profil.md) | Bot Utang-Piutang | Form, pesan validasi, dashboard per pengguna |
| [PRD-F04](./PRD-F04-cv-asisten.md) | BengkelBot | UI chat, pasangan pesan, penanganan galat jaringan |
| [PRD-F05](./PRD-F05-insight-admin.md) | Dashboard Analisis PLN, BengkelBot | Dashboard admin, kartu statistik, Chart.js `state.charts` |
| [PRD-F06](./PRD-F06-state-aksesibilitas.md) | design-system.md §5, §7 | Checklist aksesibilitas dan review UI |
| [PRD-01](./PRD-01-fondasi-proyek.md) | Bot Utang-Piutang, BengkelBot, Bot Rekap Lowongan Dealls | Application factory, konfigurasi environment, header keamanan, error handler, migrasi bertahap |
| [PRD-02](./PRD-02-data-ingestion.md) | Bot Rekap Lowongan Dealls | Adapter scraper, `robots.txt`, retry/backoff, isolasi kegagalan sumber, `scrape_runs`, CLI, fixture parser |
| [PRD-03](./PRD-03-normalisasi-deduplikasi.md) | Bot Rekap Lowongan Dealls | Insert-or-update idempoten, penyimpanan skill sebagai JSON, utilitas pembersihan teks, klasifikasi baris meta |
| [PRD-04](./PRD-04-katalog-publik.md) | Bot Rekap Lowongan Dealls | Query dinamis + filter, pagination, endpoint JSON, fixture test web |
| [PRD-05](./PRD-05-perusahaan-insight.md) | Dashboard Analisis PLN, Bot Utang-Piutang | TF-IDF/PCA/KMeans, kata kunci cluster, pesan data terbatas, agregasi grafik |
| [PRD-06](./PRD-06-akun-bookmark.md) | Bot Utang-Piutang, Bot Rekap Lowongan Dealls | Decorator pembatas akses, sesi dari server, upsert idempoten, data per pengguna |
| [PRD-07](./PRD-07-cv-rekomendasi.md) | BengkelBot | Kamus normalisasi skill, pemisahan praproses, pengukuran akurasi kamus, penanda ambigu |
| [PRD-08](./PRD-08-asisten-ai.md) | BengkelBot | Kontrak `POST /api/chat`, helper error JSON, bentuk respons, pola ambang, pengujian dengan mock |
| [PRD-09](./PRD-09-admin-api.md) | BengkelBot, Bot Rekap Lowongan Dealls | Dashboard admin, pengecekan akses admin, agregasi statistik, pemisahan JSON vs HTML, pagination API |
| [PRD-10](./PRD-10-kualitas-rilis.md) | Bot Utang-Piutang, Bot Rekap Lowongan Dealls | `pytest.ini`, test tanpa jaringan, struktur README, konfigurasi terpusat |

### Fitur KarirLens yang tidak punya acuan

| Fitur | Task | Alasan |
|---|---|---|
| Registrasi/login email-password, hash password, CSRF | PRD-01, PRD-06 | Kedua proyek memakai identitas bot Telegram, bukan akun web |
| Ekstraksi teks CV PDF/DOCX dan penghapusan berkas sementara | PRD-07 | Tidak ada proyek yang memakai `pypdf`/`pdfplumber` |
| Rekomendasi berbasis skill terkonfirmasi | PRD-07 | Tidak ada sistem rekomendasi di proyek sebelumnya |
| Panggilan DeepSeek API dan grounding konteks | PRD-08 | BengkelBot berbasis aturan tanpa LLM |
| GitHub Actions terjadwal, Render, `render.yaml` | PRD-10 | Tidak ada konfigurasi CI/deployment di proyek sebelumnya |
| Statistik gaji (median/P25/P75) | PRD-05 | Proyek referensi tidak mengolah data gaji |
| Deduplikasi lintas sumber (`dedup_hash`) | PRD-03 | Semua proyek referensi hanya memakai satu sumber |
| Seluruh Track A (design system, komponen, halaman) | PRD-F01..F06 | Proyek referensi memakai CSS sederhana, bukan design system bertoken |
