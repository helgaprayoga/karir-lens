# Design System KarirLens

| Field | Keterangan |
|---|---|
| Nama dokumen | Design System KarirLens |
| Versi | 2.0 |
| Status | Final untuk implementasi |
| Pemilik | Helga Arya Prayoga |
| Mata kuliah | Praktik Aplikasi Web |
| Tanggal | 18 November 2026 |
| Dokumen terkait | [PRD KarirLens](./PRD.md), [PRD per Task](./tasks/README.md), [Pratinjau HTML](./design-preview.html) |

---

## 1. Tujuan

Dokumen ini menetapkan **bagaimana** antarmuka KarirLens dibangun secara konsisten: token visual, sistem padding, spesifikasi komponen, state wajib, motion, dan aturan aksesibilitas.

Pembagian tanggung jawab:

| Dokumen | Menjawab |
|---|---|
| PRD | Apa yang dibangun, untuk siapa, dan kapan dinyatakan selesai |
| Design System (dokumen ini) | Bagaimana tampilan dan komponen dibangun sekali lalu dipakai ulang |

PRD **tidak** mendefinisikan warna, radius, padding, atau anatomi kartu. Dokumen inilah yang menetapkannya. Sebaliknya, design system tidak boleh menambah fitur — ia hanya mengeksekusi komponen yang sudah disetujui PRD.

Pratinjau visual yang memakai seluruh token dan komponen di dokumen ini ada di [`design-preview.html`](./design-preview.html). Dokumen dan pratinjau harus selalu sinkron.

### 1.1 Ruang Lingkup

Termasuk dalam dokumen ini:

- Token warna, tipografi, spacing, radius, elevation, motion, dan breakpoint.
- Sistem padding dan lebar halaman.
- Inventaris komponen beserta anatomi dan seluruh state.
- Aturan aksesibilitas dan checklist review UI.
- Larangan eksplisit terhadap pola yang bertentangan dengan scope produk.

Tidak termasuk:

- Fitur baru atau perubahan alur produk.
- Halaman marketing dan materi promosi.
- Aset logo dan ilustrasi.
- Dark mode.

## 2. Prinsip Desain

Empat prinsip berikut diturunkan dari kebutuhan PRD dan menjadi dasar setiap keputusan visual.

1. **Kartu yang dapat dipindai, bukan dibaca.** Setiap `JobCard` memakai urutan anatomi yang identik agar pengguna dapat membandingkan lowongan secara vertikal tanpa membaca ulang.
2. **State tidak boleh ditebak.** Setiap komponen interaktif wajib punya state terlihat: default, hover, focus, active, disabled, loading. Tidak ada kontrol yang tampil seragam padahal perilakunya berbeda.
3. **Jujur terhadap data.** Angka dan badge hanya tampil bila datanya ada. Skor kecocokan selalu disertai alasan. Statistik gaji tidak muncul bila sampel kurang dari lima. Tidak ada metrik karangan yang tidak punya tabel sumber di database.
4. **Bahasa manusia, bukan nama kolom.** Teks antarmuka ditulis dalam Bahasa Indonesia yang wajar. Nilai mentah database tidak boleh bocor ke layar.

## 3. Fondasi

### 3.1 Warna

Warna dikelompokkan berdasarkan **peran**, bukan nama. Komponen merujuk peran, sehingga perubahan tema cukup dilakukan di satu tempat. Seluruh nilai di tabel ini sudah diuji kontras (lihat Lampiran A).

**Permukaan**

| Token | Nilai | Peran |
|---|---|---|
| `--sheet` | `#FFFFFF` | Latar utama aplikasi. Shell fullscreen, bukan kartu mengambang. |
| `--sunken` | `#F4F5F7` | Latar input pencarian, nav, tag skill, badge sumber |
| `--sunken-2` | `#FAFAFB` | Latar cell statistik dan kartu insight di right rail |
| `--line` | `#EEF0F3` | Garis dekoratif: pemisah header, border kartu |
| `--line-2` | `#E1E4E9` | Border kontrol sekunder: input, chip, select |
| `--line-strong` | `#111827` | Border kontrol yang sedang terpilih |

**Teks**

| Token | Nilai | Peran | Kontras di `--sheet` |
|---|---|---|---|
| `--ink` | `#101215` | Judul, angka utama | 18.76:1 |
| `--ink-2` | `#4A515B` | Deskripsi, label kontrol | 8.02:1 |
| `--ink-3` | `#5B6270` | Metadata, caption, placeholder | 6.13:1 |

**Aksi dan status**

| Token | Nilai | Peran |
|---|---|---|
| `--action` | `#15181C` | Tombol primer, item nav aktif, toast |
| `--blue` | `#2563EB` | Aksen info, focus ring, ikon lokasi |
| `--violet` | `#6D28D9` | Kecocokan tinggi, ikon skill |
| `--rose` | `#E11D48` | Ikon level pengalaman |
| `--green` | `#15803D` | Status sukses, sampel mencukupi |
| `--amber` | `#B45309` | Data terbatas, peringatan |
| `--danger` | `#DC2626` | Latar aksi merusak, border error |
| `--danger-ink` | `#B91C1C` | Teks error di atas `--danger-bg` |

**Permukaan status** — wajib dipakai berpasangan dengan teks status, jangan teks abu di atas putih.

| Token | Nilai | Pasangan teks | Kontras |
|---|---|---|---|
| `--success-bg` | `#EAF7EE` | `--green` | 4.55:1 |
| `--warning-bg` | `#FEF4E7` | `--amber` | 4.62:1 |
| `--info-bg` | `#EEF3FF` | `--blue` | 4.65:1 |
| `--match-high-bg` | `#F3EEFF` | `--violet` | 6.25:1 |
| `--hint-bg` | `#F0F6FF` | `#1E40AF` | 8.03:1 |
| `--danger-bg` | `#FEF2F2` | `--danger-ink` | 5.91:1 |

**Warna sumber lowongan** — wajib ada di KarirLens. Nilai dipilih agar lolos 3:1 terhadap `--sunken`.

| Token | Nilai | Sumber | Kontras di `--sunken` |
|---|---|---|---|
| `--source-dealls` | `#0284C7` | Dealls | 3.75:1 |
| `--source-kalibrr` | `#059669` | Kalibrr | 3.45:1 |
| `--source-remotive` | `#B45309` | Remotive | 4.60:1 |

**Gradien AI**

| Token | Nilai | Peran |
|---|---|---|
| `--ai-from` | `#C4B5FD` | Gradien AI (awal) |
| `--ai-to` | `#93C5FD` | Gradien AI (akhir) |

Aturan pemakaian warna:

- Gradien `--ai-from` → `--ai-to` **hanya** untuk elemen yang memanggil asisten AI. Jangan dipakai sebagai dekorasi.
- Warna sumber dipakai sebagai titik aksen 5-6px, bukan latar kartu penuh.
- `--rose` hanya untuk ikon level pengalaman. `--green` dan `--amber` hanya untuk status, dan selalu di atas permukaan status pasangannya.
- Merah bukan penanda skor. Skor kecocokan rendah memakai `--ink-3`, bukan merah, agar tidak terbaca sebagai kesalahan.
- `--line` adalah garis dekoratif (1.22:1). Batas kontrol interaktif memakai `--line-2`, dengan dukungan label teks dan state hover; lihat Lampiran A untuk trade-off yang masih terbuka.

### 3.2 Tipografi

Satu keluarga font dengan dukungan angka tabular. Skala dibuat terbatas agar hierarki tegas.

```css
--font-sans: "SF Pro Display", "SF Pro Text", -apple-system,
             BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
```

SF Pro dipakai di perangkat Apple; Inter (Google Fonts) menjadi fallback yang tampil di Windows. Keduanya dipilih karena bentuk huruf `a`, `g`, dan `1` yang serupa, sehingga layout tidak bergeser antar platform.

| Token | Ukuran / tinggi baris | Bobot | Tracking | Pemakaian |
|---|---|---|---|---|
| `--text-page` | 38px / 1.05 | 700 | `-0.038em` | Judul halaman (`Jelajahi Lowongan`) |
| `--text-section` | 18.5px / 1.3 | 600 | `-0.018em` | Judul bagian (`12 Lowongan`, `Kesiapan Rekomendasi`) |
| `--text-stat` | 21px / 1.05 | 700 | `-0.03em` | Angka besar di cell statistik |
| `--text-card` | 16.5px / 1.32 | 600 | `-0.015em` | Judul lowongan di kartu |
| `--text-body` | 13.5px / 1.5 | 400 | 0 | Deskripsi lowongan |
| `--text-label` | 13px / 1.4 | 500 | 0 | Label form, tombol, chip, nav |
| `--text-meta` | 12px / 1.4 | 500 | 0 | Baris meta di kartu |
| `--text-micro` | 11px / 1.35 | 500 | 0 | Badge sumber, tag skill, caption cell |

Aturan:

- Rasio ukuran antar level minimal 1.15 agar hierarki terlihat.
- `--text-meta` dan `--text-micro` tidak boleh dipakai untuk isi utama.
- Angka memakai `font-variant-numeric: tabular-nums` agar sejajar dalam daftar.
- Setelan global:

```css
font-optical-sizing: auto;
font-feature-settings: "kern" 1, "liga" 1, "cv11" 1, "ss01" 1;
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;   /* penting di Windows */
text-rendering: optimizeLegibility;
```

- Maksimal dua bobot berbeda dalam satu kartu.

### 3.3 Spacing

Skala kelipatan 4px untuk jarak di dalam komponen:

| Token | Nilai |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |

### 3.4 Sistem Padding dan Lebar

Ini bagian yang paling mudah salah. Aturannya: **padding kiri hanya boleh diberikan di SATU level**, bukan berlapis.

**Shell fullscreen.** Aplikasi tidak memakai kanvas berbingkai. `body` tidak punya padding; `.shell` mengisi seluruh viewport.

```css
body   { padding: 0 }
.shell { width: 100%; min-height: 100vh; border-radius: 0; border: 0; box-shadow: none }
```

**Token padding**

| Token | Nilai | Peran |
|---|---|---|
| `--gutter-sheet` | 32px | Padding horizontal di dalam shell: header, page, layout |
| `--gutter-rail` | 24px | Jarak feed ↔ garis pemisah ↔ isi rail |
| `--gap-card` | 16px | Jarak antar kartu dalam grid |
| `--pad-card-y` | 18px | Padding vertikal kartu |
| `--pad-card-x` | 18px | Padding horizontal kartu |
| `--pad-panel` | 15px | Padding panel di right rail |
| `--pad-cell` | `11px 12px` | Padding cell statistik |
| `--pad-hint` | 12px | Padding hint bar |

**Pembagian padding per elemen**

| Elemen | Padding | Kenapa |
|---|---|---|
| `.top` (header) | `18px var(--gutter-sheet)` | Gutter kiri dan kanan |
| `.page` (judul + filter) | `24px var(--gutter-sheet) 0` | Gutter kiri dan kanan |
| `.layout` | `22px var(--gutter-sheet) 0` | **Satu-satunya pemberi gutter kiri untuk kolom** |
| `.feed` | `0 var(--gutter-rail) 32px 0` | Kiri sengaja `0` — mewarisi gutter dari `.layout` |
| `.rail` | `0 0 32px var(--gutter-rail)` | Kanan `0` — mewarisi gutter dari `.layout` |

**Kenapa `.feed` padding kiri `0`.** `.layout` sudah memberi `--gutter-sheet`. Jika `.feed` menambah padding kiri sendiri, kartu pertama akan menjorok melewati judul halaman dan header. Ini bug nyata yang pernah terjadi pada versi pratinjau. Akibat kebenarannya: tepi kiri kartu, judul halaman, dan isi header berada di satu garis lurus.

**Lebar**

| Elemen | Aturan |
|---|---|
| Shell | `width: 100%` — full-bleed, tanpa `max-width` |
| Layout | `grid-template-columns: minmax(0, 1fr) var(--rail-w)` — feed fleksibel, rail tetap `322px` |
| Grid kartu | `repeat(2, minmax(0, 1fr))` + `gap: var(--gap-card)` |
| Grid statistik | `repeat(auto-fit, minmax(104px, 1fr))` — melebar saat ruang cukup, turun ke satu kolom saat sempit |

Prinsip "expanded": feed mengambil **seluruh sisa ruang** (`minmax(0, 1fr)`) sementara rail tetap. Tidak ada ruang kosong menganga, tetapi juga tidak memaksa lebar tetap yang membuat konten melar di monitor ultrawide.

### 3.5 Radius dan Elevation

| Token | Nilai | Pemakaian |
|---|---|---|
| `--r-sm` | 8px | Tag skill, badge kecil, kotak ikon |
| `--r-chip` | 10px | **Semua kontrol**: chip filter, nav, tombol, badge sumber, pill status, counter |
| `--r-md` | 12px | Input, select, item nav |
| `--r-card` | 16px | Kartu lowongan, panel rail |
| `--r-full` | 9999px | **Hanya** toggle switch dan progress bar |

**Aturan bentuk:** seluruh kontrol memakai `--r-chip` — kotak dengan sudut membulat, **bukan pill**. Hanya dua elemen yang tetap penuh membulat karena bentuknya menyatakan status: toggle switch (on/off) dan progress bar (kemajuan). Titik sumber, avatar, dan ikon indikator memakai `border-radius: 50%` karena lingkaran, bukan pill.

**Elevation** — kartu **tidak** memakai shadow saat diam. Border 1px sudah cukup dan mencegah tampilan "kotor" dari border + shadow bersamaan.

| Token | Nilai | Pemakaian |
|---|---|---|
| `--shadow-hover` | `0 4px 12px -2px rgba(16,24,40,.10)` | Hanya saat kartu hover |
| `--shadow-toast` | `0 8px 24px -6px rgba(16,24,40,.35)` | Toast |

### 3.6 Breakpoint

| Token | Lebar | Perubahan |
|---|---|---|
| `--bp-lg` | 1240px | `--gutter-sheet` 32 → 24, `--rail-w` 322 → 300 |
| `--bp-rail-drop` | 1180px | Rail turun ke bawah sebagai 2 kolom |
| `--bp-md` | 900px | Rail menjadi 1 kolom |
| `--bp-sm` | 820px | `--gutter-sheet` → 18, kartu 1 kolom, `--pad-card-x` → 16 |
| `--bp-xs` | 480px | `--pad-card-y` → 16, judul halaman 25px |

Target minimum adalah **360px** sesuai PRD §9.5.

### 3.7 Motion

Animasi KarirLens **hanya untuk memperjelas perubahan state**, bukan dekorasi. Aturan penentu: bila animasi tidak membantu pengguna memahami apa yang baru berubah, hapus.

| Token | Nilai | Pemakaian |
|---|---|---|
| `--dur-instant` | 90ms | Feedback tekan (`:active`) |
| `--dur-fast` | 120ms | Hover, focus, perubahan border |
| `--dur-base` | 200ms | Masuk/keluar kartu, list, toast, fade |
| `--ease-out` | `cubic-bezier(.22,1,.36,1)` | Gerak masuk, muncul |
| `--ease-in-out` | `cubic-bezier(.65,0,.35,1)` | Shimmer, loop |

Aturan:

- Durasi maksimum **200ms**. Lebih dari itu terasa lambat saat memfilter.
- `prefers-reduced-motion: reduce` mematikan **transition dan animation**, bukan hanya transition. AutoAnimate juga tidak dimuat.
- Jangan menganimasikan `width`, `height`, atau `top/left` bila `transform` bisa dipakai.
- Tidak ada animasi yang berjalan terus-menerus kecuali shimmer skeleton.

#### Daftar animasi yang diizinkan

| # | Animasi | Pemicu | Requirement |
|---|---|---|---|
| 1 | Card lift (`translateY(-1px)` + `--shadow-hover`) | Hover kartu | R-04-07 |
| 2 | Skeleton shimmer | State loading | R-04-06 |
| 3 | Bookmark pop (`scale 1 → 1.18 → 1`) | Bookmark disimpan | R-06-03 |
| 4 | List masuk/keluar (AutoAnimate) | Filter berubah, bookmark/skill dihapus | R-04-02, R-06-04 |
| 5 | Toast slide-up + fade | Simpan/hapus berhasil | R-06-08 |
| 6 | EmptyState fade-up | Hasil pencarian kosong | R-04-06 |
| 7 | MatchBadge pop-in | Rekomendasi dimuat | R-07-10 |
| 8 | Sparkline grow dari bawah | Insight dimuat | R-05-13 |

#### Pustaka

| Pilihan | Ukuran | Keputusan |
|---|---|---|
| CSS transition/animation native | 0 KB | **Dipakai** untuk seluruh animasi state |
| AutoAnimate (FormKit) | ~2 KB | **Dipakai** untuk list dinamis, dimuat dengan fallback |
| Chart.js animation | 0 KB (sudah ada) | **Dipakai** untuk grafik insight |
| View Transitions API | 0 KB | Opsional, progressive enhancement |
| GSAP | ~28 KB + plugin | **Tidak dipakai**: tidak ada kebutuhan timeline kompleks, dan bertabrakan dengan target performa PRD §9.1 |
| AOS / scroll-reveal | ~6 KB | **Tidak dipakai**: dekoratif, tidak menjelaskan state |

AutoAnimate dimuat malas (`defer`) dan aplikasi tetap berfungsi bila CDN gagal — animasi list dilewati, tidak ada error yang terlihat pengguna. Saat implementasi Flask, simpan berkasnya di `static/vendor/` agar tidak bergantung jaringan.

## 4. Inventaris Komponen

| Komponen | Dipakai di | Acuan requirement |
|---|---|---|
| `JobCard` | `/jobs`, `/saved`, rekomendasi | R-04-07, R-06-03 |
| `SourceBadge` | Kartu dan detail lowongan | R-04-08 |
| `EmploymentTypeBadge` | Kartu dan detail | R-03-04, R-04-07 |
| `SkillTag` | Kartu, detail, profil | R-03-06 |
| `MatchBadge` | Rekomendasi | R-07-10 |
| `FilterChip` | Bar filter `/jobs` | R-04-02 |
| `SortControl` | Bar filter `/jobs` | R-04-03 |
| `SearchField` | `/jobs`, admin | R-04-01 |
| `Pagination` | `/jobs`, `/saved`, admin | R-04-04, R-06-07 |
| `EmptyState` | Semua daftar | R-04-06, R-06-07 |
| `SalaryRange` | Kartu dan detail | R-05-09 |
| `StatTile` | `/insights`, `/admin` | R-05-06, R-09-02 |
| `MetricCell` | Right rail, `/admin` | R-05-06, R-06-01 |
| `ChartCard` | `/insights` | R-05-13 |
| `InsightCard` | Right rail "Insight AI" | R-07-09 |
| `SkillPanel` | Right rail profil | R-06-01 |
| `SkeletonCard` | Semua daftar saat memuat | R-04-06 |
| `Toast` | Aksi simpan/hapus | R-06-08 |
| `DataTable` | `/admin/*` | R-09-03, R-09-05 |
| `StatusPill` | `/admin/runs` | R-09-06 |
| `Button` | Seluruh aplikasi | — |
| `NavPill` | Header | R-06-10 |
| `AlertBanner` | Insight, data terbatas | R-05-11 |

### 4.1 JobCard

Komponen inti. Urutan anatomi **wajib** dan tidak boleh diubah antar halaman.

```text
┌────────────────────────────────────────────┐
│ [Perusahaan] [badge sumber]        [simpan]│  baris 1
│ Judul Lowongan                             │  baris 2
│ ◎ level · ⌖ lokasi · 🕘 waktu              │  baris 3
│ Deskripsi, tepat dua baris...              │  baris 4
│ [skill] [skill] [skill] [+N]               │  baris 5
│ Gaji                                       │  baris 6
└────────────────────────────────────────────┘
```

| Bagian | Aturan |
|---|---|
| Nama perusahaan | `--text-micro`, `--ink-2`, satu baris dengan ellipsis |
| `SourceBadge` | Wajib tampil, tepat setelah nama perusahaan |
| Judul | `--text-card`, `--ink`, maksimal dua baris dengan ellipsis |
| Baris meta | `--text-meta`, `--ink-3`, dipisah titik tengah. Ikon berwarna: level `--rose`, lokasi `--blue`, waktu `--ink-3`. Field kosong disembunyikan, jangan tampilkan placeholder palsu |
| Deskripsi | `--text-body`, `--ink-3`, **tepat dua baris** dengan `-webkit-line-clamp: 2` |
| Skill | Maksimal empat `SkillTag`, sisanya `+N` |
| Gaji | `SalaryRange`, didorong ke bawah dengan `margin-top: auto` agar semua kartu dalam satu baris sejajar |
| Tombol simpan | 28×28px visual, area sentuh 44×44px, `aria-pressed` |

Ritme vertikal internal kartu — **bukan satu nilai untuk semua blok**:

| Jarak | Nilai |
|---|---|
| `c-top` → judul | 9px |
| judul → meta | 7px |
| meta → deskripsi | 10px |
| deskripsi → tag | 12px |
| tag → harga | 14px |

State:

| State | Perubahan |
|---|---|
| Default | Border `--line` 1px, **tanpa shadow** |
| Hover | Border `--line-2`, `translateY(-1px)`, `--shadow-hover` |
| Focus-visible | Ring 2px `--blue` offset 2px |
| Tersimpan | Ikon bookmark terisi, `aria-pressed="true"` |
| Loading | `SkeletonCard`, tanpa teks palsu |

**Larangan:** tidak ada kolom jumlah pelamar, proposals, status lamaran, atau tahapan seleksi. Produk ini menyimpan bookmark, bukan melacak lamaran (PRD §4 Non-Tujuan).

### 4.2 SourceBadge

Identitas KarirLens. Setiap lowongan wajib menampilkan asalnya.

| Properti | Aturan |
|---|---|
| Teks | Nama sumber: `Dealls`, `Kalibrr`, `Remotive` |
| Ikon | Titik `--source-*` 5px, `border-radius: 50%` |
| Latar | `--sunken`, radius `--r-chip` |
| Teks | `--text-micro`, `--ink-3` |
| Padding | `2px 7px` |
| Aksesibilitas | `aria-label="Sumber: Dealls"` |

Di halaman detail, badge sumber disertai kalimat atribusi dan tautan ke lowongan asli (R-04-08).

### 4.3 EmploymentTypeBadge

Nilai baku mengikuti R-03-04: `full-time`, `part-time`, `contract`, `internship`, `freelance`, `unknown`.

| Nilai baku | Label tampil |
|---|---|
| `full-time` | Penuh waktu |
| `part-time` | Paruh waktu |
| `contract` | Kontrak |
| `internship` | Magang |
| `freelance` | Lepas |
| `unknown` | Tidak disebutkan |

`unknown` **tidak** ditampilkan sebagai badge; cukup hilangkan badge-nya.

### 4.4 SkillTag

| Properti | Aturan |
|---|---|
| Ukuran teks | `--text-micro` |
| Latar | `--sunken` |
| Teks | `--ink-2` — **wajib lolos kontras**, jangan memakai abu di atas abu |
| Radius | `--r-sm` |
| Padding | `4px 9px` |
| Mode | Statis pada kartu; dapat diklik pada detail sebagai filter |

Pada kartu, maksimal empat tag lalu penanda `+N` berwarna `--ink-3`.

### 4.5 MatchBadge

Dipakai **hanya** pada rekomendasi. Selalu berpasangan dengan alasan.

| Tier | Kondisi | Token | Label tampil |
|---|---|---|---|
| Tinggi | Skor ≥ 75 | `--violet` di `--match-high-bg` | `82% cocok` |
| Sedang | Skor 50-74 | `--blue` di `--info-bg` | `61% cocok` |
| Rendah | Skor < 50 | `--ink-3` di `--sunken` | `42% cocok` |

Aturan:

- Angka persen boleh ditampilkan, tetapi **wajib** disertai alasan tekstual, misalnya "Cocok pada 3 skill yang Anda konfirmasi: python, sql, tableau" (R-07-10).
- Alasan dipisah garis putus-putus dari isi kartu.
- Ambang harus dinyatakan di satu tempat konfigurasi, tidak tersebar di template.
- Jangan memakai merah untuk skor rendah.

### 4.6 FilterChip

Dua varian yang **harus terlihat berbeda**:

| Varian | Tampilan | Perilaku | Contoh |
|---|---|---|---|
| **Dropdown** | Border `--line-2`, teks `--ink-2`, ikon `▾` | Membuka pilihan; belum aktif | `Kota ▾` |
| **Terapan** | Border `#9AA1AC`, teks `--ink`, ikon `×` | Menghapus filter | `Jakarta ×` |

| Properti | Nilai |
|---|---|
| Tinggi | 38px |
| Padding | `0 13px` |
| Radius | `--r-chip` |
| Teks | `--text-label`, bobot 500 |
| Hover | Latar `--sunken`, border `#D2D7DE` |

Aturan:

- Jangan mencampur kedua makna dalam satu tampilan seragam.
- Chip terapan memakai `aria-pressed="true"`.
- Perubahan filter mengubah URL (R-04-14).
- Tombol `Filter` di header menampilkan jumlah filter aktif sebagai counter `--r-chip`.

**Toggle pengurutan (mis. "Cocokkan otomatis") tidak boleh diletakkan di baris filter.** Toggle mengubah cara hasil diurutkan, bukan menyaring isi, sehingga ditempatkan terpisah di dekat kontrol pengurutan (`SortControl`).

### 4.7 SalaryRange

| Kondisi data | Tampilan |
|---|---|
| `min` dan `max` ada | `Rp 9.000.000 – 14.000.000 / bulan` |
| Hanya `min` | `Mulai Rp 11.000.000 / bulan` |
| Hanya `max` | `Sampai Rp 8.000.000 / bulan` |
| Kosong | `Gaji tidak dicantumkan` |
| Mata uang berbeda | Selalu tampilkan kode mata uang, jangan diasumsikan IDR |

Angka memakai `--text-card` bobot 700 dengan `tabular-nums`; satuan `/ bulan` memakai `--text-micro` `--ink-3`. Pemisah ribuan gaya Indonesia sesuai R-04-11. Tidak ada nilai prediksi.

### 4.8 StatTile, MetricCell, dan ChartCard

`StatTile` menampilkan satu angka besar dengan label kecil di halaman insight.

- Angka: `--text-page`, bobot 700, `tabular-nums`.
- Label: `--text-micro`, `--ink-3`.
- Bila data tidak mencukupi (mis. sampel gaji < 5), tampilkan `—` dengan keterangan "Data belum cukup", **bukan** angka nol.

`MetricCell` adalah versi ringkas untuk right rail dan admin.

| Properti | Aturan |
|---|---|
| Wadah | Latar `--sunken-2`, border `--line`, radius `--r-chip`, padding `11px 12px` |
| Grid | `repeat(auto-fit, minmax(104px, 1fr))`, `gap 10px` |
| Angka | `--text-stat`, bobot 700 |
| Ikon | 18×18px, `flex: 0 0 18px`, warna sesuai makna |
| Caption | `--text-micro`, `--ink-3`, `overflow-wrap: anywhere` |
| Cell lebar penuh | `.cell.wide` dengan `grid-column: 1 / -1` untuk tren bersparkline |
| Cell tren | Label di **samping** angka, sparkline di **bawah** selebar cell |

`ChartCard` membungkus grafik Chart.js.

- Tinggi minimum 240px, maksimum 360px.
- Setiap grafik punya judul dan label sumbu yang jelas.
- Satu registry chart per halaman; grafik lama wajib di-`destroy()` sebelum membuat yang baru agar canvas tidak menumpuk.
- Palet grafik memakai token yang sama dengan badge agar konsisten.
- Pada lebar 360px, legenda turun ke bawah grafik.

### 4.9 Pagination

- Menampilkan `Menampilkan 1–12 dari 240 lowongan` plus kontrol halaman.
- Ukuran halaman baku: 12 untuk `/jobs`, 20 untuk `/saved` dan admin.
- Tombol halaman: 32×32px, radius 9px, halaman aktif berlatarbelakang `--action`.
- Tombol nonaktif benar-benar nonaktif (`disabled`), bukan hanya berwarna pucat.
- Wajib ada di semua daftar; tidak boleh memuat seluruh data ke browser (PRD §9.1).

### 4.10 EmptyState

Setiap daftar kosong wajib memakai komponen ini.

| Konteks | Pesan | Aksi |
|---|---|---|
| Pencarian kosong | "Tidak ada lowongan yang cocok dengan '{kata}'." | "Hapus semua filter" |
| Bookmark kosong | "Belum ada lowongan tersimpan." | "Jelajahi lowongan" |
| Skill belum dikonfirmasi | "Unggah CV agar rekomendasi dapat dihitung." | "Unggah CV" |
| Data insight kurang | "Data belum mencukupi untuk menampilkan statistik." | — |

Wadah: border putus-putus `--line-2`, padding `48px 24px`, ikon 52px di kotak `--sunken`. Animasi fade-up 200ms. Jangan menampilkan grafik atau tabel kosong tanpa penjelasan.

### 4.11 StatusPill

Dipakai di `/admin/runs` untuk status proses.

| Status sistem | Label tampil | Warna |
|---|---|---|
| `success` | Berhasil | `--green` di `--success-bg` |
| `partial` | Sebagian berhasil | `--amber` di `--warning-bg` |
| `failed` | Gagal | `--danger-ink` di `--danger-bg` |
| `running` | Sedang berjalan | `--ink-3` di `--sunken` |
| `skipped` | Dilewati | `--ink-3` di `--sunken` |

| Properti | Nilai |
|---|---|
| Radius | `--r-chip` |
| Padding | `3px 10px` |
| Teks | `--text-micro`, bobot 600 |
| Ikon | Titik 6px berwarna sama dengan teks |

Label ditulis manusia. Nilai enum mentah seperti `onprogress` atau `suggested` tidak boleh tampil di layar.

### 4.12 InsightCard

Kartu insight di right rail. Menggantikan pola bullet list bertitik kecil yang terbaca pasif.

```text
┌──────────────────────────────────────┐
│ [ikon]  3 lowongan baru sesuai       │
│         skill yang Anda konfirmasi   │
│         [Baru] hari ini              │
└──────────────────────────────────────┘
```

| Bagian | Aturan |
|---|---|
| Wadah | `--sunken-2`, border `--line`, radius `--r-chip`, padding `10px 11px` |
| Grid | `auto minmax(0, 1fr)`, `gap 10px` |
| Ikon | Kotak 26px, radius `--r-sm`, latar permukaan status, SVG 13px |
| Teks | `--text-meta`, `--ink-2`, kata kunci `<b>` `--ink` |
| Metadata | Baris kedua: pill status + keterangan singkat (`hari ini`, `perlu 5 menit`, `12 lowongan`) |

Wajib `overflow-wrap: anywhere` agar teks panjang turun ke bawah, tidak menabrak ikon. Maksimal tiga kartu per panel.

### 4.13 SkillPanel

Panel profil di right rail. Menampilkan data akun dan **daftar skill terkonfirmasi** (R-06-01).

| Bagian | Aturan |
|---|---|
| Avatar | 42×42px, radius 11px |
| Nama | `--text-label`, bobot 600 |
| Peran | `--text-micro`, `--ink-3` |
| Judul daftar | `--text-micro` uppercase `--ink-3`, tracking `.05em` |
| Skill | `SkillTag` yang sudah dikonfirmasi |
| Aksi | Tombol `Kelola skill dari CV` selebar panel |
| Keterangan | "Dipakai untuk menghitung rekomendasi" |

**Larangan:** jangan menampilkan persentase "kelengkapan profil". PRD tidak mendefinisikan apa itu profil lengkap, sehingga angkanya karangan. Tampilkan daftar skill yang benar-benar ada.

### 4.14 SkeletonCard

State loading untuk daftar lowongan (R-04-06). **Tidak boleh ada teks palsu** — hanya blok abu.

| Bagian | Dimensi |
|---|---|
| Baris perusahaan | 96×12px |
| Badge kanan | 54×16px |
| Judul | Tinggi 15px, lebar 72% |
| Deskripsi | Dua baris, tinggi 11px dan 34px |
| Tag | Tiga blok 52px, 52px, 38px, tinggi 20px |
| Gaji | 118×15px |

Animasi: `shimmer` 1.4s `--ease-in-out` infinite. Kartu diberi `aria-busy="true"` dan `aria-hidden="true"`.

### 4.15 Toast

Konfirmasi singkat setelah aksi (R-06-08).

| Properti | Aturan |
|---|---|
| Posisi | `fixed`, bawah tengah, `bottom: 24px` |
| Latar | `--action`, teks `#FFFFFF` |
| Radius | `--r-chip` |
| Teks | `--text-label`, bobot 500 |
| Ikon | Centang 13px |
| Animasi | `translateY(12px) → 0` + fade, 200ms |
| Durasi tampil | 2200ms, lalu menghilang |
| Aksesibilitas | `role="status"`, `aria-live="polite"` |

Satu toast pada satu waktu. Memicu ulang sebelum hilang akan mereset timer, bukan menumpuk toast baru.

### 4.16 Button

| Varian | Latar | Teks | Pemakaian |
|---|---|---|---|
| Primary | `--action` | `#FFFFFF` | Aksi utama per layar (maksimal satu) |
| Line | `--sheet` + border `--line-2` | `--ink` | Aksi pendukung |
| Soft | `--sunken` | `--ink` | Aksi di dalam panel |
| Ghost | transparan | `--ink-2` | Aksi dalam kartu |
| Danger | `--danger` | `#FFFFFF` | Hapus data |

| Properti | Nilai |
|---|---|
| Tinggi | 40px |
| Padding | `0 15px` |
| Radius | `--r-chip` |
| Teks | `--text-label`, bobot 600 |

State wajib: default, hover, focus-visible, active (`scale .98`, 90ms), disabled, loading. Tombol `disabled` harus punya alasan yang terlihat di dekatnya — jangan sekadar mengabu-kan tombol tanpa penjelasan.

### 4.17 NavPill

Navigasi header berupa deretan tautan dengan satu item aktif.

- Wadah: `--sunken`, radius `--r-chip`, padding 4px.
- Item: radius `--r-chip`, padding `8px 16px`, `--text-label` bobot 500.
- Item aktif: latar `--action`, teks `#FFFFFF`, `aria-current="page"`.
- Item lain: transparan, `--ink-2`.
- Jumlah item mengikuti peran: publik, pengguna login, admin (R-06-10).
- Harus dapat dijangkau dengan Tab dan menampilkan focus ring.

### 4.18 AlertBanner

| Varian | Latar | Teks | Pemakaian |
|---|---|---|---|
| Info | `--hint-bg` | `#1E40AF` | Informasi netral, mis. "12 lowongan cocok hari ini" |
| Warning | `--warning-bg` | `--amber` | Data terbatas (R-05-11) |
| Error | `--danger-bg` | `--danger-ink` | Kegagalan memuat data |

Radius `--r-md`, padding `12px 13px`, teks `--text-label`, ikon 15px. Satu banner maksimal per halaman. Jangan menduplikasi informasi yang sudah ada di judul bagian.

## 5. Aksesibilitas

Persyaratan minimum sesuai PRD §9.5:

| Aspek | Aturan |
|---|---|
| Kontras teks | Minimal 4.5:1 untuk teks normal, 3:1 untuk teks ≥ 18px tebal |
| Kontras non-teks | Minimal 3:1 untuk ikon fungsional dan focus ring |
| Pasangan yang harus diuji | Lihat Lampiran A. Pasangan abu-di-atas-abu adalah kegagalan paling sering; uji sebelum rilis |
| Target sentuh | Minimal 44×44px untuk semua kontrol ikon |
| Focus | `:focus-visible` wajib terlihat, ring 2px `--blue` dengan offset 2px. Jangan menghapus outline tanpa pengganti |
| Tekan | Semua kontrol memberi feedback `scale(.98)` 90ms |
| Keyboard | Seluruh alur dapat diselesaikan tanpa mouse; urutan Tab mengikuti urutan visual |
| Form | Setiap input punya `<label>` terhubung; pesan error memakai `aria-describedby` |
| Ikon bermakna | Wajib `aria-label`; ikon dekoratif `aria-hidden="true"` |
| Gambar grafik | Sediakan ringkasan teks atau tabel alternatif |
| Motion | Hormati `prefers-reduced-motion`; lihat §3.7 |
| Toast | `role="status"`, `aria-live="polite"` |
| Bahasa | `<html lang="id">` |

## 6. Larangan Eksplisit

Pola berikut muncul di referensi visual namun **tidak boleh** diadopsi karena bertentangan dengan scope produk atau tidak punya data pendukung.

| Pola | Alasan |
|---|---|
| Jumlah pelamar atau proposals pada kartu | Tracker lamaran di luar scope (PRD §4) |
| Status lamaran, tahapan seleksi, "under review" | Sama, di luar scope |
| Panel "Performa", job success rate, proposals sent | Metrik freelancing; tidak ada tabelnya di database (PRD §4) |
| Persentase "kelengkapan profil" | PRD tidak mendefinisikan apa itu profil lengkap |
| Badge kecocokan tanpa alasan | R-07-10 mewajibkan alasan kecocokan |
| Dua pintu masuk AI dengan nama berbeda | KarirLens hanya punya satu `/assistant` (PRD-08) |
| Angka statistik saat sampel kurang dari 5 | R-05-08 dan R-10-13 |
| Nilai enum mentah di layar | Prinsip §2 butir 4 |
| Merah untuk skor rendah | Merah khusus error dan aksi merusak |
| Judul dan meta yang dipotong tanpa ellipsis | Membuat teks terlihat rusak |
| Tombol yang tampak nonaktif padahal aktif | State dan perilaku harus sesuai |
| Pill pada kontrol | Kontrol memakai `--r-chip`; lihat §3.5 |
| Shadow pada kartu saat diam | Border 1px sudah cukup |

## 7. Checklist Review UI

Dipakai saat meninjau setiap halaman sebelum dianggap selesai.

- [ ] Semua warna berasal dari token, tidak ada nilai hex lepas di template.
- [ ] Padding kiri hanya diberikan di `.layout`, tidak berlapis di `.feed`.
- [ ] Tepi kiri kartu, judul halaman, dan isi header berada di satu garis lurus.
- [ ] Tepi kanan rail rata dengan header.
- [ ] Tidak ada `JobCard` yang berbeda urutan anatominya antar halaman.
- [ ] Setiap `SourceBadge` tampil dan benar sesuai sumber data.
- [ ] Deskripsi kartu terpotong tepat dua baris.
- [ ] Semua kontrol memakai `--r-chip`; `--r-full` hanya pada toggle dan progress bar.
- [ ] Setiap kontrol interaktif punya state hover, focus, active, dan disabled.
- [ ] Semua teks lolos kontras minimum; Lampiran A diperiksa ulang bila token berubah.
- [ ] Tidak ada metrik lamaran, performa, atau kelengkapan profil di layar mana pun.
- [ ] `MatchBadge` selalu berpasangan dengan alasan.
- [ ] Setiap angka statistik punya tabel sumber di database.
- [ ] Kondisi kosong memakai `EmptyState`, bukan area kosong.
- [ ] Layout tidak rusak pada 360px, 768px, 1024px, dan 1280px.
- [ ] Halaman dapat diselesaikan dengan keyboard saja.
- [ ] Animasi tidak berjalan saat `prefers-reduced-motion: reduce`.
- [ ] Semua teks antarmuka berbahasa Indonesia dan tidak menampilkan nilai mentah database.

## 8. Catatan Implementasi

- Bootstrap dipakai sebagai fondasi grid dan utilitas; token di §3 dijadikan CSS custom property agar dapat menimpa tema bawaan.
- Satu berkas `static/css/tokens.css` untuk token, `static/css/components.css` untuk komponen. Jangan menulis gaya inline di template.
- Chart.js dan AutoAnimate disimpan lokal di `static/vendor/` agar demo tidak bergantung jaringan.
- Font: `@import` Inter dari Google Fonts dengan `display=swap`, dan biarkan SF Pro dipakai lebih dulu di perangkat Apple.
- Halaman contoh komponen (`/styleguide`, hanya untuk pengembangan) membantu memverifikasi state tanpa harus membuka setiap fitur.
- Setiap komponen baru wajib ditambahkan ke §4 sebelum dipakai di halaman.
- Bila token berubah, jalankan ulang uji kontras dan perbarui Lampiran A.

## 9. Di Luar Scope

- Perubahan requirement produk; dokumen ini tidak boleh menambah fitur.
- Materi marketing, landing page, dan aset ilustrasi.
- Dark mode. Bila ditambahkan nanti, token §3.1 diberi varian tema tanpa mengubah nama peran.
- Redesign di luar halaman yang tercantum pada PRD per task.
- Animasi dekoratif seperti parallax dan scroll-reveal.

## 10. Lampiran A — Audit Kontras

Nilai dihitung dengan rumus kontras WCAG 2.x. Ambang: 4.5:1 untuk teks normal, 3:1 untuk teks besar dan elemen non-teks.

| Pasangan | Rasio | Status |
|---|---|---|
| `--ink` di `--sheet` | 18.76:1 | Lulus AA normal |
| `--ink-2` di `--sheet` | 8.02:1 | Lulus AA normal |
| `--ink-3` di `--sheet` | 6.13:1 | Lulus AA normal |
| `--ink-3` di `--sunken` | 5.62:1 | Lulus AA normal |
| `--ink-3` di `--sunken-2` | 5.88:1 | Lulus AA normal |
| `#FFFFFF` di `--action` | 17.81:1 | Lulus AA normal |
| `--green` di `--success-bg` | 4.55:1 | Lulus AA normal |
| `--amber` di `--warning-bg` | 4.62:1 | Lulus AA normal |
| `--blue` di `--info-bg` | 4.65:1 | Lulus AA normal |
| `--blue` di `--match-mid-bg` | 4.64:1 | Lulus AA normal |
| `--violet` di `--match-high-bg` | 6.25:1 | Lulus AA normal |
| `--danger-ink` di `--danger-bg` | 5.91:1 | Lulus AA normal |
| `#1E40AF` di `--hint-bg` | 8.03:1 | Lulus AA normal |
| `--source-dealls` di `--sunken` | 3.75:1 | Lulus non-teks |
| `--source-kalibrr` di `--sunken` | 3.45:1 | Lulus non-teks |
| `--source-remotive` di `--sunken` | 4.60:1 | Lulus AA normal |
| `--line` di `--sheet` | 1.14:1 | **Belum lolos** non-teks |
| `--line-2` di `--sheet` | 1.27:1 | **Belum lolos** non-teks |

**Catatan pada `--line-2`.** Batas kontrol interaktif seharusnya ≥ 3:1. Nilai 1.27:1 dipertahankan karena border tipis inilah yang membuat antarmuka terasa ringan dan sesuai referensi. Batas kontrol ditegaskan oleh label teks, state hover (`--sunken`), dan focus ring `--blue` 2px. Ini **trade-off sadar**, bukan kelalaian. Bila audit aksesibilitas formal dilakukan, naikkan `--line-2` ke `#8B919C` (3.17:1) dan terima bahwa chip akan terlihat sedikit lebih berkotak.

Nilai pada tabel ini berasal dari versi token di §3.1. Setiap perubahan warna wajib disertai pembaruan tabel.

## 11. Riwayat Dokumen

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 18 November 2026 | Versi awal: token warna, tipografi, spacing, radius, inventaris 18 komponen, aturan aksesibilitas, larangan pola tracker lamaran, dan checklist review UI. |
| 1.1 | 18 November 2026 | Menambah §3.6 Motion. Radius diubah: kontrol memakai `--radius-chip`, `--radius-full` hanya untuk toggle dan progress bar. |
| 2.0 | 18 November 2026 | Diselaraskan dengan pratinjau yang sudah divalidasi. Warna diperbarui ke nilai yang lolos audit (`--ink`, `--ink-2`, `--ink-3`, `--green`, `--amber`, warna sumber) dan ditambah permukaan status serta `--sunken-2`. Ditambah §3.4 Sistem Padding dan Lebar: shell fullscreen, padding kiri hanya di `.layout`, feed mengambil sisa ruang. Tipografi diperbarui ke ukuran nyata dan stack SF Pro + Inter. Elevation diubah: kartu tanpa shadow saat diam. Breakpoint disesuaikan. Komponen baru: `MetricCell`, `InsightCard`, `SkillPanel`, `SkeletonCard`, `Toast`, `SortControl`. Ditambah Lampiran A audit kontras. Ditambah larangan metrik performa dan persentase kelengkapan profil. |
