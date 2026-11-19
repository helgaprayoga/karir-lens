# PRD-F01 — Design System & Kerangka UI

| Field | Keterangan |
|---|---|
| ID task | PRD-F01 |
| Nama task | Design System & Kerangka UI |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | Tidak ada (memanfaatkan kerangka PRD-01) |
| Task yang bergantung | PRD-F02 s.d. PRD-F06 |
| Status | Selesai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Design system | [Design System KarirLens](../design-system.md) |
| Arsitektur kode | [Arsitektur Kode KarirLens](../ARCHITECTURE.md) |

---

## 1. Konteks

Track A mengerjakan seluruh antarmuka lebih dulu, sebelum logika backend diisi. Task ini adalah fondasinya: mengubah kerangka kasar dari PRD-01 menjadi sistem komponen yang lengkap dan dapat dipakai ulang, sehingga PRD-F02 sampai PRD-F06 hanya menyusun halaman dari komponen yang sudah ada.

PRD-01 sudah menghasilkan `tokens.css`, `components.css`, `base.html`, dan form auth sederhana. Task ini melengkapinya: seluruh komponen pada design system §4, shell dua kolom, header lengkap dengan pencarian, dan halaman `/styleguide` untuk memeriksa state komponen tanpa membuka setiap fitur.

Acuan visual adalah [`design-preview.html`](../design-preview.html). Setiap komponen yang dibangun harus memakai bahasa visual yang sama dengan pratinjau itu: token warna, radius, padding, dan anatomi yang identik.

## 2. Tujuan

1. Menyediakan seluruh komponen design system §4 sebagai CSS + partial Jinja yang dapat dipakai ulang.
2. Menyediakan shell dua kolom (feed + rail) sesuai design system §3.4, termasuk aturan padding satu level.
3. Menyediakan header lengkap: brand, navpill per peran, pencarian, aksi AI, dan menu pengguna.
4. Menyediakan `/styleguide` yang menampilkan setiap komponen dalam semua state wajibnya.
5. Menyediakan mekanisme data contoh agar halaman dapat dirender sebelum backend ada.
6. Menjaga agar tidak ada nilai warna, jarak, atau radius lepas di template.

## 3. Scope

### 3.1 Termasuk

- `tokens.css` lengkap sesuai design system §3.1 sampai §3.7.
- `components.css` untuk seluruh komponen §4: `JobCard`, `SourceBadge`, `EmploymentTypeBadge`, `SkillTag`, `MatchBadge`, `FilterChip`, `SortControl`, `SearchField`, `Pagination`, `EmptyState`, `SalaryRange`, `StatTile`, `MetricCell`, `ChartCard`, `InsightCard`, `SkillPanel`, `SkeletonCard`, `Toast`, `DataTable`, `StatusPill`, `Button`, `NavPill`, `AlertBanner`.
- Partial Jinja di `templates/components/` untuk komponen yang berulang.
- Shell dua kolom: `.layout`, `.feed`, `.rail`, dengan aturan padding satu level.
- Header lengkap sesuai `design-preview.html` baris 612–643.
- `/styleguide` (hanya saat `PREVIEW_UI=true`) yang menampilkan semua komponen dan state.
- Blueprint `app/preview/` dan fixture `tests/fixtures/ui/*.json`.
- Font Inter dari Google Fonts dengan `display=swap`, fallback SF Pro lebih dulu.
- Ikon SVG inline sebagai partial, bukan pustaka ikon eksternal.

### 3.2 Tidak termasuk

- Query database, aturan bisnis, panggilan AI.
- Halaman fitur lengkap (PRD-F02 s.d. F05).
- Chart.js dan AutoAnimate (dimuat pada F02 dan F05 saat komponennya dipakai).
- Perubahan skema database atau service.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F01-01 | Seluruh token design system §3 tersedia sebagai CSS custom property di `static/css/tokens.css`. Tidak ada nilai hex lepas di template maupun komponen. | P0 |
| R-F01-02 | `components.css` menyediakan setiap komponen pada design system §4 beserta state default, hover, focus-visible, active, dan disabled. | P0 |
| R-F01-03 | Partial Jinja di `templates/components/` untuk `job_card`, `source_badge`, `skill_tag`, `filter_chip`, `pagination`, `empty_state`, `status_pill`, `alert_banner`, `skeleton_card`, `stat_tile`. | P0 |
| R-F01-04 | Shell dua kolom memakai `grid-template-columns: minmax(0, 1fr) var(--rail-w)`. Padding kiri hanya diberikan di `.layout`, tidak di `.feed`. | P0 |
| R-F01-05 | Header memuat brand, navpill, pencarian, tombol aksi AI, dan menu pengguna; navpill berubah menurut peran (publik, pengguna, admin). | P0 |
| R-F01-06 | Semua kontrol memakai `--r-chip`; `--r-full` hanya untuk toggle dan progress bar. | P0 |
| R-F01-07 | Breakpoint 1240, 1180, 900, 820, 480 px menghasilkan perubahan sesuai design system §3.6; target minimum 360 px. | P0 |
| R-F01-08 | `/styleguide` menampilkan setiap komponen dalam semua state, dan hanya tersedia ketika `PREVIEW_UI=true`. | P0 |
| R-F01-09 | Blueprint `app/preview/` hanya diregistrasi ketika `PREVIEW_UI=true`, dan menyajikan halaman dengan data dari `tests/fixtures/ui/*.json`. | P0 |
| R-F01-10 | Seluruh teks antarmuka berbahasa Indonesia; tidak ada nilai enum mentah database yang tampil. | P0 |
| R-F01-11 | `prefers-reduced-motion: reduce` mematikan seluruh transition dan animation. | P0 |
| R-F01-12 | Font Inter dimuat dengan `display=swap` dan `font-variant-numeric: tabular-nums` pada angka. | P1 |

### 4.1 Aturan Padding Satu Level

Design system §3.4 menetapkan aturan yang paling mudah dilanggar:

| Elemen | Padding | Catatan |
|---|---|---|
| `.top` | `18px var(--gutter-sheet)` | Gutter kiri dan kanan |
| `.page` | `24px var(--gutter-sheet) 0` | Gutter kiri dan kanan |
| `.layout` | `22px var(--gutter-sheet) 0` | **Satu-satunya** pemberi gutter kiri untuk kolom |
| `.feed` | `0 var(--gutter-rail) 32px 0` | Kiri `0` — mewarisi gutter dari `.layout` |
| `.rail` | `0 0 32px var(--gutter-rail)` | Kanan `0` — mewarisi gutter dari `.layout` |

Kebenaran yang harus terlihat: tepi kiri kartu, judul halaman, dan isi header berada di satu garis lurus. Tepi kanan rail rata dengan header.

### 4.2 Kontrak Template

Task ini menetapkan kontrak yang dipakai seluruh halaman berikutnya.

**`templates/base.html`** menerima:

| Variabel | Tipe | Keterangan |
|---|---|---|
| `nav_links` | `list[dict]` | Disediakan context processor; setiap item `{endpoint, label}` |
| `current_user` | objek | Flask-Login; menyediakan `is_authenticated`, `display_name`, `is_admin` |

**Partial `job_card`** menerima satu `job` dengan bentuk:

```json
{
  "id": 1,
  "title": "Data Engineer",
  "company_name": "Northwind Data",
  "company_slug": "northwind-data",
  "location": "Jakarta Pusat",
  "employment_type": "full-time",
  "description": "...",
  "skills": ["python", "sql"],
  "salary_min": 12000000,
  "salary_max": 18000000,
  "salary_currency": "IDR",
  "salary_period": "month",
  "source": "kalibrr",
  "source_url": "https://...",
  "posted_at": "2026-11-18T09:00:00Z",
  "is_saved": false,
  "match": { "score": 82, "reasons": ["skill: python", "skill: sql"] }
}
```

`match` boleh `none` untuk kartu non-rekomendasi. Partial tidak boleh memanggil service atau query; ia hanya membaca `job`.

## 5. Acceptance Criteria

- [x] Semua komponen pada design system §4 tersedia dan dapat dilihat di `/styleguide`.
- [x] Setiap komponen menampilkan state default, hover, focus-visible, active, dan disabled.
- [x] Tidak ada nilai hex, px radius, atau px padding lepas di template.
- [x] Tepi kiri kartu, judul halaman, dan isi header berada di satu garis lurus pada 1280 px.
- [x] Rail tetap `--rail-w` dan feed mengambil sisa ruang.
- [x] Layout tidak rusak pada 360, 768, 1024, dan 1280 px. *(diukur di browser: `scrollWidth` = viewport pada keempat lebar, tanpa overflow horizontal)*
- [x] `/styleguide` mengembalikan 404 ketika `PREVIEW_UI` tidak aktif.
- [x] Navpill menampilkan tautan berbeda untuk publik, pengguna login, dan admin.
- [x] Tidak ada animasi berjalan saat `prefers-reduced-motion: reduce`.
- [x] Halaman dapat dinavigasi dengan keyboard; focus ring terlihat pada semua kontrol. *(diukur di browser: 53 kontrol, semuanya punya focus ring; skip-link fokus-visible)*

## 6. Dependensi

- PRD-01 (application factory, `base.html`, token awal, konfigurasi).
- Bootstrap 5.3.3 lokal di `static/vendor/bootstrap/` (sudah tersedia).
- Font Inter dari Google Fonts (jaringan saat pengembangan; fallback sistem saat offline).
- `design-system.md` dan `design-preview.html` sebagai acuan visual.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_tokens_defined` | Setiap token pada design system §3 ada di `tokens.css`. |
| `test_no_raw_hex_in_templates` | Tidak ada nilai `#rrggbb` di `templates/**`. |
| `test_no_inline_style` | Tidak ada atribut `style=` di template, kecuali nilai data yang diizinkan. |
| `test_styleguide_available_in_preview` | `/styleguide` mengembalikan 200 ketika `PREVIEW_UI=true`. |
| `test_styleguide_hidden_in_production` | `/styleguide` mengembalikan 404 ketika `PREVIEW_UI` tidak aktif. |
| `test_components_rendered` | Setiap partial komponen dapat dirender dengan fixture tanpa error. |
| `test_radius_policy` | Hanya toggle dan progress bar memakai `--r-full`. |
| `test_preview_blueprint_gated` | Blueprint `preview` hanya terdaftar saat `PREVIEW_UI=true`. |
| `test_base_layout_has_required_hooks` | `base.html` memuat `.shell`, `.top`, `.layout`, skip-link, `lang="id"`. |

### 7.2 Pengujian Manual

1. Buka `/styleguide` dan periksa setiap komponen pada semua state.
2. Periksa garis lurus tepi kiri pada 1280 px: kartu, judul halaman, header.
3. Uji 360, 768, 1024, 1280 px; pastikan tidak ada horizontal scroll.
4. Tab melalui seluruh halaman; pastikan urutan fokus mengikuti urutan visual dan ring terlihat.
5. Aktifkan `prefers-reduced-motion` dan pastikan tidak ada animasi.
6. Bandingkan `/styleguide` dengan `design-preview.html` secara berdampingan.

## 8. Out of Scope

- Halaman fitur lengkap dan isinya (PRD-F02 s.d. F05).
- Query, service, repository, dan koneksi Supabase.
- Chart.js dan AutoAnimate.
- Dark mode dan aset ilustrasi (design system §9).

## 9. Catatan Teknis

- Partial Jinja disimpan di `templates/components/` dan dipanggil dengan `{% include %}` atau `{% import %}` sebagai macro. Macro lebih disukai agar parameter eksplisit.
- Gunakan `{% from "components/job_card.html" import job_card %}` agar kontrak parameter terlihat di template pemanggil.
- Untuk state komponen, cukup CSS (`:hover`, `:focus-visible`, `:active`, `[disabled]`); jangan memakai JavaScript untuk mengubah state visual.
- Nilai dinamis (panjang bar, warna titik sumber) boleh lewat atribut `data-*` atau custom property inline; ini bukan "nilai hex lepas" karena berasal dari token.
- `PREVIEW_UI` dibaca dari environment dan hanya aktif di pengembangan.

### 9.1 Catatan Implementasi

| Berkas | Isi |
|---|---|
| `static/css/tokens.css` | Seluruh token §3 plus token turunan yang dibutuhkan komponen (`--line-3`, `--line-4`, `--ink-4`, `--ink-5`, `--skeleton-*`, `--spark-*`, `--avatar-*`). |
| `static/css/components.css` | Seluruh komponen §4 plus shell dan motion. Satu berkas agar urutan cascade mudah dibaca. |
| `templates/components/` | `icons`, `job_card`, `source_badge`, `skill_tag`, `salary_range`, `filter_chip`, `pagination`, `empty_state`, `status_pill`, `alert_banner`, `skeleton_card`, `stat_tile`, `match_badge`. |
| `templates/preview/` | `styleguide.html` (audit visual) dan `index.html` (daftar halaman preview). |
| `app/preview/` | Blueprint + `fixtures.py`. Hanya membaca `tests/fixtures/ui/*.json` (aturan arsitektur 8). |
| `app/template_filters.py` | Filter `tanggal`, `tanggal_relatif`, `angka`, `persen`. |
| `tests/fixtures/ui/` | `jobs`, `jobs_recommended`, `insights`, `profile`, `runs`, `admin`. |
| `tests/unit/test_ui_rules.py` | 22 test penegak aturan §7.1. |

Dua keputusan yang diambil saat implementasi:

1. **`preview_ui` ditentukan dari `app.view_functions`, bukan dari `app.config`.** Versi pertama memakai config, dan gagal saat config diubah setelah `create_app` — `url_for('preview.styleguide')` melempar `BuildError` dan halaman 500. Pola ini sama dengan `app/navigation.py` yang sudah menyaring tautan terhadap endpoint terdaftar.
2. **Tinggi batang sparkline lewat `data-height` + JavaScript.** Atribut `style=` dilarang mutlak oleh test, termasuk untuk nilai data. Alternatifnya adalah kelas per tinggi, yang tidak masuk akal untuk 12 batang.

`static/css/app.css` dari PRD-01 dihapus: isinya sudah sepenuhnya digantikan `components.css`.

### 9.2 Hasil Audit Browser

Dijalankan dengan `agent-browser` (headless Chromium) pada server lokal, 18 November 2026. Audit terukur ini menemukan **delapan bug** yang tidak tertangkap test otomatis:

| Bug | Bukti | Perbaikan |
|---|---|---|
| Tag HTML tampil mentah di banner | `&lt;b&gt;PREVIEW_UI=true&lt;/b&gt;` terlihat sebagai teks | `alert_banner` menambah parameter `html`; teks polos di-escape |
| Judul kartu berwarna biru | `<a>` di dalam `h3` mewarisi warna tautan | `.job-card h3 a` diberi `color: var(--ink)` |
| Badge kecocokan melar selebar kartu | `.match` 431px (lebar kartu), bukan 74px | `align-self: flex-start` pada flex-column |
| Ikon EmptyState melar | SVG tanpa ukuran mengisi kotak grid | `.empty .empty-icon svg` diberi 22px |
| **Gutter dobel** | h1 di 64px, kartu di 32px — tidak segaris | `.content` jadi wadah netral; `.page` tidak menambah gutter di dalam `.layout`/`.layout-single` |
| **Overflow horizontal di 360px** | `scrollWidth` 541 vs viewport 360 | `base.html` tidak lagi memaksa grid dua kolom; tabel memakai `overflow-x: auto` |
| **Target sentuh 28px** | `.save-btn` 28×28, §5 minta 44×44 | tombol `var(--touch-min)` 44px |
| **Header tidak sejajar** | brand center 48px, nav pill center 40px | Bootstrap memberi `margin-bottom` pada `<ul>`; `.nav-pill` direset `margin: 0` |

Hasil akhir setelah perbaikan, diukur ulang di browser:

| Lebar | `scrollWidth` | Overflow | Tepi kiri brand / h1 / kartu |
|---|---|---|---|
| 1280px | 1280 | Tidak | 32 / 32 / 32 |
| 1024px | 1024 | Tidak | 24 / 24 / 24 |
| 768px | 768 | Tidak | 18 / 18 / 18 |
| 360px | 360 | Tidak | 18 / 18 / 18 |

Keyboard: 53 kontrol dapat difokus, **semuanya** menampilkan indikator fokus, dan skip-link terlihat saat difokus.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-preview.html` baris 610–643 | Struktur `.top`: brand dengan ikon SVG, `.navpill`, `.top-right` berisi aksi AI dan menu pengguna. |
| `docs/design-preview.html` baris 645–685 | Struktur `.page` dan `.head`: judul halaman, pencarian, tombol filter, baris chip filter, kontrol urutan. |
| `docs/design-preview.html` baris 687–895 | Struktur `.layout` dua kolom, `.feed` dengan grid kartu, `.pager`. |
| `docs/design-preview.html` baris 897–998 | Struktur `.rail`: hint bar, panel statistik, panel profil, panel insight. |
| `docs/design-preview.html` baris 699–724 | Anatomi `JobCard` lengkap: baris perusahaan+source+simpan, judul, meta, deskripsi, tag, gaji. |
| `docs/design-system.md` §3, §4, §5 | Seluruh token, anatomi komponen, dan aturan aksesibilitas. |

**Pola yang diadopsi**

- Satu sumber token; komponen merujuk peran, bukan nilai.
- Anatomi `JobCard` tetap identik antar halaman.
- Padding kiri satu level agar tepi kiri sejajar.
- State wajib terlihat, bukan ditebak.

**Yang tidak diambil**

- Angka dan teks statis pada pratinjau (mis. "12 lowongan", "Helga A.") — diganti data dari fixture, lalu dari service pada Track B.
- Panel yang tidak punya tabel sumber di database (mis. "kelengkapan profil") sesuai design system §6.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- `/styleguide` menampilkan seluruh komponen design system §4.
- Kontrak template pada §4.2 tertulis dan dipakai PRD-F berikutnya.
