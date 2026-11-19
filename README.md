# KarirLens

Platform agregasi lowongan kerja dengan kategorisasi otomatis, insight gaji, dan rekomendasi berbasis CV. Data diambil dari Dealls, Kalibrr, dan Remotive, lalu disajikan dalam satu antarmuka pencarian.

Mata kuliah Praktik Aplikasi Web — Helga Arya Prayoga.

## Status

Pengerjaan dibagi dua track: **seluruh antarmuka lebih dulu** (Track A), baru logika backend (Track B).

| Track | Keadaan |
|---|---|
| A — Frontend (PRD-F01..F06) | PRD-F01, F02 selesai; PRD-F03 s.d. F06 belum dimulai |
| B — Backend (PRD-01..PRD-10) | PRD-01 selesai; PRD-02 s.d. PRD-10 belum dimulai |

| Lapisan | Keadaan |
|---|---|
| Struktur direktori, application factory, blueprint | Selesai |
| Konfigurasi environment, error handler, security header | Selesai |
| Koneksi Supabase, helper pagination, hierarki error | Selesai |
| Layout dasar, navigasi, halaman error | Selesai |
| Registrasi, login, logout, CSRF, cookie aman | Selesai |
| Logging tanpa data sensitif | Selesai |
| Design system lengkap, `/styleguide`, preview blueprint | Selesai (PRD-F01) |
| Halaman katalog, profil, CV, asisten, insight, admin | Katalog selesai (PRD-F02); sisanya PRD-F03..F05 |
| Modul `jobs`, `insights`, `profile`, `cv`, `assistant`, `admin`, `api` | Kerangka, diisi per PRD |
| Pipeline `scraper` (adapter, normalisasi, dedup, clustering) | Kerangka, diisi per PRD |

## Dokumentasi

| Dokumen | Isi |
|---|---|
| [PRD KarirLens](docs/PRD.md) | Acuan produk dan teknis tingkat tinggi |
| [PRD per Task](docs/tasks/README.md) | Pemecahan pekerjaan menjadi dua track: frontend lalu backend |
| [Arsitektur Kode](docs/ARCHITECTURE.md) | Struktur, lapisan, arah dependensi, penempatan kode |
| [Design System](docs/design-system.md) | Token visual, komponen, state, aksesibilitas |
| [Panduan Setup Supabase](docs/SUPABASE-SETUP.md) | Membuat project, menjalankan migrasi, memverifikasi skema |

## Arsitektur Singkat

Modular monolith dengan tiga lapisan per modul:

```text
routes.py  ->  service.py  ->  repository.py  ->  core/db.py  ->  Supabase
   HTTP         aturan bisnis      query
```

- `app/<modul>/` — satu folder per fitur, berisi tiga lapisan di atas.
- `core/` — shared kernel: konfigurasi, koneksi database, error, pagination, normalisasi teks, kamus skill, klien DeepSeek. Bebas Flask.
- `scraper/` — entrypoint batch (adapter sumber, pipeline data, clustering). Bebas Flask.

Aturan dependensi dijaga otomatis oleh `tests/unit/test_architecture.py`. Rincian dan alasannya ada di [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Kebutuhan

- Python 3.11 atau lebih baru
- Proyek Supabase beserta `SUPABASE_URL` dan `SUPABASE_KEY`
- Kunci DeepSeek (hanya untuk fitur asisten AI)

## Setup Lokal

```powershell
# 1. Virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dependensi
pip install -r requirements.txt

# 3. Konfigurasi
Copy-Item .env.example .env
# lalu isi SECRET_KEY, SUPABASE_URL, SUPABASE_KEY,
# serta SUPABASE_DB_HOST / USER / PASSWORD untuk migrasi

# 4. Skema database — dijalankan dari program
python -m db status       # lihat status migrasi
python -m db migrate      # terapkan migrasi

# 5. Verifikasi skema
python scripts\verify_supabase.py

# 6. Jalankan aplikasi
flask --app wsgi run --debug
```

Panduan lengkap termasuk cara membuat project Supabase: [docs/SUPABASE-SETUP.md](docs/SUPABASE-SETUP.md).

Aplikasi tersedia di `http://127.0.0.1:5000`.

## Variabel Environment

| Variabel | Wajib | Bawaan | Fungsi |
|---|---|---|---|
| `SECRET_KEY` | Ya | — | Kunci sesi dan CSRF. Aplikasi menolak start bila kosong. |
| `SUPABASE_URL` | Ya | — | URL proyek Supabase. |
| `SUPABASE_KEY` | Ya | — | Kunci API (`publishable`). Dipakai aplikasi web lewat PostgREST. |
| `SUPABASE_DB_HOST` | Untuk migrasi | — | Host pooler dari **Settings → Database**. |
| `SUPABASE_DB_PORT` | Untuk migrasi | `5432` | Port Session pooler. |
| `SUPABASE_DB_NAME` | Tidak | `postgres` | Nama database. |
| `SUPABASE_DB_USER` | Untuk migrasi | — | `postgres.<project-ref>`. |
| `SUPABASE_DB_PASSWORD` | Untuk migrasi | — | Password database (bukan kunci API). |
| `SUPABASE_DB_SSLMODE` | Tidak | `require` | Mode SSL koneksi langsung. |
| `DEEPSEEK_API_KEY` | Untuk AI | — | Kunci DeepSeek. |
| `DEEPSEEK_MODEL` | Tidak | `deepseek-chat` | Model DeepSeek. |
| `AI_DAILY_LIMIT` | Tidak | `20` | Batas pertanyaan asisten per pengguna per hari. |
| `SCRAPER_USER_AGENT` | Tidak | `KarirLensBot/1.0` | User agent pipeline data. |
| `SCRAPER_MAX_RETRY` | Tidak | `3` | Maksimum retry pengambilan data. |
| `CLUSTER_N_CLUSTERS` | Tidak | `6` | Jumlah cluster KMeans. |
| `CLUSTER_PCA_COMPONENTS` | Tidak | `2` | Komponen PCA sebelum KMeans. |
| `MAX_UPLOAD_BYTES` | Tidak | `5242880` | Batas ukuran berkas CV (5 MB). |
| `SESSION_COOKIE_SECURE` | Tidak | `false` | Set `true` pada produksi. |
| `PREVIEW_UI` | Tidak | `false` | Aktifkan blueprint preview untuk meninjau UI dengan data contoh. |

**`SUPABASE_KEY` dan `SUPABASE_DB_PASSWORD` berbeda.** Yang pertama adalah kunci API untuk membaca/menulis baris; yang kedua adalah password database untuk menjalankan migrasi. Keduanya tidak bisa saling menggantikan.

Secret tidak boleh masuk repository. `.env` sudah di-ignore.

## Migrasi Database

Aplikasi mengakses Supabase lewat dua jalur berbeda:

| Jalur | Dipakai untuk | Perintah |
|---|---|---|
| PostgREST (kunci API) | CRUD baris | otomatis, lewat aplikasi |
| Postgres langsung (password DB) | DDL: `CREATE TABLE`, `CREATE INDEX` | `python -m db migrate` |

```powershell
python -m db status                 # status setiap migrasi
python -m db migrate                # terapkan yang belum dijalankan
python -m db migrate --dry-run      # tampilkan tanpa menulis
```

Runner bersifat idempoten (tabel pelacak `schema_migrations`), atomik per berkas (satu transaksi), dan mendeteksi perubahan berkas yang sudah diterapkan. Detail: [docs/SUPABASE-SETUP.md §4](docs/SUPABASE-SETUP.md).

## Pipeline Data

```powershell
python -m scraper run --source all      # ambil lowongan dari tiga sumber
python -m scraper run --source dealls   # satu sumber saja
python -m scraper cluster               # hitung ulang clustering dan insight
```

Keduanya belum berisi implementasi; masing-masing mengisi `NotImplementedError` sampai PRD-02 dan PRD-05 dikerjakan.

## Pengujian

```powershell
python -m pytest                # seluruh test
python -m pytest tests/unit     # test cepat, tanpa jaringan
```

Test berjalan tanpa Supabase dan tanpa jaringan: client database dan DeepSeek diganti stub pada `tests/conftest.py`.

## Struktur Proyek

```text
app/          aplikasi web (Flask), satu folder per fitur
core/         shared kernel: config, db, errors, pagination, text, skills, external
scraper/      pipeline data: adapters, pipeline, cluster
templates/    Jinja, mengikuti nama modul
static/       css (tokens, components), js, vendor (Bootstrap lokal)
migrations/   skema SQL
tests/        unit dan integration
docs/         PRD, arsitektur, design system, PRD per task
```

## Halaman yang Sudah Ada

| Route | Keterangan |
|---|---|
| `/` | Beranda |
| `/auth/register` | Registrasi |
| `/auth/login` | Login |
| `/auth/logout` | Logout (POST) |
| `/preview/` | Daftar halaman preview (hanya `PREVIEW_UI=true`) |
| `/preview/styleguide` | Audit seluruh komponen design system (hanya `PREVIEW_UI=true`) |
| `/preview/home` | Beranda katalog dengan data contoh |
| `/preview/jobs` | Katalog: pencarian, filter, urutan, pagination |
| `/preview/jobs/<id>` | Detail lowongan dan lowongan serupa |
| `/preview/companies/<slug>` | Halaman perusahaan dari data lowongan |

Halaman `/preview/*` hanya terdaftar bila `PREVIEW_UI=true`. Ketika flag itu mati, route-nya tidak ada sama sekali sehingga mengembalikan 404, bukan 403.

Route katalog, insight, profil, CV, asisten, dan admin ditambahkan pada PRD berikutnya. Navigasi otomatis hanya menampilkan tautan yang endpoint-nya sudah terdaftar.

## Batasan

- Tidak ada tracker lamaran atau status lamaran.
- Tidak ada prediksi gaji; statistik hanya dari data faktual.
- Berkas dan teks CV tidak disimpan.
- Statistik gaji tidak tampil bila sampel kurang dari lima.
- Halaman perusahaan hanya memakai data yang diturunkan dari lowongan.
