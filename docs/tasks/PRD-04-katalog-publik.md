# PRD-04 — Katalog Publik

| Field | Keterangan |
|---|---|
| ID task | PRD-04 |
| Nama task | Katalog Publik (Backend) |
| Track | B — Backend |
| Prioritas | P0 |
| Milestone | M3 Katalog publik (2 hari) |
| Dependensi | PRD-01, PRD-03, PRD-F02 |
| Task yang bergantung | PRD-05, PRD-06, PRD-07, PRD-09 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F02](./PRD-F02-katalog-publik.md) |

---

## 1. Konteks

Tampilan katalog publik sudah dibangun pada PRD-F02, termasuk beranda, daftar lowongan, detail, halaman perusahaan, pagination, empty state, dan skeleton. Template, komponen, dan kontrol filter sudah ada dan diuji dengan data fixture.

Task ini mengisi **logika di belakang template itu**: query pencarian dan filter, pagination server-side, pengambilan detail, dan penurunan data perusahaan. Semua query hidup di `app/jobs/repository.py` dan `app/insights/repository.py`; aturan filter hidup di `service.py`; route hanya memanggil service dan merender template yang sudah ada.

Keluaran task ini wajib memenuhi **kontrak template PRD-F02 §4.1** tanpa mengubah template.

## 2. Tujuan

1. Mengganti sumber data fixture pada halaman katalog dengan query Supabase.
2. Menyediakan pencarian, filter, urutan, dan pagination server-side.
3. Menyediakan detail lowongan dan lowongan serupa.
4. Menurunkan ringkasan perusahaan dari tabel `jobs`.
5. Menyediakan service yang dipakai ulang REST API pada PRD-09.

## 3. Scope

### 3.1 Termasuk

- `app/jobs/repository.py`: query kriteria, count, detail, lowongan serupa.
- `app/jobs/service.py`: validasi filter defensif, penyusunan kriteria, metadata halaman.
- Route `main`, `jobs` yang mengisi variabel kontrak PRD-F02 §4.1.
- `app/insights/service.py` fungsi perusahaan dan repository terkait (dipakai PRD-05).
- Filter Jinja `tanggal` dan `angka`.
- Menonaktifkan route preview untuk halaman yang sudah punya backend.

### 3.2 Tidak termasuk

- Markup, CSS, dan JavaScript halaman (selesai pada PRD-F02).
- Clustering, kategori, skill populer, statistik gaji (PRD-05).
- Bookmark persisten (PRD-06).
- REST API (PRD-09).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-04-01 | `service.search_jobs` menerima `q`, `city`, `employment_type`, `source`, `sort`, `page`, `per_page` dan mengembalikan `{items, meta, filters, options}`. | P0 |
| R-04-02 | Nilai filter di luar himpunan baku direset ke default, bukan menghasilkan error. | P0 |
| R-04-03 | Pencarian `q` mencakup `title`, `company_name`, dan `skills`. | P0 |
| R-04-04 | Urutan mendukung `posted_desc` (default), `posted_asc`, dan `relevance` saat `q` ada. | P0 |
| R-04-05 | Pagination server-side memakai `core/pagination.py`, dengan `per_page` default 12 dan maksimum 50. | P0 |
| R-04-06 | `service.get_job` mengembalikan detail beserta lowongan serupa maksimum 6 berdasarkan skill yang sama. | P0 |
| R-04-07 | `service.get_company` menurunkan nama, jumlah lowongan, lokasi, tipe kerja, dan skill sering muncul dari tabel `jobs`. | P0 |
| R-04-08 | Semua query memakai parameter terikat PostgREST; tidak ada string SQL yang disusun dari input pengguna. | P0 |
| R-04-09 | Route mengembalikan 404 lewat `AppError` bila lowongan atau perusahaan tidak ada, sehingga halaman error PRD-01 dipakai. | P0 |
| R-04-10 | Halaman katalog tetap dapat diakses tanpa login. | P0 |
| R-04-11 | Keluaran service memenuhi kontrak template PRD-F02 §4.1 tanpa perubahan template. | P0 |
| R-04-12 | Filter `tanggal` dan `angka` tersedia untuk seluruh template. | P1 |
| R-04-13 | Target performa: daftar < 1,5 detik untuk ~5.000 lowongan. | P0 |

### 4.1 Kontrak yang Harus Dipenuhi

Bentuk data pada [PRD-F02 §4.1](./PRD-F02-katalog-publik.md) adalah spesifikasi. Repository boleh mengambil kolom berbeda, tetapi service wajib mengembalikan `dict` dengan kunci dan tipe yang sama.

| Fungsi service | Mengisi variabel template |
|---|---|
| `search_jobs(...)` | `items`, `meta`, `filters`, `options` |
| `get_job(job_id)` | `job`, `similar` |
| `get_company(slug)` | `company` |
| `get_home()` | `stats`, `latest`, `categories` (bagian kategori diisi PRD-05) |

### 4.1 Parameter Query `/jobs`

| Parameter | Nilai | Default |
|---|---|---|
| `q` | Teks bebas (posisi, perusahaan, skill) | kosong |
| `city` | Nama kota dari data | semua |
| `employment_type` | `full-time`, `part-time`, `contract`, `internship`, `freelance` | semua |
| `source` | `dealls`, `kalibrr`, `remotive` | semua |
| `sort` | `posted_desc`, `posted_asc`, `relevance` | `posted_desc` |
| `page` | Integer ≥ 1 | `1` |
| `per_page` | Integer 1-50 | `12` |

### 4.2 Struktur Hasil Query

```json
{
  "items": [ { "id": 1, "title": "...", "company_name": "...", "company_slug": "...", "location": "...", "employment_type": "full-time", "skills": ["python"], "salary_min": null, "salary_max": null, "source": "dealls", "source_url": "...", "posted_at": "..." } ],
  "meta": { "page": 1, "per_page": 12, "total": 120, "has_next": true }
}
```

## 5. Acceptance Criteria

- [ ] Pencarian posisi, perusahaan, dan skill mengembalikan hasil relevan.
- [ ] Kombinasi filter kota, tipe kerja, dan sumber bekerja tanpa error.
- [ ] Nilai filter di luar himpunan direset ke default, tidak menghasilkan error.
- [ ] Pagination mengembalikan metadata yang benar dan sesuai `core/pagination.py`.
- [ ] Halaman katalog diakses tanpa login.
- [ ] Setiap lowongan yang tampil memiliki tautan sumber asli yang valid.
- [ ] Lowongan atau perusahaan yang tidak ada menghasilkan 404 lewat `AppError`.
- [ ] Service mengembalikan `dict` sesuai kontrak PRD-F02 §4.1 tanpa mengubah template.
- [ ] Waktu muat daftar < 1,5 detik pada data uji ~5.000 baris.
- [ ] Tidak ada template, CSS, atau komponen baru yang ditambahkan pada task ini.

## 6. Dependensi

- PRD-01 (layout, blueprint, `core/pagination.py`, `core/errors.py`).
- PRD-03 (data ternormalisasi, `company_slug`, `dedup_hash`).
- PRD-F02 (template, komponen, dan kontrak data).
- Data uji minimal untuk verifikasi pagination dan pencarian.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_jobs_default_list` | Halaman pertama mengembalikan item dan metadata benar. |
| `test_jobs_search_title` | `q` menemukan lowongan berdasarkan judul. |
| `test_jobs_search_company_and_skill` | `q` menemukan berdasarkan perusahaan dan skill. |
| `test_jobs_filter_combined` | Kombinasi `city`, `employment_type`, `source` bekerja. |
| `test_jobs_filter_invalid_reset` | Nilai filter di luar himpunan direset ke default. |
| `test_jobs_sort` | Urutan `posted_desc` dan `posted_asc` benar. |
| `test_jobs_pagination_meta` | `page`/`per_page`/`has_next` sesuai `build_meta`. |
| `test_job_detail_not_found` | ID tidak ada menghasilkan `NotFoundError`. |
| `test_company_derived_from_jobs` | Ringkasan perusahaan hanya dari data `jobs`. |
| `test_service_matches_template_contract` | Kunci `dict` service sama dengan kontrak PRD-F02 §4.1. |
| `test_templates_unchanged_by_backend` | Template katalog tidak diubah pada task ini. |
| `test_public_pages_no_auth` | Semua route publik dapat diakses tanpa login. |

### 7.2 Pengujian Manual

1. Cari "python" lalu tambahkan filter kota dan tipe kerja.
2. Refresh halaman dan pastikan state URL tetap.
3. Buka detail lowongan dari masing-masing sumber dan periksa tautan asli.
4. Isi URL dengan `employment_type=ngawur` dan pastikan halaman tetap normal.
5. Ukur waktu muat dengan data uji ±5.000 lowongan.

## 8. Out of Scope

- Halaman perusahaan (PRD-05) beserta insight kategori, skill, dan gaji.
- Bookmark, profil, CV, rekomendasi, dan asisten AI.
- Panel admin dan REST API (logika query dipakai ulang di PRD-09).
- Profil resmi perusahaan, logo, rating, atau ulasan.

## 9. Catatan Teknis

- Pisahkan query ke `app/jobs/service.py` agar dapat dipakai API pada PRD-09.
- Gunakan index `jobs.posted_at`, `jobs.company_slug`, dan pencarian teks untuk performa.
- Tambahkan cache ringan hanya bila perlu; default tanpa cache.
- Pagination wajib server-side; jangan memuat seluruh data ke browser.
- Semua teks antarmuka berbahasa Indonesia.

## 10. Referensi Proyek

Proyek utama: **Bot Rekap Lowongan Dealls** (`D:\Semester 5\Praktik Scripting\Pertemuan 9`), khusus `app.py` — dashboard Flask-nya sudah menyelesaikan pencarian, filter, pagination, dan JSON API di atas data lowongan.

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `app.py` — `_lowongan(kata, status, halaman)` | Pembentukan klausa dinamis dengan daftar `syarat` dan `parameter`: `WHERE {' AND '.join(syarat)}`, pencarian `LIKE` pada judul/perusahaan/skill. Acuan langsung R-04-01, R-04-02, dan R-04-05. |
| `app.py` — blok pagination | `PER_HALAMAN = 25`, hitung `total` lewat `COUNT(*)`, `offset = (halaman - 1) * PER_HALAMAN`, dan kembalikan `total_halaman` serta `per_halaman`. Acuan R-04-04 dan struktur `meta` pada §4.2. |
| `app.py` — `@app.route("/")`, `beranda()` | Validasi query string secara defensif: `status` di luar himpunan direset ke default, `halaman` yang bukan angka dijatuhkan ke 1. Acuan R-04-03 dan R-04-13. |
| `app.py` — `detail_lowongan(slug)` | Pola `fetch_one` lalu `abort(404)` bila baris kosong, disertai `templates/detail.html`. Acuan R-04-07 dan R-04-09. |
| `app.py` — `api_lowongan()`, `api_statistik()` | Endpoint JSON yang memakai fungsi Python yang sama dengan halaman HTML, bukan query terpisah. Ini acuan R-04-14 dan persiapan pemakaian ulang di PRD-09. |
| `app.py` — `@app.template_filter("tanggal")`, `@app.template_filter("angka")` | Filter Jinja untuk format tanggal Indonesia (`%d %b %Y, %H:%M`) dan pemisah ribuan gaya Indonesia (`12.345`). Acuan R-04-11 dan konsistensi Bahasa Indonesia. |
| `app.py` — `@app.context_processor` | Variabel umum (nama aplikasi, waktu dibuat) diinjeksi sekali untuk semua template, bukan diulang per route. |
| `templates/index.html`, `templates/detail.html`, `static/style.css` | Struktur halaman daftar dan detail: kartu lowongan, chip skill, badge status, tabel berhalaman, plus CSS tanpa dependensi. Acuan R-04-07 dan R-04-11. |
| `tests/test_web.py` | Fixture `klien(tmp_path, monkeypatch)` yang menyiapkan database sementara berisi 30 lowongan lalu memakai `app.test_client()`. Pola ini langsung dipakai untuk test plan §7.1. |

**Cara mengadaptasi ke KarirLens**

1. Ambil `_lowongan()` dan pecah menjadi `app/jobs/service.py` agar dipakai ulang oleh halaman dan `/api/jobs`.
2. Pertahankan pola validasi query string yang defensif sebelum menyusun klausa filter.
3. Pakai filter `tanggal` dan `angka` untuk konsistensi format Indonesia di seluruh halaman.
4. Karena database KarirLens adalah Supabase, klausa `WHERE` dipindahkan ke PostgREST filter atau `text()` berparameter, bukan disusun sebagai string SQL mentah. Pencarian teks memakai `ilike`/full-text search, bukan `LIKE` manual.

**Yang tidak diambil**

- Status aktif/nonaktif lowongan (`is_active`) sebagai filter. Tidak ada di skema KarirLens.
- Kolom `slug` sebagai kunci URL; KarirLens memakai `id` numerik untuk `/jobs/<id>` dan `company_slug` untuk `/companies/<slug>`.
- Ekspor CSV/XLSX/DOCX dan grafik matplotlib. Tidak termasuk scope P0 katalog; grafik KarirLens memakai Chart.js di PRD-05.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Halaman publik berfungsi tanpa login.
- Performa target terpenuhi pada data uji.
