# API KarirLens

REST API untuk data lowongan, insight, dan data pribadi pengguna. Kontrak ini
dipenuhi `app/api/routes.py`; setiap endpoint memanggil fungsi `service` yang
sama dengan halaman web, sehingga hasil web dan API tidak mungkin berbeda
(R-09-15).

- Base URL lokal: `http://127.0.0.1:5000`
- Base URL produksi: `https://karir-lens.onrender.com`
- Format: JSON, `Content-Type: application/json`
- Autentikasi: **sesi cookie**, bukan token. Endpoint bertanda *Pengguna*
  memerlukan sesi hasil login.

---

## 1. Format respons

### Berhasil

```json
{
  "data": {},
  "meta": { "page": 1, "per_page": 12, "total": 120, "has_next": true }
}
```

`meta` hanya ada pada endpoint daftar. Endpoint tunggal mengembalikan `data`
saja.

### Gagal

```json
{
  "error": { "code": "NOT_FOUND", "message": "Lowongan tidak ditemukan." }
}
```

| Status | `code` | Kapan |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Body/parameter tidak valid |
| 401 | `UNAUTHORIZED` | Endpoint pengguna tanpa sesi |
| 403 | `FORBIDDEN` | Bukan admin pada halaman admin |
| 404 | `NOT_FOUND` | ID atau slug tidak ada |
| 413 | `PAYLOAD_TOO_LARGE` | Berkas CV melebihi batas |
| 429 | `RATE_LIMITED` | Batas pertanyaan asisten harian habis |
| 500 | `INTERNAL_ERROR` | Kesalahan tak terduga |
| 502 | `EXTERNAL_SERVICE_ERROR` | DeepSeek tidak dapat dihubungi |

Pesan galat tidak pernah memuat traceback, nama tabel, atau isi berkas.

---

## 2. Pagination

Dua parameter, berlaku pada endpoint daftar:

| Parameter | Bawaan | Batas |
|---|---|---|
| `page` | `1` | minimal 1 |
| `per_page` | `12` | 1–50 |

Nilai non-numerik atau di luar rentang **dijatuhkan ke default**, bukan
menghasilkan error (R-04-02). `meta.has_next` menentukan apakah halaman
berikutnya ada — jangan menebak dari panjang `data`.

---

## 3. Endpoint publik

Tidak memerlukan sesi (R-09-14).

### `GET /api/jobs`

Daftar lowongan dengan pencarian, filter, dan urutan.

| Parameter | Contoh | Keterangan |
|---|---|---|
| `q` | `python` | Judul, perusahaan, atau skill |
| `city` | `Jakarta` atau `Jakarta,Bandung` | Banyak nilai dipisah koma atau diulang |
| `employment_type` | `full-time` | `full-time`, `part-time`, `contract`, `internship`, `freelance` |
| `source` | `dealls` | `dealls`, `kalibrr`, `remotive` |
| `category` | `2` | `cluster_id` dari `/api/insights/categories` |
| `sort` | `posted_desc` | `posted_desc`, `posted_asc`, `relevance` |
| `page`, `per_page` | `2`, `24` | Lihat §2 |

Nilai di luar himpunan baku **dibuang**, bukan menghasilkan error. Filter
bernilai banyak adalah OR di dalam satu dimensi dan AND antar dimensi.

```json
{
  "data": [
    {
      "id": 41,
      "title": "Backend Engineer",
      "company_name": "Northwind",
      "company_slug": "northwind",
      "location": "Jakarta",
      "employment_type": "full-time",
      "skills": ["go", "postgresql"],
      "skills_source": "declared",
      "salary_min": 12000000,
      "salary_max": 18000000,
      "salary_currency": "IDR",
      "salary_period": "month",
      "source": "kalibrr",
      "source_url": "https://www.kalibrr.com/...",
      "posted_at": "2026-11-20T00:00:00+00:00",
      "is_saved": false
    }
  ],
  "meta": { "page": 1, "per_page": 12, "total": 363, "has_next": true }
}
```

`skills_source` bernilai `declared` bila sumber menyatakannya sendiri dan
`inferred` bila hasil kamus dari judul/deskripsi. `experience_level` selalu
`null`: kolomnya tidak ada di skema, dan menebaknya dari judul akan mengarang.

### `GET /api/jobs/<id>`

Detail satu lowongan. `404` berformat galat standar bila ID tidak ada.

### `GET /api/companies/<slug>`

Ringkasan perusahaan yang **hanya** diturunkan dari tabel `jobs`. Tidak ada
tabel perusahaan, jadi perusahaan tanpa lowongan tidak dapat muncul — dan itu
batas yang benar, bukan kekurangan.

```json
{
  "data": {
    "name": "Northwind",
    "slug": "northwind",
    "job_count": 4,
    "locations": ["Jakarta"],
    "employment_types": ["full-time"],
    "top_skills": ["python", "sql"],
    "jobs": []
  }
}
```

### `GET /api/insights/categories`

Distribusi lowongan per cluster hasil clustering.

```json
{ "data": [ { "id": 1, "label": "Data & Ai", "keywords": ["data", "python"], "job_count": 101 } ] }
```

### `GET /api/insights/skills`

Skill paling banyak diminta, terurut menurun.

```json
{ "data": [ { "skill": "python", "count": 78 } ] }
```

### `GET /api/insights/salary`

Statistik gaji **faktual** — median, P25, P75 dari titik tengah rentang.

```json
{
  "data": {
    "sample_sufficient": true,
    "minimum_sample": 5,
    "groups": [
      { "currency": "IDR", "period": "month", "median": 12000000,
        "p25": 9000000, "p75": 16000000, "sample": 28 }
    ]
  }
}
```

**Aturan yang tidak boleh dilanggar pemanggil:**

- Kelompok dengan **kurang dari 5 sampel tidak muncul sama sekali**
  (`sample_sufficient` menjadi `false` bila tidak ada satu pun yang lolos).
  Ini berlaku di web dan API; API tidak memberi jalan pintas (R-10-13).
- Mata uang dan periode tidak dicampur. `period` `null` berarti sumber tidak
  menyebutnya — bukan "bulanan".
- Tidak ada field prediksi. Angka yang tidak dimiliki data tidak dikarang.

---

## 4. Endpoint pengguna

Memerlukan sesi login. Tanpa sesi: **401** dengan `code: UNAUTHORIZED`.

### `GET /api/recommendations`

Rekomendasi dari skill yang sudah dikonfirmasi pengguna. Skor dihitung
deterministik, tanpa AI.

```json
{ "data": [ { "id": 41, "title": "Backend Engineer", "match": 0.82, "skills": ["go"] } ] }
```

### `GET /api/saved-jobs`

Bookmark milik pengguna, terbaru disimpan lebih dulu. Mendukung `page` dan
`per_page`.

### `POST /api/saved-jobs`

Menyimpan lowongan. **Idempoten**: menyimpan dua kali tidak menambah baris.

```http
POST /api/saved-jobs
Content-Type: application/json
X-CSRFToken: <token dari meta name="csrf-token">

{ "job_id": 41 }
```

| Status | Arti |
|---|---|
| 201 | Baru disimpan |
| 200 | Sudah tersimpan sebelumnya |
| 400 | `job_id` bukan angka |
| 404 | Lowongan tidak ada |

**CSRF wajib.** Endpoint ini mengubah data, jadi `CSRFProtect` menolak
permintaan tanpa header `X-CSRFToken`. Token diambil dari
`<meta name="csrf-token">` pada halaman mana pun.

### `DELETE /api/saved-jobs/<job_id>`

Menghapus bookmark milik sendiri. Header `X-CSRFToken` juga wajib. Menghapus
bookmark yang tidak ada tetap `200` — hasil akhirnya sama.

### `POST /api/cv/extract`

Ekstraksi skill dari berkas CV. Berkas **tidak disimpan**: ditulis ke berkas
sementara lalu dihapus di blok `finally` (R-10-12).

```http
POST /api/cv/extract
Content-Type: multipart/form-data
X-CSRFToken: <token>

file: <cv.pdf atau cv.docx>
```

```json
{
  "data": {
    "skills": ["python", "docker", "kubernetes"],
    "ambiguous": [{ "text": "terraform", "reason": "tidak ada di kamus" }]
  }
}
```

Kandidat `ambiguous` dikembalikan untuk **diputuskan pengguna**, bukan dikirim
ke layanan luar. Ekstraksi memakai kamus 105 skill + 80 alias, bukan LLM.

PDF hasil pindai tidak punya lapisan teks; jawabannya `400` dengan saran
mengunggah DOCX, bukan teks kosong.

### `POST /api/assistant`

Pertanyaan bahasa alami, dijawab dari data aplikasi oleh DeepSeek.

```http
POST /api/assistant
Content-Type: application/json
X-CSRFToken: <token>

{ "message": "lowongan data analyst apa saja?" }
```

```json
{
  "data": {
    "reply": "Ada 12 lowongan data analyst, terbanyak di kategori Data & Ai.",
    "sources": [ { "label": "Data Analyst — Northwind", "url": "https://..." } ]
  }
}
```

- `sources` **selalu** dari database, bukan dari teks model — model dapat
  mengarang URL (R-08-06).
- Batas `AI_DAILY_LIMIT` pertanyaan per pengguna per hari (`429` bila habis).
  Pertanyaan yang dijawab dengan klarifikasi **tidak** memotong kuota.
- Bila konteks tidak memuat jawaban, asisten menolak dengan jujur alih-alih
  mengarang.

---

## 5. Panel admin (HTML, bukan API)

Tidak ada endpoint admin di API publik. Halaman `/admin*` mengembalikan HTML
dan hanya untuk `users.role = 'admin'`:

| Route | Isi |
|---|---|
| `GET /admin` | Ringkasan dan lima proses terakhir |
| `GET /admin/jobs` | Daftar lowongan, pencarian, pagination |
| `POST /admin/jobs/<id>/delete` | Hapus lowongan (butuh `X-CSRFToken`) |
| `GET /admin/users` | Daftar pengguna; tanpa password, tanpa skill |
| `GET /admin/runs` | Riwayat `scrape_runs` |
| `GET /admin/clusters` | Tinjauan cluster |

Tamu → `302` ke login. Pengguna biasa → `403`. Panel admin tidak pernah
menampilkan berkas atau teks CV (R-09-09).

---

## 6. Contoh pemakaian

```bash
# Daftar lowongan berbahasa manusia
curl "https://karir-lens.onrender.com/api/jobs?q=backend&per_page=5"

# Insight gaji
curl "https://karir-lens.onrender.com/api/insights/salary"

# Endpoint pengguna: sertakan cookie sesi
curl -b cookies.txt "https://karir-lens.onrender.com/api/saved-jobs"

# Tanpa sesi: 401, bukan pengalihan
curl -i "https://karir-lens.onrender.com/api/saved-jobs"
```

---

## 7. Yang tidak disediakan

Sengaja tidak ada, dan bukan karena belum dikerjakan:

- **Tracker lamaran atau status lamaran.** KarirLens mengumpulkan lowongan,
  bukan mengelola proses melamar.
- **Endpoint admin di API publik.**
- **Penyimpanan berkas atau teks CV.** Yang tersimpan hanya nama skill yang
  dikonfirmasi pengguna.
- **Prediksi gaji.** Statistik hanya dari data faktual.
