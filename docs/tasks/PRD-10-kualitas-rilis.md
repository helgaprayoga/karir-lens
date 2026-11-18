# PRD-10 — Kualitas dan Rilis

| Field | Keterangan |
|---|---|
| ID task | PRD-10 |
| Nama task | Kualitas dan Rilis |
| Prioritas | P0 |
| Milestone | M8 Rilis (1-2 hari) |
| Dependensi | PRD-01 sampai PRD-09 |
| Task yang bergantung | Tidak ada |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |

---

## 1. Konteks

Setelah seluruh fitur P0 dan P1 selesai, aplikasi perlu diuji menyeluruh, didokumentasikan, diotomatisasi pembaruan datanya, dan di-deploy. Task ini menutup proyek: memastikan GitHub Actions menjalankan pembaruan data terjadwal, aplikasi berjalan di Render, pengujian utama lulus, dan dokumentasi penggunaan tersedia.

## 2. Tujuan

1. Menyediakan workflow GitHub Actions untuk pembaruan data terjadwal (minimal harian).
2. Menyediakan konfigurasi deployment Render yang memakai environment variable.
3. Menjalankan dan melengkapi pengujian utama (parser, logika, endpoint penting).
4. Menyediakan dokumentasi penggunaan, API, dan catatan implementasi.
5. Melakukan pemeriksaan akhir terhadap seluruh constraint produk.

## 3. Scope

### 3.1 Termasuk

- Workflow GitHub Actions: jadwal harian, menjalankan ingestion, clustering, dan statistik; menyimpan hasil ke `scrape_runs`.
- Konfigurasi `Procfile`/`render.yaml` dan variabel environment.
- Pipeline test otomatis (`pytest`, lint/format bila ada).
- Dokumentasi: `README.md`, `docs/API.md`, `docs/IMPLEMENTASI.md`, dan catatan keterbatasan.
- Pemeriksaan akhir: tidak ada tracker lamaran, CV tidak tersimpan, statistik gaji minimal sampel, API konsisten.
- Seed data uji untuk demo bila diperlukan.

### 3.2 Tidak termasuk

- Penambahan fitur baru.
- Perubahan scope produk.
- Tracker lamaran atau status lamaran.
- Layanan berbayar atau langganan.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-10-01 | Workflow GitHub Actions berjalan minimal sekali per hari dan dapat dijalankan manual. | P0 |
| R-10-02 | Workflow menjalankan ingestion untuk ketiga sumber, lalu clustering dan statistik bila data cukup. | P0 |
| R-10-03 | Workflow mencatat status akhir ke `scrape_runs` dan gagal terlihat di riwayat Actions. | P0 |
| R-10-04 | Secret disimpan di GitHub Secrets dan environment Render, bukan repository. | P0 |
| R-10-05 | Aplikasi berhasil di-deploy ke Render dan dapat diakses melalui URL. | P0 |
| R-10-06 | Konfigurasi produksi memakai cookie sesi `Secure`, `HttpOnly`, dan `SameSite`. | P0 |
| R-10-07 | Seluruh test utama lulus di CI: parser, normalisasi, deduplikasi, statistik gaji, bookmark, rekomendasi, API. | P0 |
| R-10-08 | `README.md` menjelaskan setup lokal, environment, migrasi, dan cara menjalankan test. | P0 |
| R-10-09 | `docs/API.md` mendokumentasikan endpoint, parameter, pagination, dan format error. | P0 |
| R-10-10 | `docs/IMPLEMENTASI.md` mencatat keputusan, batasan, dan pertanyaan terbuka yang diselesaikan. | P1 |
| R-10-11 | Pemeriksaan akhir memastikan tidak ada fitur tracker lamaran atau status lamaran. | P0 |
| R-10-12 | Pemeriksaan akhir memastikan file dan teks CV tidak tersimpan dan tidak di-log. | P0 |
| R-10-13 | Statistik gaji tidak tampil saat sampel < 5 di seluruh antarmuka. | P0 |
| R-10-14 | Halaman publik dimuat di bawah 2 detik setelah instance aktif (dengan toleransi cold start terdokumentasi). | P1 |
| R-10-15 | Log produksi tidak memuat data sensitif. | P0 |

### 4.1 Struktur Workflow Acuan

```yaml
name: KarirLens data refresh

on:
  schedule:
    - cron: "0 2 * * *"
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup python
      - install dependencies
      - run scraper --source all
      - run clustering dan statistik bila data cukup
      - laporkan status (gagal jika semua sumber gagal)
```

### 4.2 Checklist Rilis

| Item | Kriteria |
|---|---|
| Database | Migrasi terbaru diterapkan pada Supabase produksi. |
| Environment | Semua variable wajib tersedia di Render dan GitHub Secrets. |
| Test | `pytest` lulus di CI. |
| Data | Minimal satu pembaruan terjadwal berhasil tercatat. |
| Privasi | Tidak ada file/teks CV tersimpan. |
| Scope | Tidak ada tracker lamaran atau status lamaran. |
| Dokumentasi | README, API, dan catatan implementasi tersedia. |

## 5. Acceptance Criteria

- [ ] Workflow terjadwal berjalan dan hasilnya terlihat di `scrape_runs` serta Actions.
- [ ] Workflow dapat dijalankan manual.
- [ ] Aplikasi dapat diakses melalui Render.
- [ ] Cookie sesi produksi aman.
- [ ] Semua test utama lulus di CI.
- [ ] Dokumentasi setup, API, dan implementasi tersedia dan akurat.
- [ ] Tidak ada secret di repository.
- [ ] Tidak ada tracker lamaran atau status lamaran di aplikasi.
- [ ] File dan teks CV tidak tersimpan dan tidak di-log.
- [ ] Statistik gaji konsisten memakai aturan minimal lima sampel.

## 6. Dependensi

- PRD-01 sampai PRD-09 selesai.
- Akses GitHub Actions, akun Render, dan Supabase produksi.
- Kredensial DeepSeek untuk fitur AI.
- Seed data uji untuk demo.

## 7. Test Plan

### 7.1 Pengujian Otomatis (CI)

| Test | Cakupan |
|---|---|
| `test_full_pytest_suite` | Seluruh test lulus di CI. |
| `test_ingestion_smoke` | Ingestion satu sumber berjalan pada environment uji (opsional, dapat di-skip tanpa jaringan). |
| `test_api_contract` | Endpoint utama mengembalikan struktur sesuai dokumentasi. |
| `test_no_application_tracker` | Tidak ada route/tabel/field tracker lamaran. |
| `test_no_cv_persistence` | Tidak ada file/teks CV tersimpan setelah alur CV. |
| `test_salary_threshold_all_surfaces` | Aturan minimal sampel konsisten di web dan API. |
| `test_secure_cookie_production` | Konfigurasi produksi memakai cookie aman. |

### 7.2 Pengujian Manual (Rilis)

1. Jalankan workflow secara manual dan periksa log Actions serta `scrape_runs`.
2. Tunggu jadwal harian dan pastikan workflow berjalan.
3. Buka aplikasi Render dan uji alur publik, akun, bookmark, CV, rekomendasi, AI, admin.
4. Periksa cookie sesi di browser produksi.
5. Ikuti README dari nol pada mesin bersih.
6. Panggil endpoint API sesuai `docs/API.md`.
7. Verifikasi tidak ada data CV di admin atau log.
8. Verifikasi tidak ada tracker lamaran di UI, route, atau database.

## 8. Out of Scope

- Fitur baru dan perubahan produk.
- Optimasi performa lanjutan di luar target.
- Migrasi ke layanan berbayar.
- Pengujian beban berskala besar.

## 9. Catatan Teknis

- Render Free dapat cold start; dokumentasikan toleransi dan pertahankan proses terjadwal di Actions.
- Supabase Free dapat pause; aktifkan data harian dan backup.
- Simpan catatan hasil uji akhir di `docs/IMPLEMENTASI.md`.
- Jangan menambahkan retensi atau pembersihan data berkala kecuali disetujui (pertanyaan terbuka PRD induk).

## 10. Referensi Proyek

**Tidak ada proyek referensi untuk GitHub Actions, Render, atau `render.yaml`.** Kedua folder tidak memiliki workflow CI maupun konfigurasi deployment; bagian itu dikerjakan tanpa acuan.

Yang dirujuk adalah **budaya pengujian dan dokumentasi** dari dua proyek.

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `D:\Semester 5\Praktik Scripting\Pertemuan 8\pytest.ini` | Konfigurasi minimal namun efektif: `[pytest]` dengan `pythonpath = .` dan `testpaths = tests`, sehingga `pytest` dari root langsung menemukan seluruh test tanpa `sys.path` manual. Acuan R-10-07. |
| `D:\Semester 5\Praktik Scripting\Pertemuan 9\tests\test_parser.py`, `tests/fixtures/*.html` | Seluruh uji parser berjalan **tanpa internet** memakai fixture HTML asli. Acuan agar CI tidak bergantung pada situs sumber. |
| `D:\Semester 5\Praktik Scripting\Pertemuan 9\README.md` | Struktur dokumentasi: tabel fitur, struktur proyek, instalasi, tabel variabel environment, cara menjalankan, catatan teknis, batasan, dan tabel pemecahan masalah. Ini menjadi kerangka `README.md` dan `docs/IMPLEMENTASI.md` (R-10-08, R-10-10). |
| `D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot\README.md` | Tabel variabel lingkungan dengan kolom "Bawaan" dan "Fungsi", plus bagian batasan. Acuan agar dokumentasi environment lengkap dan tidak membocorkan secret (R-10-15). |
| `D:\Semester 5\Praktik Scripting\Pertemuan 9\config.py` | Pemisahan seluruh nilai yang dapat berubah ke satu tempat, dengan helper `_env_*` dan default aman. Acuan agar konfigurasi produksi (cookie `Secure`, Render) dapat diubah tanpa mengedit kode. |
| `D:\Semester 5\Praktik Scripting\Pertemuan 9\requirements.txt` | Komentar pada setiap kelompok dependensi yang menjelaskan **mengapa** dibutuhkan (mis. `tzdata` wajib di Windows). Acuan agar `requirements.txt` KarirLens terdokumentasi. |

**Cara mengadaptasi ke KarirLens**

1. Tambahkan `pytest.ini` dengan `pythonpath = .` dan `testpaths = tests` agar perintah `pytest` konsisten di CI dan lokal.
2. Simpan fixture HTML untuk ketiga sumber agar test parser tidak memanggil jaringan di CI.
3. Gunakan struktur README proyek referensi sebagai kerangka, lalu tambahkan bagian khusus deployment Render dan GitHub Actions.
4. Seluruh nilai yang berubah per environment masuk ke `app/config.py`, dibaca lewat helper `_env_*`; CI dan Render cukup mengisi variabel.

**Yang tidak diambil**

- Bot Telegram, `JobQueue`, dan penjadwalan berbasis polling. KarirLens memakai GitHub Actions `schedule`.
- SQLite dan `data.db`. KarirLens memakai Supabase; backup dan retensi mengikuti PRD induk.
- Tidak ada acuan untuk `Procfile`, `render.yaml`, GitHub Secrets, atau toleransi cold start Render; bagian itu dikerjakan tanpa acuan.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Workflow terjadwal berjalan dan tercatat.
- Aplikasi dapat diakses melalui Render.
- Dokumentasi lengkap dan akurat.
- Seluruh constraint produk (tanpa tracker lamaran, tanpa penyimpanan CV, statistik gaji berbasis sampel) terbukti terpenuhi.
