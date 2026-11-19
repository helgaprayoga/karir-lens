# PRD-F02 — Katalog Publik (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F02 |
| Nama task | Katalog Publik |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01 |
| Task yang bergantung | PRD-F03, PRD-F04, PRD-F05, PRD-04 |
| Status | Belum dimulai |
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

- [ ] `/jobs` tampil dengan pencarian, chip filter, urutan, grid kartu, right rail, dan pagination.
- [ ] `/` menampilkan hero, ringkasan jumlah, lowongan terbaru, dan pintasan kategori.
- [ ] `/jobs/<id>` menampilkan detail lengkap dan tautan sumber asli.
- [ ] `/companies/<slug>` hanya menampilkan data turunan lowongan.
- [ ] Setiap kartu menampilkan badge sumber yang benar.
- [ ] Deskripsi terpotong tepat dua baris.
- [ ] Chip filter aktif dapat dihapus dan menandai `aria-pressed`.
- [ ] Kondisi kosong memakai `EmptyState` dengan saran.
- [ ] Skeleton tampil pada state loading, tanpa teks palsu.
- [ ] Layout tidak rusak pada 360, 768, 1024, dan 1280 px.
- [ ] Tepi kiri kartu sejajar dengan judul halaman dan header.
- [ ] Semua route katalog dapat dibuka tanpa login.

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
