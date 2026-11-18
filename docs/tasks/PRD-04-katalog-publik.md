# PRD-04 — Katalog Publik

| Field | Keterangan |
|---|---|
| ID task | PRD-04 |
| Nama task | Katalog Publik |
| Prioritas | P0 |
| Milestone | M3 Katalog publik (2 hari) |
| Dependensi | PRD-01, PRD-03 |
| Task yang bergantung | PRD-05, PRD-06, PRD-07, PRD-09 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |

---

## 1. Konteks

Setelah data lowongan bersih dan konsisten (PRD-03), pengguna membutuhkan antarmuka publik untuk menemukan lowongan. Task ini membangun beranda, daftar lowongan dengan pencarian, filter, pengurutan, dan pagination, serta halaman detail lowongan. Halaman perusahaan dan insight dibangun pada PRD-05.

Halaman publik tidak memerlukan akun. Semua route pada task ini adalah publik, dan logika query-nya dipakai ulang oleh REST API pada PRD-09.

## 2. Tujuan

1. Menyediakan beranda yang menjelaskan produk dan menampilkan lowongan terbaru serta kategori.
2. Menyediakan pencarian berdasarkan posisi, perusahaan, atau skill.
3. Menyediakan filter kota, tipe kerja, dan sumber.
4. Menyediakan halaman detail lowongan dengan tautan sumber asli.
5. Menjaga performa: halaman publik di bawah 2 detik, pencarian di bawah 1,5 detik untuk ~5.000 lowongan.

## 3. Scope

### 3.1 Termasuk

- Route `/` (beranda): hero, ringkasan jumlah lowongan, lowongan terbaru, pintasan kategori.
- Route `/jobs`: daftar lowongan dengan pencarian, filter, pengurutan, dan pagination.
- Route `/jobs/<id>`: detail lowongan, skill, gaji bila ada, sumber, tautan asli, lowongan serupa.
- Komponen UI: kartu lowongan, chip skill, badge tipe kerja, badge sumber, indikator gaji.
- Kondisi kosong, loading, dan error yang jelas.
- Service layer query yang dipakai ulang oleh API.

### 3.2 Tidak termasuk

- Halaman perusahaan (dibangun di PRD-05).
- Clustering, insight kategori, skill populer, dan statistik gaji (PRD-05).
- Bookmark dan halaman tersimpan (PRD-06).
- Asisten AI, admin, dan REST API (PRD-08, PRD-09).
- Profil resmi perusahaan dari situs eksternal.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-04-01 | `/jobs` mendukung query `q` untuk mencari posisi, perusahaan, atau skill. | P0 |
| R-04-02 | `/jobs` mendukung filter `city`, `employment_type`, dan `source`. Filter dapat dikombinasikan dengan pencarian. | P0 |
| R-04-03 | `/jobs` mendukung pengurutan `sort=posted_desc` (default), `posted_asc`, dan `relevance` saat `q` tersedia. | P0 |
| R-04-04 | `/jobs` memakai pagination server-side (mis. 12-20 item per halaman) dengan metadata `page`, `per_page`, `total`, `has_next`. | P0 |
| R-04-05 | Query database memakai parameter terikat; pencarian memakai pencarian teks yang aman (bukan string mentah). | P0 |
| R-04-06 | Kondisi kosong menampilkan pesan jelas dan saran menghapus filter. | P0 |
| R-04-07 | `/jobs/<id>` menampilkan judul, perusahaan, lokasi, tipe kerja, deskripsi, skill, gaji bila tersedia, sumber, tanggal, dan tautan ke lowongan asli. | P0 |
| R-04-08 | `/jobs/<id>` menampilkan atribusi sumber (termasuk Remotive) dan tautan asli yang valid. | P0 |
| R-04-09 | `/jobs/<id>` menampilkan lowongan serupa berdasarkan skill yang sama (maksimum 5-6 item). | P1 |
| R-04-10 | Halaman publik menampilkan pesan yang ramah saat data gagal dimuat. | P0 |
| R-04-11 | Layout responsif mulai 360 px, navigasi keyboard-friendly, label form jelas, dan kontras memenuhi keterbacaan dasar. | P0 |
| R-04-12 | `/` menampilkan jumlah lowongan terkini dan lowongan terbaru tanpa query berat. | P0 |
| R-04-13 | Semua halaman publik dapat diakses tanpa login. | P0 |
| R-04-14 | State pencarian/filter tersimpan di URL agar dapat dibagikan dan di-refresh. | P1 |

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
- [ ] Pagination menampilkan metadata benar dan navigasi berfungsi.
- [ ] Kondisi kosong menampilkan pesan jelas.
- [ ] Setiap lowongan yang tampil memiliki tautan sumber asli yang valid.
- [ ] Tidak ada halaman tracker lamaran atau status lamaran.
- [ ] Halaman publik diakses tanpa login.
- [ ] Tampilan rapi pada 360 px, 768 px, dan 1280 px.
- [ ] Waktu muat halaman publik < 2 detik dan pencarian < 1,5 detik pada data uji ~5.000 baris.

## 6. Dependensi

- PRD-01 (layout, blueprint).
- PRD-03 (data ternormalisasi, `company_slug`, `dedup_hash`).
- Data uji minimal untuk verifikasi pagination dan pencarian.
- Pustaka: Bootstrap, JavaScript dasar.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_jobs_default_list` | Halaman pertama mengembalikan item dan metadata benar. |
| `test_jobs_search_title` | `q` menemukan lowongan berdasarkan judul. |
| `test_jobs_search_company_and_skill` | `q` menemukan berdasarkan perusahaan dan skill. |
| `test_jobs_filter_combined` | Kombinasi `city`, `employment_type`, `source` bekerja. |
| `test_jobs_sort` | Urutan `posted_desc` dan `posted_asc` benar. |
| `test_jobs_pagination` | `page`/`per_page` dan `has_next` benar. |
| `test_jobs_empty_state` | Hasil kosong merender pesan kosong. |
| `test_job_detail_source_link` | Detail menampilkan `source_url` valid dan atribusi sumber. |
| `test_job_detail_not_found` | ID tidak ada menghasilkan 404 ramah. |
| `test_public_pages_no_auth` | Semua route publik dapat diakses tanpa login. |

### 7.2 Pengujian Manual

1. Cari "python" lalu tambahkan filter kota dan tipe kerja.
2. Refresh halaman dan pastikan state URL tetap.
3. Buka detail lowongan dari masing-masing sumber dan periksa tautan asli.
4. Uji tampilan pada 360 px, 768 px, dan 1280 px.
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
