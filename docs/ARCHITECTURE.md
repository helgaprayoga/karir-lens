# Arsitektur Kode KarirLens

| Field | Keterangan |
|---|---|
| Nama dokumen | Arsitektur Kode KarirLens |
| Versi | 1.0 |
| Status | Final untuk scope web |
| Pemilik | Helga Arya Prayoga |
| Mata kuliah | Praktik Aplikasi Web |
| Tanggal | 18 November 2026 |
| PRD induk | [PRD KarirLens](./PRD.md) |
| Design system | [Design System KarirLens](./design-system.md) |
| Daftar task | [PRD per Task](./tasks/README.md) |

Dokumen ini menetapkan bagaimana kode KarirLens disusun: di mana sebuah logika diletakkan, ke arah mana sebuah modul boleh bergantung, dan bagaimana aturan itu dijaga agar tetap berlaku sampai PRD-10. PRD menetapkan **apa** yang dibangun; dokumen ini menetapkan **di mana** kode yang membangunnya tinggal.

---

## 1. Ringkasan Keputusan

**Modular monolith dengan tiga lapisan per modul, ditopang satu shared kernel.**

```text
                    +-----------------------------------+
   Browser / curl   |  app/  (Flask)                    |
        |           |                                   |
        v           |  routes.py  --(HTTP saja)-->      |
   +---------+      |      |                            |
   | routes  |------+------+                            |
   +---------+      |      v                            |
                    |  service.py  (aturan bisnis)      |
                    |      |                            |
                    |      v                            |
                    |  repository.py  (query PostgREST) |
                    +------|----------------------------+
                           v
                    +------------------+
                    |   core/db.py     |-----> Supabase
                    +------------------+

   GitHub Actions --> scraper/ (CLI, tanpa Flask)
                        adapters/ -> pipeline/ -> core/db.py
                        cluster.py -> scikit-learn -> core/db.py
```

Satu kalimat: **vertikal per fitur, horizontal per tanggung jawab.**

- **Vertikal** — kode dipotong per fitur: `auth`, `jobs`, `insights`, `profile`, `cv`, `assistant`, `admin`, `api`, `main`. Berkas untuk satu fitur berada di satu folder.
- **Horizontal** — di dalam setiap modul ada tiga lapisan dengan tugas tunggal: `routes.py` (HTTP), `service.py` (aturan bisnis), `repository.py` (akses data).
- **Shared kernel** — `core/` berisi hal yang dipakai lebih dari satu modul dan lebih dari satu entrypoint. `core/` **tidak mengenal Flask**.

---

## 2. Konteks yang Membentuk Keputusan

Keputusan di atas bukan preferensi gaya. Ia diturunkan dari enam fakta proyek.

| Fakta | Sumber | Akibat pada arsitektur |
|---|---|---|
| REST API wajib memakai logika yang sama dengan halaman web, "tanpa duplikasi logika". | R-09-15, R-09-11 | Butuh lapisan `service` yang dapat dipanggil dua presenter berbeda (HTML dan JSON). |
| Satu client Supabase di-inject ke service layer; semua query berparameter. | R-01-05 | Butuh satu tempat pemilik client dan satu tempat query. |
| Query lowongan dipakai ulang API. | PRD-04 §9 menyebut `app/jobs/service.py` | Modul `jobs` sudah ditetapkan berbasis fitur, bukan berbasis lapisan global. |
| Dua entrypoint: aplikasi web (Render) dan pipeline data (GitHub Actions). | PRD §10.1, PRD-10 | Butuh paket bersama yang bebas framework, agar `scraper/` tidak menyeret Flask. |
| Supabase (PostgREST) mengembalikan `dict`/`list[dict]`, bukan objek domain. | PRD §10.3 | Entity, DTO, dan mapper tidak punya pekerjaan yang nyata. |
| Dikerjakan satu orang dalam 12–14 hari kerja, ~35 route, 10 task PRD. | PRD §16.1, §18 | Anggaran untuk lapisan seremonial hampir nol. Setiap berkas harus membayar dirinya sendiri. |

Domain KarirLens tipis. Aturan bisnis yang benar-benar ada hanyalah: deduplikasi lintas sumber, pencocokan skill berbasis kamus, aturan sampel gaji ≥ 5, hanya skill terkonfirmasi yang dipakai, rate limit asisten AI, dan larangan klaim di luar data pada jawaban AI. Enam aturan itu tidak butuh kerangka empat lapis; ia butuh **satu tempat yang jelas** untuk tinggal. Itulah `service.py`.

---

## 3. Keputusan dan Alternatif yang Ditolak

| Alternatif | Dipakai? | Alasan |
|---|---|---|
| **Modular monolith + 3 layer** | **Ya** | Memenuhi R-09-15 dan R-01-05 dengan biaya paling kecil. Satu folder per fitur, tiga berkas per folder. |
| Full Clean Architecture (entities / usecases / interface adapters / frameworks) | Tidak | Untuk `list jobs with filter`, sebuah usecase hanya membungkus satu panggilan repository. Jumlah berkas naik sekitar tiga kali lipat tanpa perubahan perilaku. Tidak ada rencana mengganti database, sehingga batas `framework`/`interface adapter` tidak membeli apa pun. |
| Repository interface abstrak + implementasi konkret | Tidak | Hanya ada satu implementasi: Supabase. Antarmuka dengan satu implementasi adalah lapisan tanpa nilai. Penggantian di test dilakukan lewat dependency injection pada `tests/conftest.py`. |
| ORM + entity + DTO mapper | Tidak | PostgREST mengembalikan `dict`. Mapper akan menjadi kode konversi bolak-balik tanpa manfaat. `dict` dipakai langsung sampai template/JSON. |
| DI container (`dependency-injector`, `punq`) | Tidak | `create_app()` dan fungsi modul sudah cukup. Container menambah satu konsep yang harus dipahami tanpa menyelesaikan masalah nyata di proyek sekecil ini. |
| MVC polos (logika bisnis di dalam blueprint) | Tidak | Langsung melanggar R-09-15: API akan menduplikasi query halaman web. |
| Package-by-layer global (`app/services/`, `app/repositories/`, `app/models/`) | Tidak | Menyebarkan satu fitur ke tiga folder. Path yang ditetapkan PRD (`app/jobs/service.py`) jauh lebih mudah ditelusuri saat mengerjakan task per task, dan memungkinkan fitur ditambah atau dihapus tanpa menyentuh fitur lain. |
| Microservice, atau scraper dipisah repo | Tidak | Target deploy Render Free + GitHub Actions. Satu repo, dua entrypoint sudah memenuhi pemisahan yang dibutuhkan. |
| Service berbasis class + `__init__` menampung dependency | Tidak | Fungsi bebas lebih mudah diuji dan dipanggil lintas modul. Dependency diambil dari `core/db.py` di dalam repository, bukan dioper lewat rantai konstruktor. |

---

## 4. Aturan Dependensi

Ini bagian yang mengikat. Semua aturan lain di dokumen ini turun dari sini.

| # | Aturan | Boleh | Tidak boleh |
|---|---|---|---|
| 1 | `routes.py` adalah lapisan HTTP | impor `service` modul sendiri, helper `core`, `flask` | impor `repository`, impor `supabase`, menulis query, memuat aturan bisnis |
| 2 | `service.py` adalah lapisan aturan bisnis | impor `repository` modul sendiri, `service` modul lain, `core/*` | impor `repository` modul lain, impor `flask`, memegang `request`/`session` |
| 3 | `repository.py` adalah lapisan data | impor `core/db.py` | impor `service`, impor modul lain, menyusun string SQL dari input pengguna |
| 4 | `core/*` adalah shared kernel | pustaka standar, pustaka pihak ketiga non-web, `core/*` | impor `flask`, impor `app.*`, impor `scraper.*` |
| 5 | `scraper/*` adalah entrypoint batch | `core/*`, pustaka data/HTTP | impor `flask`, impor `app.*` |
| 6 | Blueprint | diregistrasi hanya oleh `app/__init__.py` | saling mengimpor `routes.py` |
| 7 | `app/api/` adalah adapter presentasi | memanggil `service` modul lain, `core/errors`, `core/pagination` | menulis aturan bisnis, menulis query, menduplikasi logika `service` |

Aturan 4 dan 5 adalah alasan `core/` diletakkan di akar repo, **bukan** di dalam `app/`. Kalau `core` berada di dalam paket Flask, `scraper/` harus mengimpor `app`, dan pemisahan entrypoint runtuh.

Aturan 1–7 diuji otomatis (lihat §10), bukan hanya disepakati.

### Mengapa `routes.py` tidak boleh menyentuh repository

Kalau route memanggil repository langsung, ia melewati aturan bisnis. Contoh nyata di proyek ini: `insights/service.py` menolak menampilkan statistik gaji saat sampel < 5. Route yang memanggil repository langsung akan menampilkan angka yang seharusnya disembunyikan, dan aturan itu harus diulang di API. Satu jalur lewat service membuat aturan PRD hanya punya satu tempat tinggal.

### Mengapa `service.py` tidak boleh menyentuh `flask`

Service harus bisa dipanggil dari tiga konteks: route HTML, route JSON, dan test. Kalau service membaca `request.args` atau `session`, ia hanya bisa dipanggil dari dalam request Flask. Karena itu route yang mengekstrak input HTTP, lalu mengopernya sebagai parameter biasa.

```python
# app/jobs/routes.py
page = service.search_jobs(q=request.args.get("q"), page=request.args.get("page"))

# app/api/routes.py  -- service yang sama, presenter berbeda
return jsonify(data=page["items"], meta=page["meta"])
```

Dua baris di atas adalah wujud konkret R-09-15.

---

## 5. Matriks Dependensi Antar Modul

Modul hanya boleh bergantung ke bawah, dan tidak ada siklus.

| Modul | Memanggil service modul | Alasan |
|---|---|---|
| `main` | `jobs`, `insights` | Beranda menampilkan lowongan terbaru dan pintasan kategori. |
| `auth` | — | Berdiri sendiri di atas tabel `users`. |
| `jobs` | — | Modul paling dasar bersama `insights`. |
| `insights` | — | Membaca `jobs` dan `clusters` lewat repository-nya sendiri. |
| `profile` | — | Memiliki tabel `user_skills` dan `saved_jobs`. |
| `cv` | `jobs` | Rekomendasi membutuhkan kandidat lowongan. |
| `assistant` | `jobs`, `insights` | Menyusun konteks dari lowongan, cluster, dan statistik gaji. |
| `admin` | `jobs`, `insights` | Menampilkan, menghapus, dan meninjau data yang dimiliki modul tersebut. |
| `api` | `jobs`, `insights`, `profile`, `cv`, `assistant` | Adapter JSON untuk seluruh service. |

Dua keputusan yang perlu dijelaskan:

**`profile` tidak bergantung pada `cv`.** Konfirmasi skill adalah operasi milik `profile`; `cv` hanya mengusulkan skill. Arah ini mencegah siklus `cv → profile → cv` pada PRD-07.

**`insights` tidak bergantung pada `jobs`.** Insight membaca tabel `jobs` lewat repository miliknya sendiri. Yang dipakai bersama bukan repository, melainkan *bentuk data*: `core/pagination.py` menjamin metadata halaman identik, dan `core/text.py` menjamin normalisasi skill sama. Berbagi tabel antar modul boleh; berbagi repository tidak.

---

## 6. Struktur Direktori

```text
KarirLens/
├── app/                            # entrypoint web (Flask)
│   ├── __init__.py                 # create_app, registrasi blueprint, error handler, security header
│   ├── config.py                   # Development/Testing/ProductionConfig dari core.config
│   ├── extensions.py               # csrf, login_manager
│   │
│   ├── main/                       # beranda
│   │   ├── __init__.py             # bp = Blueprint("main", __name__)
│   │   └── routes.py
│   ├── auth/                       # registrasi, login, logout
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── forms.py
│   ├── jobs/                       # katalog publik: cari, filter, detail
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── repository.py
│   ├── insights/                   # kategori, skill, gaji, halaman perusahaan
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── salary.py               # median, P25, P75, aturan sampel >= 5
│   ├── profile/                    # profil, skill terkonfirmasi, bookmark
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── forms.py
│   ├── cv/                         # upload CV, ekstraksi skill, rekomendasi
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── extractor.py            # pypdf / python-docx -> teks -> skill
│   │   └── recommender.py          # skor deterministik, tanpa AI
│   ├── assistant/                  # asisten AI
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── service.py              # menyusun konteks + rate limit
│   ├── admin/                      # panel admin
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── repository.py
│   └── api/                        # adapter JSON, tanpa logika bisnis
│       ├── __init__.py
│       ├── routes.py
│       └── response.py             # {"data","meta"} dan {"error"}
│
├── core/                           # shared kernel, bebas Flask
│   ├── __init__.py
│   ├── config.py                   # _env_str/_env_int/_env_bool, Settings, validate_settings
│   ├── db.py                       # satu client Supabase, lazy
│   ├── errors.py                   # AppError, ValidationError, NotFoundError, ForbiddenError
│   ├── pagination.py               # parse_page, build_meta
│   ├── text.py                     # normalize_text, slugify, tokenize
│   ├── skills.py                   # preprocess, match_skills, is_ambiguous
│   ├── data/
│   │   └── skills.json             # kamus skill + sinonim
│   └── external/
│       ├── __init__.py
│       └── deepseek.py             # DeepSeekClient, implementation via requests
│
├── scraper/                        # entrypoint batch, bebas Flask
│   ├── __init__.py
│   ├── __main__.py                 # python -m scraper
│   ├── cli.py                      # argparse: run, cluster
│   ├── http.py                     # session, user agent, timeout, backoff, robots.txt
│   ├── runner.py                   # satu-satunya orkestrator ingestion
│   ├── cluster.py                  # TF-IDF -> PCA -> KMeans -> clusters
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAdapter (port)
│   │   ├── dealls.py
│   │   ├── kalibrr.py
│   │   ├── remotive.py
│   │   └── registry.py
│   └── pipeline/
│       ├── __init__.py
│       ├── normalize.py            # PRD-03
│       ├── dedup.py                # PRD-03, dedup_hash
│       └── persist.py              # insert-or-update idempoten
│
├── templates/                      # Jinja, mengikuti nama modul
│   ├── base.html
│   ├── auth/  jobs/  insights/  profile/  cv/  assistant/  admin/  errors/
├── static/
│   ├── css/  js/
│   └── vendor/                     # chart.umd.min.js, bootstrap
├── migrations/
│   └── 001_initial_schema.sql
├── tests/
│   ├── conftest.py
│   ├── fixtures/                   # HTML/JSON sumber, CV sintetis, dataset kecil
│   ├── unit/
│   └── integration/
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── README.md
└── render.yaml                     # PRD-10
```

Berkas `render.yaml`, `.github/workflows/`, `docs/API.md`, dan `docs/IMPLEMENTASI.md` belum dibuat; itu pekerjaan PRD-10.

---

## 7. Kontrak Tiap Lapisan

### 7.1 `routes.py` — HTTP saja

```python
from flask import Blueprint, render_template, request
from . import service

bp = Blueprint("jobs", __name__, url_prefix="/jobs")

@bp.get("/")
def index():
    result = service.search_jobs(
        q=request.args.get("q"),
        city=request.args.get("city"),
        employment_type=request.args.get("employment_type"),
        source=request.args.get("source"),
        sort=request.args.get("sort"),
        page=request.args.get("page"),
        per_page=request.args.get("per_page"),
    )
    return render_template("jobs/list.html", **result)
```

Boleh: membaca `request`, memanggil service, memilih template, menyusun redirect/flash.
Tidak boleh: query, aturan bisnis, `try/except` untuk error domain (sudah ditangani handler global).

### 7.2 `service.py` — aturan bisnis

Fungsi bebas. Menerima tipe primitif, mengembalikan `dict` siap render atau JSON. Di sinilah aturan PRD hidup:

| Modul | Aturan yang tinggal di sini |
|---|---|
| `jobs` | Validasi filter defensif (nilai di luar himpunan direset ke default), susun kriteria, bangun metadata halaman. |
| `insights` | Statistik gaji hanya jika sampel ≥ 5, dipisah per `salary_currency` dan `salary_period`, tanpa field prediksi. |
| `profile` | Hanya `is_confirmed = true` yang dipakai fitur lain; bookmark unik per pengguna dan lowongan. |
| `cv` | Validasi tipe/ukuran berkas, ekstraksi lokal lebih dulu, AI hanya untuk skill ambigu, hapus berkas sementara di blok `finally`. |
| `assistant` | Konteks hanya dari data aplikasi, tolak jika konteks kosong, rate limit per pengguna. |
| `admin` | Satu ringkasan agregat untuk kartu dan tabel. |

```python
# app/insights/service.py
from core.errors import ValidationError
from . import repository, salary

MIN_SALARY_SAMPLE = 5

def get_salary_stats(currency=None, period=None):
    rows = repository.find_salary_rows(currency=currency, period=period)
    groups = salary.group_by_currency_period(rows)

    result = []
    for key, values in groups.items():
        if len(values) < MIN_SALARY_SAMPLE:
            continue                       # R-05-08: sembunyikan, bukan tampilkan kosong
        result.append(salary.summarize(key, values))

    return {"sample_sufficient": bool(result), "items": result}
```

Fungsi di atas dipanggil halaman `/insights` dan `/api/insights/salary` tanpa perubahan. Itu memenuhi R-05-15 dan R-09-15 sekaligus.

### 7.3 `repository.py` — akses data

Satu-satunya tempat query PostgREST hidup. Mengembalikan `dict`/`list[dict]` apa adanya.

```python
from core import db

TABLE = "jobs"

def find_page(criteria: dict, offset: int, limit: int) -> list[dict]:
    query = db.get_db().table(TABLE).select("*")

    if criteria.get("q"):
        query = query.or_(
            f"title.ilike.%{criteria['q']}%,company_name.ilike.%{criteria['q']}%"
        )
    if criteria.get("city"):
        query = query.eq("location", criteria["city"])

    return query.order("posted_at", desc=True).range(offset, offset + limit - 1).execute().data
```

Aturan keras: **tidak ada string SQL/interpolasi filter yang dibangun dari input pengguna.** Filter PostgREST disusun dari daftar kunci yang diizinkan pada `service.py`; nilai diikat oleh builder PostgREST. Repository hanya tahu tabelnya sendiri.

### 7.4 `core/` — shared kernel

| Berkas | Isi | Dipakai oleh |
|---|---|---|
| `config.py` | `_env_str`/`_env_int`/`_env_bool`, `Settings`, `validate_settings()`. Fail-fast dengan pesan jelas. | `app`, `scraper`, `tests` |
| `db.py` | `get_db()` mengembalikan satu client Supabase, dibuat lazy pada pemanggilan pertama. | seluruh `repository.py`, `scraper/pipeline/persist.py` |
| `errors.py` | `AppError(code, message, status)` dan turunannya, dengan `to_dict()`. | service, error handler |
| `pagination.py` | `parse_page(args)`, `build_meta()`. Satu sumber kebenaran untuk `page`/`per_page`/`total`/`has_next`. | `jobs`, `admin`, `api` |
| `text.py` | `normalize_text`, `slugify`, `normalize_company`, `tokenize`. | `scraper/pipeline/normalize.py`, `cv/extractor.py` |
| `skills.py` | `preprocess()`, `match_skills()`, `is_ambiguous()`, memuat `data/skills.json` dan memvalidasinya saat start. | `scraper/pipeline/normalize.py`, `cv/extractor.py`, `profile` |
| `external/deepseek.py` | `Protocol` + implementasi `requests` dengan timeout eksplisit. | `assistant`, `cv` (fallback) |

`core/text.py` dan `core/skills.py` ada di `core/` bukan di `scraper/` karena R-07-04 menuntut normalisasi skill CV **sama persis** dengan normalisasi skill lowongan dari PRD-03. Menaruhnya di `core/` membuat kesamaan itu terjamin oleh satu implementasi, bukan oleh dua salinan yang harus disamakan manual.

### 7.5 `scraper/` — ports and adapters

Bagian ini memang memakai arsitektur berbeda, karena masalahnya berbeda: sumber eksternal yang berubah sewaktu-waktu.

```text
adapters/base.py        BaseAdapter  (port)  ->  fetch / parse / iter_jobs / is_allowed
adapters/dealls.py      implementasi          \
adapters/kalibrr.py     implementasi           >  registry.py  ->  runner.py
adapters/remotive.py    implementasi          /
pipeline/normalize.py   RawJob -> Job bersih
pipeline/dedup.py       dedup_hash, penggabungan lintas sumber
pipeline/persist.py     insert-or-update idempoten
```

`BaseAdapter` adalah satu-satunya antarmuka abstrak di proyek ini, dan ia memang layak ada: ada tiga implementasi nyata dengan kontrak sama (R-02-01), dan menambah sumber keempat cukup menambah satu modul. Bandingkan dengan abstraksi repository yang hanya akan punya satu implementasi — itulah bedanya.

`runner.py` adalah satu-satunya orkestrator. Adapter tidak saling memanggil (PRD-02 §9). `cluster.py` adalah job batch yang tidak pernah dipanggil dari request web (PRD-05 §9).

---

## 8. Alur Permintaan dan Alur Error

### 8.1 Alur normal

```text
GET /jobs?q=python&city=Jakarta
  -> app/jobs/routes.py            baca request.args
  -> app/jobs/service.py           validasi filter, susun kriteria, panggil repository
  -> app/jobs/repository.py        query PostgREST terikat
  -> core/db.py                    client Supabase
  <- list[dict] + meta             core/pagination.py
  <- templates/jobs/list.html      Jinja
```

### 8.2 Alur API untuk data yang sama

```text
GET /api/jobs?q=python&city=Jakarta
  -> app/api/routes.py             baca request.args
  -> app/jobs/service.py           fungsi yang sama persis
  <- app/api/response.py           {"data": [...], "meta": {...}}
```

Tidak ada query kedua, tidak ada aturan kedua.

### 8.3 Alur error

Semua error domain dilempar sebagai `AppError`, bukan `return` kode status dari dalam service.

```python
# service
raise NotFoundError("Lowongan tidak ditemukan.")

# app/__init__.py -- satu handler untuk semua
@app.errorhandler(AppError)
def handle_app_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.to_dict()}), error.status
    return render_template("errors/error.html", error=error), error.status
```

Konsekuensinya: service bebas dari `flask` (aturan 2), format error konsisten di seluruh endpoint (R-09-13), dan tiap route tidak perlu `try/except` berulang. Halaman HTML mendapat halaman ramah tanpa stack trace (R-01-12).

---

## 9. Pedoman Penempatan Kode

Saat mengerjakan PRD-02 sampai PRD-10, pertanyaan pertama selalu sama: "kode ini taruh di mana?"

| Jenis kode | Tempat | Contoh |
|---|---|---|
| Membaca `request`, memilih template, redirect | `app/<modul>/routes.py` | `@bp.get("/jobs")` |
| Memvalidasi kombinasi filter, aturan bisnis | `app/<modul>/service.py` | aturan sampel gaji ≥ 5 |
| Membangun klausa query, memanggil PostgREST | `app/<modul>/repository.py` | `find_page(criteria, offset, limit)` |
| Bentuk respons JSON atau format error | `app/api/response.py`, `core/errors.py` | `{"data","meta"}` |
| Normalisasi teks, kamus skill, hash dedup | `core/text.py`, `core/skills.py` | `preprocess("JS") -> "javascript"` |
| Metadata halaman | `core/pagination.py` | `build_meta(page, per_page, total)` |
| Panggilan HTTP ke DeepSeek | `core/external/deepseek.py` | `client.chat(messages)` |
| Membaca HTML sumber lowongan | `scraper/adapters/<sumber>.py` | `parse(item)` |
| Membersihkan dan menggabungkan data | `scraper/pipeline/` | `dedup.compute_hash(job)` |
| Clustering | `scraper/cluster.py` | TF-IDF → PCA → KMeans |
| Form dan validasinya | `app/<modul>/forms.py` | `RegisterForm` |
| Template | `templates/<modul>/` | `templates/jobs/list.html` |

Aturan penentu ketika ragu: **kalau kode itu perlu berjalan tanpa HTTP, ia tidak boleh berada di `routes.py`. Kalau kode itu perlu berjalan tanpa Flask sama sekali, ia harus berada di `core/` atau `scraper/`.**

---

## 10. Penjagaan Otomatis

Diagram arsitektur yang tidak diuji akan luntur pada task ketiga. Karena itu aturan §4 dijaga oleh `tests/unit/test_architecture.py`, yang membaca AST setiap berkas dan menegakkan tiga hal:

1. Tidak ada `app/*/routes.py` yang mengimpor `supabase` atau `app.*.repository`.
2. Tidak ada berkas di `core/` maupun `scraper/` yang mengimpor `flask`.
3. Tidak ada `app/*/service.py` yang mengimpor `app/<modul lain>/repository.py`.

Test ini cepat, tidak menyentuh jaringan, dan langsung memberi tahu ketika sebuah task PRD mulai memotong lapisan. Ia juga berlaku sebagai dokumentasi yang tidak bisa basi: AST menyatakan aturan dengan lebih tepat daripada prosa.

Selain itu, `validate_settings()` memastikan aplikasi gagal start dengan pesan jelas ketika `SECRET_KEY` atau kredensial Supabase tidak tersedia (R-01-04), alih-alih meledak pada request pertama.

---

## 11. Pemetaan Task PRD ke Direktori

| Task | Direktori utama yang disentuh |
|---|---|
| PRD-01 Fondasi | `app/__init__.py`, `app/config.py`, `app/extensions.py`, `core/{config,db,errors,pagination}.py`, `app/auth/`, `templates/base.html`, `templates/errors/`, `migrations/` |
| PRD-02 Data ingestion | `scraper/{http,runner,cli}.py`, `scraper/adapters/`, `scraper/pipeline/persist.py` |
| PRD-03 Normalisasi & deduplikasi | `scraper/pipeline/{normalize,dedup}.py`, `core/{text,skills}.py`, `core/data/skills.json` |
| PRD-04 Katalog publik | `app/main/`, `app/jobs/`, `templates/jobs/`, `app/api/routes.py` (bagian jobs) |
| PRD-05 Perusahaan & insight | `app/insights/`, `scraper/cluster.py`, `templates/insights/`, `static/js/` (Chart.js) |
| PRD-06 Akun & bookmark | `app/auth/`, `app/profile/`, `templates/profile/` |
| PRD-07 CV & rekomendasi | `app/cv/`, `core/skills.py`, `templates/cv/` |
| PRD-08 Asisten AI | `app/assistant/`, `core/external/deepseek.py`, `templates/assistant/` |
| PRD-09 Admin & API | `app/admin/`, `app/api/{routes,response}.py`, `templates/admin/` |
| PRD-10 Kualitas & rilis | `.github/workflows/`, `render.yaml`, `tests/`, `README.md`, `docs/API.md` |

Setiap task hanya menyentuh folder modulnya sendiri, kecuali `core/` ketika ia menambah aturan yang dipakai bersama (PRD-03 dan PRD-07). Itu sebabnya `core/` dijaga ketat: ia satu-satunya berkas yang dipakai semua orang.

---

## 12. Penyesuaian terhadap PRD

Dokumen ini menyempurnakan tiga hal pada PRD yang sudah ada. Semuanya bersifat penempatan berkas, bukan perubahan fitur.

| Pada | Sebelum | Sesudah | Alasan |
|---|---|---|---|
| PRD-01 R-01-01 | Struktur direktori belum menyebut `core/` dan belum menyebut pola tiga lapisan | Struktur mengikuti §6 dokumen ini | Shared kernel harus berada di luar `app/` agar `scraper/` bebas Flask. |
| PRD-01 R-01-05 | Client Supabase "di-inject ke service layer" | Client dimiliki `core/db.py` dan diakses lewat `repository.py`; service tidak menyentuh client | Menjaga aturan 2 dan 3: service tidak boleh tahu cara data diambil. |
| PRD-07 §10 | Kamus skill disebut `cv/skill_dict.py` | `core/skills.py` + `core/data/skills.json` | R-07-04 menuntut normalisasi sama dengan PRD-03. Kamus di `core/` menjamin satu implementasi, bukan dua. |

Tidak ada fitur, route, tabel, atau acceptance criteria yang berubah.

---

## 13. Konsekuensi

Yang diperoleh:

- R-09-15 (API dan web berbagi service) terpenuhi secara struktural, bukan kebetulan.
- Modul dapat dikerjakan berurutan sesuai PRD-02 sampai PRD-10 tanpa saling menabrak.
- `scraper/` dapat jalan di GitHub Actions tanpa memasang Flask.
- Aturan arsitektur dijaga test, jadi tetap berlaku di akhir proyek.

Yang dikorbankan:

- Jumlah berkas lebih banyak dibanding satu modul satu berkas. Ini disengaja: satu berkas per lapisan membuat batas tanggung jawab terlihat.
- Beberapa fungsi service hanya membungkus satu panggilan repository. Ini juga disengaja: tempat tinggal aturan bisnis harus ada sebelum aturannya bertambah, dan `insights` serta `jobs` sudah membuktikan bahwa tempat itu terpakai.
- Tidak ada `entity`/`DTO`, sehingga `dict` dari Supabase mengalir sampai template. Untuk ukuran proyek ini itu keuntungan, bukan kerugian: tidak ada kode konversi yang harus dijaga sinkron dengan skema.

Yang akan memicu peninjauan ulang:

- Jika jumlah sumber lowongan melewati sekitar enam, `BaseAdapter` tetap memadai; yang perlu ditinjau adalah `runner.py`, bukan lapisannya.
- Jika kelak ada kebutuhan mengganti Supabase dengan penyimpanan lain, repository sudah menjadi satu-satunya titik yang perlu diubah — di situlah keuntungan memisahkan `repository.py` sejak awal akan terasa.
