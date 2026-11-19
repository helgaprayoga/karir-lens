# PRD-F02 — Katalog Publik (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F02 |
| Nama task | Katalog Publik |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01 |
| Task yang bergantung | PRD-F03, PRD-F04, PRD-F05, PRD-04 |
| Status | Selesai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Backend pasangan | [PRD-04](./PRD-04-katalog-publik.md) |
| Design system | [Design System KarirLens](../design-system.md) |

---

## 1. Konteks

Katalog publik adalah halaman yang paling banyak dilihat dan menjadi acuan bahasa visual seluruh aplikasi. Acuan visualnya adalah [`design-preview.html`](../design-preview.html), yang sudah memuat beranda daftar lowongan lengkap: header, bar pencarian, chip filter, grid kartu dua kolom, right rail, dan pagination.

Task ini membangun seluruh tampilan katalog tanpa query database. Data berasal dari `tests/fixtures/ui/jobs.json` lewat blueprint preview (PRD-F01 R-F01-09). Ketika PRD-04 dikerjakan, route produksi mengambil alih dengan kontrak template yang sama.

## 2. Tujuan

1. Membangun beranda, daftar lowongan, detail lowongan, dan halaman perusahaan.
2. Menyediakan bar pencarian, chip filter, dan kontrol urutan sesuai preview.
3. Menyediakan grid `JobCard` dua kolom dengan anatomi tetap.
4. Menyediakan right rail: hint, statistik, profil, dan insight.
5. Menyediakan pagination, empty state, dan skeleton state.
6. Menetapkan kontrak template yang harus dipenuhi PRD-04.

## 3. Scope

### 3.1 Termasuk

- `/` beranda: hero, ringkasan jumlah, lowongan terbaru, pintasan kategori.
- `/jobs`: pencarian, filter (kota, tipe kerja, sumber), urutan, pagination.
- `/jobs/<id>`: detail lengkap, skill, gaji, sumber, tautan asli, lowongan serupa.
- `/companies/<slug>`: ringkasan perusahaan dari data lowongan.
- Partial `job_card`, `filter_chip`, `sort_control`, `search_field`, `pagination`, `empty_state`, `skeleton_card`, `salary_range`.
- Right rail: `MetricCell`, `SkillPanel`, `InsightCard`, hint bar.
- State kosong, loading, dan error pada semua daftar.
- Seluruh teks berbahasa Indonesia.

### 3.2 Tidak termasuk

- Query, filter di database, pagination server-side (PRD-04).
- Statistik gaji dan clustering (PRD-05).
- Bookmark persisten (PRD-06); tombol simpan hanya menampilkan state.
- Chart.js (PRD-F05).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F02-01 | `/jobs` menampilkan bar pencarian, chip filter, kontrol urutan, dan grid kartu sesuai `design-preview.html`. | P0 |
| R-F02-02 | `JobCard` memakai anatomi tetap: perusahaan+sumber+simpan, judul, meta, deskripsi dua baris, tag skill, gaji. | P0 |
| R-F02-03 | Deskripsi kartu terpotong tepat dua baris dengan ellipsis. | P0 |
| R-F02-04 | Setiap kartu menampilkan `SourceBadge` sesuai sumber, dengan warna token yang benar. | P0 |
| R-F02-05 | Gaji tampil sebagai rentang, "Mulai", "Sampai", atau "Gaji tidak dicantumkan" bila kosong. | P0 |
| R-F02-06 | Chip filter aktif menampilkan tombol hapus dan `aria-pressed="true"`. | P0 |
| R-F02-07 | Pagination menampilkan rentang ("Menampilkan 1–6 dari 240"), tombol sebelumnya/berikutnya, dan nomor halaman. | P0 |
| R-F02-08 | Kondisi kosong memakai `EmptyState` dengan saran menghapus filter, bukan area kosong. | P0 |
| R-F02-09 | State loading memakai `SkeletonCard`, tanpa teks palsu. | P0 |
| R-F02-10 | State pencarian dan filter tercermin di URL dan bertahan saat refresh. | P1 |
| R-F02-11 | `/jobs/<id>` menampilkan detail lengkap dan tautan ke sumber asli. | P0 |
| R-F02-12 | `/jobs/<id>` menampilkan lowongan serupa (maksimum 6). | P1 |
| R-F02-13 | `/companies/<slug>` hanya menampilkan data turunan lowongan: nama, jumlah, lokasi, tipe kerja, skill sering muncul, daftar lowongan. | P0 |
| R-F02-14 | `/companies/<slug>` tidak menampilkan logo, rating, jumlah karyawan, atau alamat di luar data lowongan. | P0 |
| R-F02-15 | Right rail tampil pada ≥1180 px dan turun ke bawah konten pada layar lebih sempit. | P0 |
| R-F02-16 | Semua route katalog dapat diakses tanpa login. | P0 |
| R-F02-17 | Balasan `MatchBadge` selalu disertai alasan kecocokan, tidak pernah berdiri sendiri. | P0 |

### 4.1 Kontrak Template

**`jobs/list.html`** menerima (dari fixture pada Track A, dari PRD-04 pada Track B):

| Variabel | Tipe | Keterangan |
|---|---|---|
| `items` | `list[dict]` | Bentuk `job` pada PRD-F01 §4.2 |
| `meta` | `dict` | `{page, per_page, total, has_next}` |
| `filters` | `dict` | `{q, city, employment_type, source, sort}` — nilai aktif |
| `options` | `dict` | `{cities: list, employment_types: list, sources: list}` untuk chip |
| `is_loading` | `bool` | Opsional; memicu skeleton |

**`jobs/detail.html`** menerima `job` dan `similar` (`list[dict]`, maksimum 6).

**`companies/detail.html`** menerima `company`:

```json
{
  "name": "Northwind Data",
  "slug": "northwind-data",
  "job_count": 12,
  "locations": ["Jakarta Pusat", "Remote"],
  "employment_types": ["full-time", "contract"],
  "top_skills": ["python", "sql"],
  "jobs": []
}
```

**`main/index.html`** menerima `stats` (`{total_jobs, total_companies, total_categories}`), `latest` (`list[dict]`), dan `categories` (`list[dict]`).

## 5. Acceptance Criteria

- [x] `/jobs` tampil dengan pencarian, chip filter, urutan, grid kartu, right rail, dan pagination.
- [x] `/` menampilkan hero, ringkasan jumlah, lowongan terbaru, dan pintasan kategori.
- [x] `/jobs/<id>` menampilkan detail lengkap dan tautan sumber asli.
- [x] `/companies/<slug>` hanya menampilkan data turunan lowongan.
- [x] Setiap kartu menampilkan badge sumber yang benar.
- [x] Deskripsi terpotong tepat dua baris.
- [x] Chip filter aktif dapat dihapus dan menandai `aria-pressed`.
- [x] Kondisi kosong memakai `EmptyState` dengan saran.
- [x] Skeleton tampil pada state loading, tanpa teks palsu.
- [x] Layout tidak rusak pada 360, 768, 1024, dan 1280 px. *(diukur di browser: `scrollWidth` = viewport pada keempat lebar)*
- [x] Tepi kiri kartu sejajar dengan judul halaman dan header. *(32/32/32 · 24/24/24 · 18/18/18)*
- [x] Semua route katalog dapat dibuka tanpa login.

## 6. Dependensi

- PRD-F01 (token, komponen, shell, preview blueprint).
- `design-preview.html` sebagai acuan visual.
- Fixture `tests/fixtures/ui/jobs.json`, `companies.json`, `home.json`.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_jobs_list_renders_cards` | `/jobs` merender satu `JobCard` per item fixture. |
| `test_job_card_anatomy_order` | Urutan elemen kartu sesuai R-F02-02. |
| `test_source_badge_per_source` | Tiga sumber menghasilkan titik warna token yang benar. |
| `test_salary_range_variants` | Empat varian gaji terender benar. |
| `test_description_clamped` | Kelas deskripsi dua baris diterapkan. |
| `test_empty_state_rendered` | Fixture kosong memicu `EmptyState`. |
| `test_skeleton_state` | `is_loading` memicu `SkeletonCard`. |
| `test_pagination_meta` | Rentang dan tombol sesuai `meta`. |
| `test_filter_chips_active` | Chip aktif menandai `aria-pressed="true"`. |
| `test_job_detail_renders` | Detail merender seluruh field dan tautan asli. |
| `test_company_page_no_external_profile` | Tidak ada logo, rating, jumlah karyawan di markup. |
| `test_public_pages_no_auth` | Semua route katalog 200 tanpa login. |

### 7.2 Pengujian Manual

1. Buka `/jobs` dan bandingkan berdampingan dengan `design-preview.html`.
2. Uji 360, 768, 1024, 1280 px; pastikan rail turun pada <1180 px.
3. Tab melalui kartu, chip, dan pagination; pastikan ring terlihat.
4. Uji fixture kosong dan fixture loading.
5. Buka detail lowongan dari ketiga sumber dan periksa badge serta tautan asli.
6. Buka halaman perusahaan dan pastikan tidak ada data di luar lowongan.

## 8. Out of Scope

- Filter dan pencarian di sisi database (PRD-04).
- Statistik gaji, kategori, dan clustering (PRD-05).
- Bookmark persisten (PRD-06).
- Grafik Chart.js (PRD-F05).
- Profil resmi perusahaan dari sumber eksternal.

## 9. Catatan Teknis

- Fixture JSON adalah kontrak. Ketika PRD-04 dikerjakan, service harus menghasilkan `dict` dengan bentuk identik agar template tidak perlu diubah.
- Tombol simpan pada kartu hanya mengubah `aria-pressed` dan ikon; tidak memanggil backend sampai PRD-06.
- Pencarian dan filter pada Track A mengubah query string lewat form GET biasa, sehingga state URL sudah benar sebelum backend ada.
- Deskripsi dua baris memakai `-webkit-line-clamp: 2` dengan `display: -webkit-box`.
- Format tanggal dan angka memakai filter Jinja `tanggal` dan `angka`, bukan inline.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-preview.html` baris 645–685 | Bar pencarian, tombol filter berbadge, chip filter, kontrol urutan dan toggle. |
| `docs/design-preview.html` baris 697–885 | Grid kartu, anatomi `JobCard`, varian gaji, `MatchBadge` dengan alasan, skeleton. |
| `docs/design-preview.html` baris 887–894 | Pagination dengan rentang dan tombol. |
| `docs/design-preview.html` baris 897–998 | Right rail: hint, panel statistik, panel profil, panel insight. |
| Bot Rekap Lowongan Dealls — `app.py` `@app.template_filter("tanggal")`, `("angka")` | Format tanggal Indonesia dan pemisah ribuan Indonesia untuk template. |

**Yang tidak diambil**

- Status aktif/nonaktif lowongan sebagai filter (tidak ada di skema).
- Kolom `slug` sebagai kunci URL; KarirLens memakai `id` numerik.
- Tombol "Pengalaman" pada pratinjau, karena skema tidak menyimpan level pengalaman.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Halaman katalog dapat ditinjau di browser dengan data fixture.
- Kontrak template pada §4.1 tertulis dan dipakai PRD-04.

## 12. Catatan Implementasi

| Berkas | Isi |
|---|---|
| `templates/jobs/list.html` | Pencarian, chip filter, urutan, grid kartu, pagination, empty/loading/error state, right rail |
| `templates/jobs/detail.html` | Judul di luar kartu, gaji, skill, deskripsi, tautan sumber, lowongan serupa |
| `templates/jobs/home.html` | Hero, `StatTile`, lowongan terbaru, pintasan kategori |
| `templates/companies/detail.html` | Ringkasan perusahaan dari data lowongan, tanpa profil eksternal |
| `app/preview/routes.py` | Route `home`, `jobs`, `jobs/<id>`, `companies/<slug>` beserta penyusun tautan chip |
| `app/preview/fixtures.py` | Filter naif, pagination, perusahaan per slug, lowongan serupa, opsi chip |
| `tests/fixtures/ui/` | `jobs.json` (6 item), `home.json`, `companies.json`, `jobs_empty.json` |
| `tests/unit/test_catalog.py` | 30 test untuk §7.1 |

Tiga keputusan yang diambil saat implementasi:

1. **Chip filter adalah tautan, bukan tombol dropdown.** Panel pilihan belum ada, sehingga ikon `▾` pada design system §4.6 tidak dirender — caret yang tidak membuka apa pun adalah state menipu (§2 prinsip 2). Chip kini toggle: klik menerapkan, klik lagi menghapus. Penyimpangan ini dicatat di docstring `filter_chip.html`.
2. **Tautan toggle disiapkan route, bukan template.** `_options()` mengembalikan `{value, label, active, href}` sehingga template tidak perlu tahu aturan "bila aktif, hapus filter".
3. **`height: 100%` pada `JobCard` dipindah ke `.cards .job-card`.** Di halaman detail, kartu berada di luar grid dan memanjang mengisi sisa tinggi `.feed` — ruang kosong sekitar 450px. Grid yang menetapkan tinggi, bukan kartunya.

### 12.1 Right Rail

`/preview/jobs` memuat seluruh isi rail yang disebut §3.1:

| Isi | Sumber data |
|---|---|
| Hint bar | `meta.total` |
| `MetricCell` | lowongan ditemukan, filter aktif, sparkline lowongan baru |
| `InsightCard` (kategori) | `home.json` → `categories` |
| `SkillPanel` | keadaan "belum masuk" untuk pengunjung publik |

**`SkillPanel` sengaja tidak menampilkan skill karangan.** Katalog publik tidak punya pengguna login, jadi yang dirender adalah keadaan kosong dengan ajakan masuk — menampilkan skill fiktif akan melanggar §2 prinsip 3.

**`MetricCell` hanya memuat angka yang konsisten dengan halaman.** Total perusahaan seluruh dataset (213) sengaja dibuang: di samping "6 lowongan" ia terbaca seolah 213 perusahaan punya 6 lowongan. Yang ditampilkan kini jumlah hasil dan jumlah filter aktif, plus sparkline 12 hari.

### 12.2 Tiga State Daftar

§3.1 mewajibkan state kosong, loading, dan error. Ketiganya kini ada dan diuji:

| State | Pemicu pada Track A | Test |
|---|---|---|
| Kosong | `?empty=1` | `test_empty_state_rendered` |
| Loading | `?loading=1` | `test_skeleton_state` |
| Error | `?error=1` | `test_error_state` |

Saat error, panel angka dan hint jumlah **tidak dirender** — "0 lowongan" adalah klaim, padahal datanya tidak diketahui. Hint berubah menjadi "Sumber lowongan tidak dapat diakses saat ini."

Dua bug visual ditemukan lewat audit browser dan langsung diperbaiki:

- **Judul detail tidak sejajar** (51px vs 32px) karena berada di dalam `.job-card` yang punya padding sendiri. Judul dipindah ke `.page-head` di luar kartu.
- **Footer menimpa tombol** pada halaman detail, akibat kartu yang melar tadi.

### 12.3 Perbaikan Setelah Uji Coba Pengguna

Dua keluhan nyata saat halaman dipakai, keduanya sudah diperbaiki:

**1. Hanya judul kartu yang dapat diklik.** Seluruh permukaan kartu kini menuju detail. Satu tautan penutup (`.card-link`, `position: absolute; inset: -1px; z-index: 1`) dipakai alih-alih membungkus kartu dengan `<a>`, karena kartu berisi `<button>` simpan dan `<button>` di dalam `<a>` tidak sah. Judul sengaja bukan tautan agar tidak ada dua tujuan tab yang sama. Tombol simpan diberi `z-index: 2` sehingga tetap dapat diklik sendiri.

`inset: -1px`, bukan `0`, karena `inset: 0` relatif terhadap padding box — border 1px tetap menjadi zona mati.

**2. Padding atas-bawah `.card-top` terlalu besar.** Penyebabnya tombol simpan: area sentuh 44×44 (§5) menggelembungkan baris dari 21px menjadi 44px. Area sentuh dipertahankan, tetapi tombol ditarik keluar dari alur visual dengan `margin-block: calc((var(--touch-min) - 20px) / -2)`. Hasil terukur di browser: **tinggi `.card-top` 44px → 21px**, tinggi kartu 237px.

Dua test baru menjaga keduanya: `test_whole_card_is_clickable` dan `test_card_top_not_inflated_by_save_button`.

**3. Tombol simpan tidak bereaksi.** Ia hanya mengubah `aria-pressed` dan ikon secara lokal, tanpa backend (PRD-F02 §9). Terverifikasi di browser: klik tombol tidak menavigasi dan `aria-pressed` berubah `false → true`.

### 12.4 Perapatan Halaman Detail

Enam keluhan pada halaman detail, semuanya diperbaiki dan diukur di browser:

| Keluhan | Perbaikan | Sesudah (terukur) |
|---|---|---|
| Jarak gaji → deskripsi terlalu tinggi | `gap` kartu 12px → 8px; margin anak dihapus | **16px** |
| Garis pemisah punya lubang besar di atasnya | `border-top` + `padding-top` dihapus dari `.detail-body` dan `.detail-actions` | **tanpa garis**, 0px |
| Gaji tanpa judul | `<div class="boxtitle">Gaji</div>` di atas `salary_range` | label tampil |
| Tombol simpan di baris aksi bawah | `position: absolute` di pojok kanan atas kartu (`top/right: 12px`) | 44×44, 13px dari tepi |
| Keterangan "Tautan menuju lowongan asli…" | dihapus — mengulang info yang sudah dibawa tombol sumber | hilang |
| "← Kembali ke daftar lowongan" teks telanjang | `.back-link`: border, radius chip, padding, ikon panah, hover | 32px tinggi |
| Jarak person → "Lihat semua lowongan" | `.panel-company`: `margin-bottom: 0` + `margin-top: 9px` | **9px** |

Catatan teknis:

- **`margin-block` negatif `.save-btn` mengalahkan `.detail-save`.** Karena `.job-card .save-btn` spesifisitasnya lebih tinggi, tombol pojok awalnya menempel 1px dari tepi atas. Diperbaiki dengan menulis selektor `.job-card .detail-save`.
- **`inset` vs `top/right`:** tombol pojok memakai `top`/`right` biasa karena ia satu-satunya anak absolute di kartu.
- **Jarak diatur `gap`, bukan margin anak.** `.tags` punya `margin-bottom: 12px` global yang menambah gap menjadi 20px; di kartu detail margin itu dinolkan.
- **Handler tombol simpan dipindah ke `base.html`.** Sebelumnya hanya ada di `list.html`, sehingga tombol di halaman detail tidak bereaksi. Satu handler di shell melayani kedua halaman.
- **Handler tidak lagi memanggil `stopPropagation()`.** Diperlukan saat tombol berada di dalam kartu bertautan; di halaman detail tidak, dan `preventDefault()` saja cukup.

Terukur pada 1280px: tombol pojok 44×44 dengan jarak 13px dari tepi atas dan kanan, gaji tidak pernah berada di bawahnya. Pada 360px: `scrollWidth` 360 = viewport, tanpa tumpang tindih.

Total test setelah §12.4: **174 lulus**.

### 12.5 Penyelarasan Halaman Perusahaan

Halaman perusahaan disamakan dengan halaman detail:

| Bagian | Sebelum | Sesudah |
|---|---|---|
| Tautan kembali | `<a>` telanjang di dalam `<p class="field-hint">` | `.back-link` — kendali 32px dengan ikon panah, sama persis dengan detail |
| Jarak nama → "2 lowongan tersedia · Jakarta Selatan" | **0px** (`.company-head .field-hint { margin: 0 }`) | **6px** |

Penyebabnya `.company-head .field-hint { margin: 0 }` yang menol-kan margin paragraf. Diganti dengan `margin-bottom: 6px` pada `h1` dan kelas `.company-sub` baru — memakai `.field-hint` di situ keliru karena teks ini bukan petunjuk isian, melainkan subjudul halaman.

Terukur: gap 6px pada 1280px maupun 360px, tanpa overflow.

Dua test baru menjaga keduanya: `test_company_back_link_matches_detail` dan `test_company_subtitle_has_small_gap`.

Total test setelah §12.5: **176 lulus**.

### 12.6 Garis Pemisah Bar Filter Dihapus

Garis horizontal tepat di atas "6 Lowongan" berasal dari `.filters`:

```css
padding: 0 0 18px;
border-bottom: 1px solid var(--line);
```

Garis itu memotong halaman persis di bawah kelompok chip dan terbaca sebagai batas tabel, bukan pemisah kelompok filter. Dihapus, diganti `margin-bottom: var(--space-4)` agar jarak ke judul hasil tidak hilang.

Terukur di browser: `border-bottom` menjadi `0px none`, jarak `.filters` → `.section-head` tetap **16px**.

Total test setelah task ini: **177 lulus**.
