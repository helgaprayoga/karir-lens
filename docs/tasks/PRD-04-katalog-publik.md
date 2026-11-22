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
| Status | Selesai (terbukti di Supabase) |
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

- [x] Pencarian posisi, perusahaan, dan skill mengembalikan hasil relevan.
- [x] Kombinasi filter kota, tipe kerja, dan sumber bekerja tanpa error.
- [x] Nilai filter di luar himpunan direset ke default, tidak menghasilkan error.
- [x] Pagination mengembalikan metadata yang benar dan sesuai `core/pagination.py`.
- [x] Halaman katalog diakses tanpa login.
- [x] Setiap lowongan yang tampil memiliki tautan sumber asli yang valid.
- [x] Lowongan atau perusahaan yang tidak ada menghasilkan 404 lewat `AppError`.
- [x] Service mengembalikan `dict` sesuai kontrak PRD-F02 §4.1 tanpa mengubah template.
- [x] Waktu muat daftar < 1,5 detik (254 ms rata-rata; lihat §12.4).
- [x] Tidak ada template, CSS, atau komponen baru yang ditambahkan pada task ini.

Bukti terukur ada di §12.4.

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

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `app/jobs/repository.py` | Query PostgREST: pencarian, filter, urutan, pagination, detail, serupa, angka beranda |
| `app/jobs/service.py` | Validasi filter defensif, skor relevansi, metadata halaman |
| `app/jobs/routes.py` | `/jobs`, `/jobs/<id>` |
| `app/insights/repository.py` | `find_jobs_by_company`, `find_sources` |
| `app/insights/service.py` | `get_company` — ringkasan turunan dari `jobs` |
| `app/insights/routes.py` | `/companies/<slug>` |
| `app/main/routes.py` | `/` dengan angka sungguhan |
| `app/templating.py` | Penerjemah nama endpoint pratinjau → produksi |
| `templates/main/index.html` | Beranda produksi (menggantikan kerangka PRD-01) |
| `tests/conftest.py` | Klien database kosong untuk seluruh test |
| `tests/unit/test_catalog_backend.py` | 33 test PRD-04 §7.1 |

### 12.2 Konflik yang Harus Diselesaikan Dulu

Template katalog ditulis pada PRD-F02 dan menautkan **endpoint pratinjau**:

```
url_for('preview.jobs')            # 8 tempat
url_for('preview.job_detail', ...)
url_for('preview.company_detail', ...)
```

Sekaligus, R-04-11 melarang mengubah template, dan §3.1 meminta route
pratinjau dinonaktifkan untuk halaman yang sudah punya backend. Ketiga aturan
itu tidak dapat dipenuhi sekaligus tanpa perantara: begitu `PREVIEW_UI=false`,
`url_for('preview.jobs')` melempar `BuildError` dan setiap halaman katalog 500.

Solusinya `app/templating.py`: satu penerjemah di globals Jinja yang memilih
endpoint menurut **halaman yang sedang dirender**, bukan menurut flag. Halaman
pratinjau tetap menaut ke `/preview/...`; halaman produksi menaut ke `/jobs`,
`/jobs/<id>`, `/companies/<slug>`. Template tidak berubah satu baris pun.
Endpoint yang tidak punya padanan produksi (profil, CV, asisten, admin) sengaja
tidak dipetakan agar salah ketik tetap terlihat, bukan diam-diam menjadi URL
salah.

### 12.3 Bug yang Ditemukan Verifikasi

**`/jobs` mengembalikan 308.** Blueprint memakai `url_prefix="/jobs"` dengan
route `"/"`, sehingga URL kanoniknya `/jobs/` dan `/jobs` — tautan yang dipakai
navigasi — dialihkan permanen. Dua aturan dipasang pada fungsi yang sama:
`""` dan `"/"`.

**`insights/service.py` mengimpor `app.jobs.repository`.** Itu melanggar
`docs/ARCHITECTURE.md` §4 butir 2 (service hanya boleh memakai repository
modulnya sendiri), dan test arsitektur menangkapnya. Query sumber dipindahkan
ke `insights/repository.find_sources`.

**`sanitize_term` menyisakan spasi ganda.** `a,b(c)` menjadi `a b c  d` alih-alih
`a b c d`; saat disisipkan ke `ilike`, spasi ganda menjadi dua token kosong.

**Tiga query terbuang di setiap halaman daftar.** `search_jobs` mengambil tabel
`sources` tiga kali (`find_page`, `count`, `_options`), dan route memanggil
`get_home()` yang mengambil statistik, lowongan terbaru, dan sparkline — tidak
satu pun dipakai `jobs/list.html`. Peta sumber kini diambil sekali dan
diteruskan; `get_home()` dihapus dari route daftar.

**Chip kota diurutkan alfabetis.** Pada data nyata, sepuluh chip pertama berisi
"Aceh Besar", "Ambon", "Badung" — masing-masing satu lowongan — sementara
"Jakarta Barat" (4 lowongan) tidak muncul. Urutannya kini menurut jumlah
lowongan, lalu abjad.

**Halaman katalog meluber pada 360px.** Terukur di browser dengan data asli:
`scrollWidth` 589px pada viewport 360px, sedangkan fixture PRD-F02 hanya
menghasilkan 360px. Penyebabnya `.cards { grid-template-columns: 1fr }` —
`1fr` berarti `minmax(auto, 1fr)`, dan `auto` melarang track lebih kecil dari
min-content anaknya. Satu judul panjang ("Host Live & Content Creator Gaming -
No Limit Gear") karena itu melebarkan seluruh kartu. Diganti
`minmax(0, 1fr)`; kini 360/360, 768/768, 1024/1024, 1280/1280.


### 12.4 Verifikasi Terukur

Terhadap Supabase sungguhan, 50 baris, lewat test client:

| Halaman | Waktu |
|---|---|
| `/` | 544 ms |
| `/jobs` | 424 ms |
| `/jobs?q=engineer` | 286 ms |
| `/jobs` rata-rata 10 permintaan | **254 ms** |

Sebelum perbaikan query, `/jobs` memakan **811 ms** dan rata-rata **628 ms** —
3,2× lebih lambat karena empat perjalanan jaringan yang tidak perlu. Keduanya
jauh di bawah target 1,5 detik (R-04-13). Catatan jujur: angka ini diukur pada
50 baris, bukan 5.000 seperti yang diminta R-04-13; yang menentukan waktu di
sini adalah jumlah round-trip ke Supabase, bukan jumlah baris, karena
pagination berjalan di server.

Fungsional, pada data nyata:

| Pemeriksaan | Hasil |
|---|---|
| `/jobs` | 200, 12 kartu, 16 chip filter, pagination, "49 Lowongan" |
| `?q=excel` | 1 hasil — cocok lewat `skills`, bukan judul |
| `?q=communication` | 2 hasil, keduanya Host Live |
| `?city=Bandung` | 2 hasil |
| `?employment_type=ngawur&sort=acak&page=abc` | 200, halaman normal |
| `/jobs/380` | 200, deskripsi, gaji, tautan `dealls.com` asli |
| `/companies/akulaku-group` | 200, "1 lowongan tersedia", lokasi, kartu |
| `/jobs/999999`, `/companies/tidak-ada` | 404 lewat `AppError` |
| Lowongan serupa | 393 ↔ 385 berbagi `communication` + `host live streaming` |

**Yang belum terbukti.** Pada run tanpa `--detail`, seluruh 49 lowongan punya
`skills: []` dan halaman perusahaan menampilkan nol skill. Itu bukan bug: skill
hanya terisi dari halaman detail. Setelah `--detail`, 17 lowongan berskill dan
kedua fitur itu bekerja seperti di tabel atas.

**Diperiksa di browser sungguhan** (server Flask, data Supabase): `/jobs`
menampilkan 50 lowongan dalam 12 kartu dengan pagination "1–12 dari 50"; chip
kota kini dipimpin "Worldwide" (7), "South Jakarta" (5), "Jakarta Barat" (4);
`/jobs/393` menampilkan gaji, tujuh chip skill, deskripsi, dan panel perusahaan;
`/companies/akulaku-group` menampilkan angka turunan dan kartu lowongannya.
Tidak ada luberan horizontal pada 360, 768, 1024, dan 1280 px.

Total test setelah task ini: **384 lulus**.

---

## 13. Lanjutan: Pemfokusan ke IT, Filter Banyak Nilai, Panel Filter

Perubahan yang diminta setelah PRD-04 selesai. Tiga bagian, semuanya terukur
terhadap data sungguhan.

### 13.1 Hanya lowongan IT

Tiga sumber ini memuat semua jenis pekerjaan. Pengambilan penuh membuktikan
seberapa besar masalahnya:

| Sumber | Diambil | IT | Disaring |
|---|---|---|---|
| dealls | 900 | 40 | 860 |
| kalibrr | 26 | 6 | 20 |
| remotive | 171 | 70 | 101 |
| **total** | **1097** | **116** | **981** |

**90% hasil adalah non-IT.** Katalog yang berisi "Head Chef", "Host Live", dan
"Community Officer" bukan katalog karir teknologi.

Klasifikasi ada di `core/tech.py` (`is_it_job`), murni dan diuji terhadap judul
nyata. Urutan buktinya: kategori sumber → judul → skill. Dealls tidak punya
kategori andal, jadi judul jadi satu-satunya sinyal.

Pencocokan judul memakai **batas kata**, bukan substring. Tanpa itu `"it
staff"` cocok di dalam **"audit staff"** dan "Tax & Audit Staff" masuk sebagai
lowongan IT — bug ini nyata, ditemukan saat menguji pada data.

Penyaringan terjadi **sebelum** halaman detail diambil, sehingga lowongan
non-IT tidak memakan satu pun permintaan tambahan.

### 13.2 Mengambil Semua, Bukan Hanya yang Terbaru

`--pages 0` (kini bawaan) mengambil sampai daftar habis. Kemampuan sebenarnya
tiap sumber, diuji langsung:

| Sumber | Paginasi | Batas nyata |
|---|---|---|
| Dealls | `?page=N` | 134 halaman, 900 lowongan |
| Kalibrr | **"Load more" → endpoint `kjs`** | 253 lowongan IT dari 2290 — lihat §14 |
| Remotive | tidak ada `?page=` | halaman **kategori**; 8 kategori IT, 171 lowongan |

> Catatan: versi pertama bagian ini menyebut Kalibrr "dibatasi 26 lowongan".
> Itu salah — kesimpulannya diambil dari menebak parameter URL, bukan dari
> mengamati halaman. Koreksi lengkapnya ada di §14.

Remotive `?page=2` mengembalikan halaman yang **identik** dengan halaman 1 —
sudah diuji, bukan diasumsikan. Karena itu yang diambil adalah seluruh kategori
IT-nya.

### 13.3 Mengganti Data Lama dengan Aman

`--replace` menghapus baris yang `source_url`-nya tidak muncul pada pengambilan
terbaru. Urutannya **ambil dulu, hapus kemudian**:

1. Bila pengambilan gagal, data lama utuh.
2. Bila sebuah sumber gagal, lowongannya tidak ikut dihapus — tidak ada dasar
   menyatakan lowongan itu sudah tidak ada.
3. Himpunan URL kosong berarti **tidak menghapus apa pun**.
4. Yang dihapus hanya baris yang benar-benar hilang, bukan mengosongkan tabel
   lalu memasukkannya kembali — `saved_jobs` menunjuk ke `jobs.id`, dan
   menghapus lalu memasukkan ulang akan memutus bookmark pengguna.

Hasil: 1097 diambil, 116 disimpan, **42 baris lama dihapus** (yang non-IT dan
yang sudah tidak tersedia). Sesudah `--detail`: deskripsi 116/116, skill
109/116, `posted_at` 116/116.

### 13.4 Filter Banyak Nilai

Sebelumnya `?city=A` hanya bisa satu kota. Sekarang `city`, `employment_type`,
dan `source` menerima banyak nilai, dengan tiga bentuk masukan yang setara:

| Bentuk | Contoh |
|---|---|
| Koma | `?city=Bandung,Jakarta` |
| Berulang | `?city=Bandung&city=Jakarta` |
| List Python | `service.search_jobs(city=["Bandung", "Jakarta"])` |

Semantiknya: **OR di dalam satu dimensi, AND antar dimensi**. Memilih dua kota
dan satu tipe kerja berarti "(Bandung atau Jakarta) DAN full-time" — bukan
"Bandung DAN Jakarta", yang tidak mungkin terpenuhi.

Diukur di browser pada data nyata:

| URL | Hasil |
|---|---|
| `/jobs` | 116 |
| `?employment_type=full-time,contract` | 105 |
| `?city=Jakarta Selatan,Jakarta Pusat` | 17 |
| keduanya sekaligus | 16 |

Tautan chip men-toggle **satu** nilai, jadi menghapus "Bandung" tidak
menghapus "Jakarta" yang dipilih bersamanya.

### 13.5 Panel Filter Sungguhan

Tombol "Filter" sebelumnya dekorasi: `aria-controls="filter-panel"` menunjuk
elemen yang tidak ada, dan tidak terjadi apa pun saat diklik.

Sekarang panel itu ada, berisi opsi dari database — 10 kota dari kolom
`location` yang terisi, 5 tipe kerja, dan 3 sumber dari tabel `sources`. Urutan
ikut di dalam form yang sama agar hanya ada **satu** tombol "Terapkan".

Chip di luar panel kini hanya menampilkan filter yang **sedang aktif**; tanpa
itu, 28 kota mendorong hasil ke bawah layar. Panel terbuka otomatis bila ada
filter aktif, `Esc` menutupnya dan mengembalikan fokus ke tombol, dan
`aria-expanded` selalu sinkron.

Diperiksa di browser: centang dua kota + satu tipe kerja menghasilkan
`?city=USA&city=Jakarta+Selatan&employment_type=full-time`, 35 lowongan, 3 chip
aktif. Pada 360px panel menjadi satu kolom tanpa luberan (`scrollWidth` 360).

Total test setelah lanjutan ini: **439 lulus**.

---

## 14. Koreksi: Kalibrr Memakai "Load more", Bukan Paginasi

Catatan §13.2 menyatakan "Kalibrr dibatasi 26 lowongan". **Itu kesimpulan yang
salah**, dan penyebabnya cara saya memeriksa: hanya menebak parameter URL
(`?page=`, `?offset=`, `?limit=`) tanpa melihat apa yang sebenarnya dilakukan
halaman.

### Cara yang benar: rekam panggilan jaringan

Dengan browser diarahkan ke `/job-board`, saya membungkus `fetch` dan
`XMLHttpRequest`, lalu menekan tombol **"Load more jobs"**. Hasilnya:

```
XHR GET https://www.kalibrr.com/kjs/job_board/search?limit=15&offset=15
XHR GET https://www.kalibrr.com/kjs/job_board/featured_jobs?limit=18&offset=15
```

Halaman itu memuat 15 lowongan; sisanya datang dari **endpoint JSON `kjs`**.
`?page=` pada HTML memang diterima sebagian, tetapi jumlah yang dapat
dijangkau tetap 26 — bukan karena server membatasi, melainkan karena HTML-nya
hanya memuat sekian banyak.

### Playwright tidak diperlukan

Tombol "Load more" hanyalah pemicu satu permintaan HTTP biasa. Menjalankan
browser penuh untuk itu menambah dependensi (unduhan Chromium ±150 MB),
memperlambat setiap eksekusi, dan menyulitkan pengujian. Yang dibutuhkan hanya
memanggil URL yang sama.

`robots.txt` Kalibrr memeriksa hal ini lebih dulu:

```
User-agent: *
Disallow: /root
Disallow: /candidate/profile
```

`/kjs/` tidak dilarang.

### Hasil

| Parameter | Hasil |
|---|---|
| `limit=100&offset=0` | 100 lowongan per permintaan |
| `function=IT+and+Software` | 2290 → **254**, seluruhnya kategori IT |
| Total diambil | **253 lowongan IT** (satu duplikat internal) |
| Waktu | 7 detik (sebelumnya 410 detik untuk 26) |

**253, bukan 26.** Peningkatannya hampir sepuluh kali lipat, dan waktunya
justru turun karena filter kategori dilakukan server.

### Perilaku server yang harus dijaga

Melewati offset 254, Kalibrr **mengabaikan filter `function`** dan mulai
mengembalikan semua kategori:

| Offset | n | Kategori |
|---|---|---|
| 200 | 54 | IT and Software |
| 300 | 100 | Accounting, Customer Service, Education, … |
| 400 | 100 | 16 kategori campur |

Tanpa penjagaan, "ambil sampai habis" akan menelan ribuan lowongan non-IT
sampai batas `MAX_PAGES_ALL` — terlihat dari hitungan "disaring" yang melonjak
dari 0 ke 1701 dan berubah antar eksekusi. `fetch()` sekarang menghentikan
pengambilan begitu isi halaman bukan lagi kategori yang diminta, dan
melaporkannya di log:

```
kalibrr: filter kategori berhenti berlaku pada offset 300; pengambilan dihentikan.
```

### Angka akhir

| Sumber | Diambil | IT | Disaring |
|---|---|---|---|
| dealls | 900 | 40 | 860 |
| kalibrr | 2290 | **253** | 0 (disaring server) |
| remotive | 171 | 65 | 105 |
| **total** | **3361** | **358** | **965** |

Katalog berisi **358 lowongan IT**, naik dari 116.

### Pelajaran

Membaca parameter URL bukan cara mengetahui cara kerja sebuah halaman.
Halaman yang memakai "Load more" tidak akan pernah menyingkap endpoint-nya lewat
tebakan — ia harus dilihat bergerak. Ini kesalahan yang sama bentuknya dengan
fixture HTML pada PRD-02: menguji tebakan, bukan kenyataan.
