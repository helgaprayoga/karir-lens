# PRD-01 — Fondasi Proyek

| Field | Keterangan |
|---|---|
| ID task | PRD-01 |
| Nama task | Fondasi Proyek |
| Prioritas | P0 |
| Milestone | M1 Fondasi (1-2 hari) |
| Dependensi | Tidak ada |
| Task yang bergantung | PRD-02 s.d. PRD-10 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Arsitektur kode | [Arsitektur Kode KarirLens](../ARCHITECTURE.md) |

---

## 1. Konteks

Repository KarirLens saat ini baru berisi dokumen perencanaan di `docs/`. Belum ada kode aplikasi, koneksi database, maupun layout web. Semua task lain bergantung pada struktur proyek yang konsisten, konfigurasi yang aman, koneksi Supabase yang dapat dipakai ulang, skema database awal, dan alur autentikasi dasar.

Task ini menghasilkan kerangka aplikasi yang dapat dijalankan secara lokal (`flask run`), terhubung ke Supabase, memiliki layout dasar Bootstrap berbahasa Indonesia, serta halaman registrasi, login, dan logout yang aman. Fitur bisnis (scraper, katalog, insight, CV, AI, admin) belum diisi detail pada task ini.

## 2. Tujuan

1. Menetapkan struktur direktori dan pola aplikasi Flask (application factory + blueprint) yang dipakai seluruh task berikutnya.
2. Menyediakan konfigurasi berbasis environment variable tanpa secret di repository.
3. Menyediakan koneksi Supabase dan helper query berparameter.
4. Membuat skema database awal sesuai model data PRD induk.
5. Menyediakan layout dasar, navigasi, flash message, dan halaman error.
6. Menyediakan autentikasi dasar (registrasi, login, logout) dengan password hash dan sesi aman.

## 3. Scope

### 3.1 Termasuk

- Struktur proyek Python/Flask dan `requirements.txt`.
- Application factory, konfigurasi per environment, dan registrasi blueprint.
- Koneksi Supabase, helper query berparameter, dan penanganan error koneksi.
- Skema database awal untuk `sources`, `jobs`, `scrape_runs`, `users`, `saved_jobs`, `user_skills`, dan `clusters`.
- Layout dasar Bootstrap responsif (mulai lebar 360 px) dengan navigasi dan footer.
- Halaman registrasi, login, dan logout dasar.
- Halaman error 404 dan 500 yang ramah pengguna.
- Logging dasar yang tidak memuat data sensitif.
- `.gitignore`, `.env.example`, dan README awal.

### 3.2 Tidak termasuk

- Scraper dan pembaruan data (PRD-02, PRD-03).
- Halaman katalog publik dan inset (PRD-04, PRD-05).
- Profil pengguna, bookmark, CV, rekomendasi, AI, admin, dan REST API (PRD-06 sampai PRD-09).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-01-01 | Struktur direktori mengikuti pola modular monolith tiga lapisan pada [Arsitektur Kode §6](../ARCHITECTURE.md): `app/` berisi satu folder per fitur dengan `routes.py`/`service.py`/`repository.py`, `core/` sebagai shared kernel bebas Flask, `scraper/` sebagai entrypoint batch, ditambah `templates/`, `static/`, `tests/`, `migrations/`. | P0 |
| R-01-02 | `create_app(config)` membuat instance Flask, memuat konfigurasi, dan meregistrasi semua blueprint. Blueprint awal: `main`, `auth`, `jobs`, `insights`, `profile`, `cv`, `assistant`, `admin`, `api`. `api` adalah satu blueprint untuk seluruh endpoint JSON, bukan satu blueprint per resource. | P0 |
| R-01-03 | Konfigurasi dibaca dari environment variable: `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `SCRAPER_USER_AGENT`, `SCRAPER_MAX_RETRY`, `AI_DAILY_LIMIT`. Nilai default non-sensitif boleh ada, secret tidak. | P0 |
| R-01-04 | Aplikasi gagal start dengan pesan jelas jika `SECRET_KEY` atau kredensial Supabase tidak tersedia. | P0 |
| R-01-05 | Satu client Supabase dimiliki `core/db.py` dan dibuat lazy. Hanya `repository.py` dan `scraper/pipeline/persist.py` yang mengaksesnya; `service.py` dan `routes.py` tidak pernah menyentuh client maupun query. Semua query memakai parameter, bukan string mentah. | P0 |
| R-01-06 | Skema database awal dibuat melalui file SQL di `migrations/` dan dapat dijalankan ulang tanpa error. | P0 |
| R-01-07 | Skema memuat constraint unik: `saved_jobs(user_id, job_id)`, `users.email`, dan index untuk `jobs.source_url`, `jobs.dedup_hash`, `jobs.posted_at`, serta `jobs.company_slug`. | P0 |
| R-01-08 | Layout dasar memakai Bootstrap, Bahasa Indonesia, navigasi keyboard-friendly, dan responsif mulai 360 px. | P0 |
| R-01-09 | Registrasi memvalidasi format email, panjang password minimal 8 karakter, email unik, dan menyimpan password dengan hash (`werkzeug.security`). | P0 |
| R-01-10 | Login membuat sesi; logout menghapus sesi. Cookie sesi memakai `HttpOnly`, `SameSite=Lax`, dan `Secure` pada environment produksi. | P0 |
| R-01-11 | Form POST dilindungi CSRF (Flask-WTF). Pesan validasi tampil di dekat field terkait. | P0 |
| R-01-12 | Halaman 404 dan 500 menampilkan pesan ramah Bahasa Indonesia tanpa stack trace ke pengguna. | P0 |
| R-01-13 | Logging tidak menulis password, token, isi CV, atau secret. Error dicatat dengan level dan konteks minimal. | P0 |
| R-01-14 | `README.md` menjelaskan cara menjalankan aplikasi dan variabel environment yang diperlukan. | P1 |

### 4.1 Struktur Direktori Acuan

Struktur lengkap beserta tanggung jawab tiap berkas ada di [Arsitektur Kode §6](../ARCHITECTURE.md). Ringkasan yang harus terbentuk pada task ini:

```text
KarirLens/
  app/
    __init__.py          # create_app, registrasi blueprint, error handler, security header
    config.py            # Development/Testing/ProductionConfig
    extensions.py        # csrf, login_manager
    main/routes.py
    auth/                # routes.py, service.py, repository.py, forms.py
    jobs/                # routes.py, service.py, repository.py (dikosongkan dulu)
    insights/            # routes.py, service.py, repository.py, salary.py (dikosongkan dulu)
    profile/             # routes.py, service.py, repository.py, forms.py (dikosongkan dulu)
    cv/                  # routes.py, service.py, repository.py, extractor.py, recommender.py
    assistant/           # routes.py, service.py
    admin/               # routes.py, service.py, repository.py
    api/                 # routes.py, response.py
  core/                  # shared kernel, bebas Flask
    config.py            # _env_* helper, Settings, validate_settings
    db.py                # satu client Supabase, lazy
    errors.py            # AppError dan turunannya
    pagination.py        # parse_page, build_meta
    text.py              # normalize_text, slugify, tokenize
    skills.py            # preprocess, match_skills (+ data/skills.json)
    external/deepseek.py # DeepSeekClient
  scraper/               # entrypoint batch, bebas Flask (PRD-02)
    __main__.py, cli.py, http.py, runner.py
    adapters/, pipeline/
  templates/
    base.html
    auth/
    errors/
  static/
    css/
    js/
  migrations/
    001_initial_schema.sql
  tests/
  requirements.txt
  .env.example
  .gitignore
  README.md
```

`core/` sengaja berada di akar repo, bukan di dalam `app/`, agar `scraper/` dapat berjalan di GitHub Actions tanpa memasang Flask. Arah dependensi antar lapisan ditetapkan pada [Arsitektur Kode §4](../ARCHITECTURE.md) dan dijaga oleh `tests/unit/test_architecture.py`.

### 4.2 Skema Database Awal

```sql
create table sources (
  id bigint generated always as identity primary key,
  name text not null unique,
  base_url text not null,
  last_scraped_at timestamptz
);

create table jobs (
  id bigint generated always as identity primary key,
  title text not null,
  company_name text,
  company_slug text,
  location text,
  employment_type text,
  description text,
  skills text[] default '{}',
  salary_min numeric,
  salary_max numeric,
  salary_currency text,
  salary_period text,
  source_id bigint references sources(id),
  source_url text not null unique,
  source_job_id text,
  posted_at timestamptz,
  scraped_at timestamptz not null default now(),
  dedup_hash text,
  cluster_id bigint references clusters(id)
);

create table scrape_runs (
  id bigint generated always as identity primary key,
  source_id bigint references sources(id),
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,
  jobs_found integer default 0,
  jobs_inserted integer default 0,
  jobs_updated integer default 0,
  error_message text
);

create table users (
  id bigint generated always as identity primary key,
  email text not null unique,
  password_hash text not null,
  name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table saved_jobs (
  user_id bigint not null references users(id),
  job_id bigint not null references jobs(id),
  created_at timestamptz not null default now(),
  unique (user_id, job_id)
);

create table user_skills (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id),
  skill text not null,
  source text,
  is_confirmed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table clusters (
  id bigint generated always as identity primary key,
  label text not null,
  keywords text[] default '{}',
  job_count integer default 0,
  created_at timestamptz not null default now()
);
```

Catatan: `jobs.cluster_id` dan tabel `clusters` dibuat sejak awal agar migrasi tidak perlu diulang; pengisiannya dilakukan pada PRD-05.

## 5. Acceptance Criteria

- [ ] `flask run` menjalankan aplikasi tanpa error pada environment lokal dengan `.env` valid.
- [ ] Semua tabel pada §4.2 terbentuk setelah migrasi dijalankan.
- [ ] Registrasi membuat user baru dengan `password_hash` (tidak ada password mentah).
- [ ] Login berhasil untuk kredensial valid dan gagal dengan pesan jelas untuk kredensial salah.
- [ ] Logout menghapus sesi dan mengembalikan pengguna ke halaman publik.
- [ ] Cookie sesi memakai `HttpOnly` dan `SameSite`; `Secure` aktif saat produksi.
- [ ] Form registrasi dan login memiliki perlindungan CSRF yang terbukti (tanpa token ditolak).
- [ ] Layout tampil rapi pada lebar 360 px, 768 px, dan 1280 px.
- [ ] Halaman 404 dan 500 tampil tanpa stack trace.
- [ ] Tidak ada secret yang masuk ke repository (`.env` di-ignore, `.env.example` hanya placeholder).
- [ ] `README.md` dapat diikuti dari nol sampai aplikasi berjalan.

## 6. Dependensi

- Akun Supabase beserta `SUPABASE_URL` dan `SUPABASE_KEY`.
- Python 3.11+ dan akses instalasi paket (`Flask`, `Flask-WTF`, `supabase`, `python-dotenv`, `pytest`).
- Tidak ada dependensi task lain.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_create_app` | `create_app("testing")` mengembalikan app dengan konfigurasi testing. |
| `test_missing_secret_fails_fast` | Aplikasi menolak start jika `SECRET_KEY`/kredensial kosong. |
| `test_register_hashes_password` | Password tersimpan sebagai hash dan bukan teks asli. |
| `test_register_rejects_duplicate_email` | Email duplikat menghasilkan error validasi. |
| `test_login_logout_flow` | Login sukses membuat sesi; logout menghapus akses halaman personal. |
| `test_csrf_required` | POST tanpa token CSRF ditolak (400). |
| `test_error_pages` | 404 dan 500 merender template tanpa detail internal. |
| `test_architecture_rules` | `tests/unit/test_architecture.py` menegakkan aturan dependensi [Arsitektur §4](../ARCHITECTURE.md): tidak ada `routes.py` yang mengimpor `supabase`/`repository`, tidak ada `core/` atau `scraper/` yang mengimpor `flask`, tidak ada `service.py` yang mengimpor `repository` modul lain. |
| `test_schema_exists` | Tabel inti tersedia (integration test, di-skip jika kredensial tidak ada). |

### 7.2 Pengujian Manual

1. Jalankan migrasi pada project Supabase baru.
2. Registrasi akun, login, logout, lalu login kembali.
3. Coba akses halaman personal tanpa login dan pastikan diarahkan ke login.
4. Periksa cookie sesi di browser (HttpOnly, SameSite, Secure di produksi).
5. Uji tampilan pada 360 px, 768 px, dan 1280 px.
6. Pastikan halaman error tampil ramah saat memanggil route yang tidak ada.

## 8. Out of Scope

- Logika scraping, normalisasi, deduplikasi, dan riwayat proses.
- Pencarian, filter, detail lowongan, dan halaman perusahaan.
- Clustering, insight kategori, skill, dan statistik gaji.
- Profil lengkap, bookmark, upload CV, rekomendasi, dan asisten AI.
- Panel admin dan REST API.
- Deployment Render dan GitHub Actions (PRD-10).

## 9. Catatan Teknis

- Gunakan pola application factory agar test dapat memakai konfigurasi terpisah.
- Ikuti aturan dependensi pada [Arsitektur Kode §4](../ARCHITECTURE.md): `routes.py` → `service.py` → `repository.py`, satu arah, tanpa lompatan lapisan.
- `core/` adalah shared kernel dan **tidak boleh mengimpor `flask`**. `scraper/` juga tidak boleh mengimpor `flask`, agar pipeline data dapat berjalan di GitHub Actions tanpa dependensi web.
- Setiap modul memiliki `service.py`, termasuk modul yang belum punya route. Tempat tinggal aturan bisnis harus ada sebelum aturannya bertambah; `app/jobs/service.py` dan `app/insights/service.py` dipakai ulang API pada PRD-09.
- `core/db.py` memegang satu client Supabase. `routes.py` dan `service.py` tidak menyentuh client maupun query; hanya `repository.py` yang melakukannya.
- Autentikasi memakai Flask-Login dengan `user_loader` membaca tabel `users`.
- Gunakan satu dekorator `login_required` untuk seluruh halaman personal, dan `admin_required` disiapkan di PRD-09.
- Semua query Supabase memakai parameter terikat; hindari string interpolation.
- CSRF wajib untuk seluruh form; API pada PRD-09 akan mengecualikan endpoint tertentu secara eksplisit.
- Skema awal tidak menambah tabel `applications` dan tidak menyimpan file atau teks CV.
- `tests/unit/test_architecture.py` dibuat pada task ini dan harus tetap lulus pada setiap task berikutnya.

## 10. Referensi Proyek

| Proyek | Berkas rujukan | Bagian yang diadopsi |
|---|---|---|
| Bot Utang-Piutang (Praktik Scripting Pertemuan 8) | `D:\Semester 5\Praktik Scripting\Pertemuan 8\web.py` | Application factory `create_app(db_path, secret_key)`, `app.config.update(...)` dengan `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`, `PERMANENT_SESSION_LIFETIME`, `@app.after_request` untuk header keamanan, serta `templates/error.html` untuk galat. |
| BengkelBot (Praktik Aplikasi Web Pertemuan 8) | `D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot\app.py` | `create_app(config=None)` dengan injeksi config untuk pengujian, `MAX_CONTENT_LENGTH`, dan error handler 404/413/500 yang membedakan respons `/api/` dari halaman HTML. |
| Bot Rekap Lowongan Dealls (Praktik Scripting Pertemuan 9) | `D:\Semester 5\Praktik Scripting\Pertemuan 9\config.py`, `db.py` | Konfigurasi terpusat melalui helper `_env_str/_env_int/_env_bool` dengan default aman, `load_dotenv()`, serta pola `CREATE TABLE IF NOT EXISTS` + fungsi `_migrasi()` untuk menambah kolom baru tanpa membuang database lama. |

**Pola yang diadopsi**

- Satu application factory yang menerima config, sehingga test memakai konfigurasi terpisah tanpa menyentuh environment produksi.
- Kredensial dibaca lewat helper environment dengan default non-sensitif; proses berhenti dengan pesan jelas bila `SECRET_KEY` tidak ada.
- Migrasi bertahap: skema dibuat idempoten dan kolom baru ditambahkan lewat fungsi migrasi, bukan dengan menghapus tabel.
- Header keamanan dan halaman error dipusatkan di satu tempat, bukan diulang per route.

**Yang tidak diambil**

- `web_auth.py` memakai token bertanda tangan dari bot Telegram sebagai pengganti login. KarirLens memakai registrasi email/password, sehingga pola token tersebut hanya dipakai sebagai acuan penamaan sesi, bukan sebagai alur login.
- Tidak ada proyek referensi yang memakai hash password, CSRF, atau Flask-Login. Bagian itu tetap mengikuti PRD induk dan tidak direferensikan ke proyek lain.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- README dan `.env.example` tersedia.
- Tidak ada secret, file `.env`, atau kredensial di repository.
