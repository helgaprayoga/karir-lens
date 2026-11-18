# KarirLens

Platform agregasi lowongan kerja dengan kategorisasi otomatis, insight gaji, dan rekomendasi berbasis CV. Data diambil dari Dealls, Kalibrr, dan Remotive, lalu disajikan dalam satu antarmuka pencarian.

Mata kuliah Praktik Aplikasi Web — Helga Arya Prayoga.

## Status

Kerangka proyek (skeleton) sudah berdiri dan lulus pengujian. Fitur belum diisi; pengerjaan mengikuti urutan task pada [docs/tasks/README.md](docs/tasks/README.md).

| Lapisan | Keadaan |
|---|---|
| Struktur direktori, application factory, blueprint | Siap |
| Konfigurasi environment, error handler, security header | Siap |
| Koneksi Supabase, helper pagination, hierarki error | Siap |
| Modul `auth`, `jobs`, `insights`, `profile`, `cv`, `assistant`, `admin`, `api` | Kerangka, diisi per PRD |
| Pipeline `scraper` (adapter, normalisasi, dedup, clustering) | Kerangka, diisi per PRD |

## Dokumentasi

| Dokumen | Isi |
|---|---|
| [PRD KarirLens](docs/PRD.md) | Acuan produk dan teknis tingkat tinggi |
| [PRD per Task](docs/tasks/README.md) | Pemecahan pekerjaan menjadi 10 task |
| [Arsitektur Kode](docs/ARCHITECTURE.md) | Struktur, lapisan, arah dependensi, penempatan kode |
| [Design System](docs/design-system.md) | Token visual, komponen, state, aksesibilitas |

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
# lalu isi SECRET_KEY, SUPABASE_URL, dan SUPABASE_KEY di .env

# 4. Skema database
# Jalankan migrations/001_initial_schema.sql pada SQL Editor Supabase

# 5. Jalankan aplikasi
flask --app wsgi run --debug
```

Aplikasi tersedia di `http://127.0.0.1:5000`.

## Variabel Environment

| Variabel | Wajib | Bawaan | Fungsi |
|---|---|---|---|
| `SECRET_KEY` | Ya | — | Kunci sesi dan CSRF. Aplikasi menolak start bila kosong. |
| `SUPABASE_URL` | Ya | — | URL proyek Supabase. |
| `SUPABASE_KEY` | Ya | — | Kunci Supabase. |
| `DEEPSEEK_API_KEY` | Untuk AI | — | Kunci DeepSeek. |
| `DEEPSEEK_MODEL` | Tidak | `deepseek-chat` | Model DeepSeek. |
| `AI_DAILY_LIMIT` | Tidak | `20` | Batas pertanyaan asisten per pengguna per hari. |
| `SCRAPER_USER_AGENT` | Tidak | `KarirLensBot/1.0` | User agent pipeline data. |
| `SCRAPER_MAX_RETRY` | Tidak | `3` | Maksimum retry pengambilan data. |
| `CLUSTER_N_CLUSTERS` | Tidak | `6` | Jumlah cluster KMeans. |
| `CLUSTER_PCA_COMPONENTS` | Tidak | `2` | Komponen PCA sebelum KMeans. |
| `MAX_UPLOAD_BYTES` | Tidak | `5242880` | Batas ukuran berkas CV (5 MB). |
| `SESSION_COOKIE_SECURE` | Tidak | `false` | Set `true` pada produksi. |

Secret tidak boleh masuk repository. `.env` sudah di-ignore.

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
static/       css, js, vendor
migrations/   skema SQL
tests/        unit dan integration
docs/         PRD, arsitektur, design system, PRD per task
```

## Batasan

- Tidak ada tracker lamaran atau status lamaran.
- Tidak ada prediksi gaji; statistik hanya dari data faktual.
- Berkas dan teks CV tidak disimpan.
- Statistik gaji tidak tampil bila sampel kurang dari lima.
- Halaman perusahaan hanya memakai data yang diturunkan dari lowongan.
