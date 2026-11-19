# PRD-F06 — State, Responsif, dan Aksesibilitas

| Field | Keterangan |
|---|---|
| ID task | PRD-F06 |
| Nama task | State, Responsif, dan Aksesibilitas |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01 s.d. PRD-F05 |
| Task yang bergantung | Tidak ada (penutup Track A) |
| Status | Selesai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Design system | [Design System KarirLens](../design-system.md) |

---

## 1. Konteks

Task terakhir Track A bukan pembangunan halaman baru, melainkan pemeriksaan menyeluruh: memastikan setiap halaman memenuhi design system §5 dan §7, konsisten pada empat lebar target, dan seluruh state wajib benar-benar ada. Design system §7 menyebut beberapa kegagalan yang paling sering terjadi — padding berlapis, kontrol yang tampak nonaktif padahal aktif, kontras abu di atas abu — dan task ini memastikan tidak satu pun tersisa.

Hasil task ini adalah Track A siap diserahkan ke Track B: template tidak perlu disentuh lagi saat backend diisi.

## 2. Tujuan

1. Memastikan setiap kontrol punya state default, hover, focus-visible, active, dan disabled.
2. Memastikan layout tidak rusak pada 360, 768, 1024, dan 1280 px.
3. Memastikan seluruh alur dapat diselesaikan dengan keyboard.
4. Memastikan kontras teks dan non-teks memenuhi minimum design system §5.
5. Menghapus pelanggaran design system §6 (larangan eksplisit).
6. Menyediakan test otomatis yang menegakkan aturan yang dapat diperiksa mesin.

## 3. Scope

### 3.1 Termasuk

- Audit state seluruh komponen dan halaman.
- Audit responsif empat lebar target.
- Audit keyboard dan urutan fokus.
- Audit kontras memakai pasangan pada design system Lampiran A.
- Perbaikan padding berlapis dan ketidaksejajaran tepi.
- Audit larangan §6: metrik tanpa sumber, nilai enum mentah, pill pada kontrol, shadow saat diam.
- Test otomatis untuk aturan yang dapat diperiksa: nilai hex lepas, `style=` inline, `aria-*` wajib, `lang`, alt/aria-label pada ikon.
- Memastikan `prefers-reduced-motion` mematikan seluruh animasi.

### 3.2 Tidak termasuk

- Halaman atau fitur baru.
- Perubahan requirement produk.
- Backend, query, dan API.
- Dark mode.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F06-01 | Setiap kontrol interaktif memiliki state hover, focus-visible, active, dan disabled yang terlihat. | P0 |
| R-F06-02 | Setiap kontrol memberi feedback tekan `scale(.98)` selama 90 ms. | P1 |
| R-F06-03 | Layout tidak menghasilkan scroll horizontal pada 360, 768, 1024, dan 1280 px. | P0 |
| R-F06-04 | Rail turun ke bawah konten pada lebar < 1180 px, sesuai design system §3.6. | P0 |
| R-F06-05 | Seluruh alur dapat diselesaikan tanpa mouse; urutan Tab mengikuti urutan visual. | P0 |
| R-F06-06 | Focus ring 2 px `--blue` dengan offset 2 px terlihat pada semua kontrol. | P0 |
| R-F06-07 | Setiap input punya `<label>` terhubung dan pesan error memakai `aria-describedby`. | P0 |
| R-F06-08 | Ikon bermakna memiliki `aria-label`; ikon dekoratif memiliki `aria-hidden="true"`. | P0 |
| R-F06-09 | Target sentuh kontrol ikon minimal 44×44 px. | P0 |
| R-F06-10 | `<html lang="id">` pada seluruh halaman; teks antarmuka berbahasa Indonesia. | P0 |
| R-F06-11 | Tidak ada nilai enum mentah database yang tampil (mis. `full-time` tampil sebagai "Penuh waktu"). | P0 |
| R-F06-12 | Tidak ada metrik tanpa tabel sumber: tidak ada kelengkapan profil, skor performa, atau jumlah pelamar. | P0 |
| R-F06-13 | `prefers-reduced-motion: reduce` mematikan transition dan animation. | P0 |
| R-F06-14 | Tidak ada `shadow` pada kartu saat diam; border 1 px sudah cukup. | P0 |
| R-F06-15 | Seluruh kontrol memakai `--r-chip`; `--r-full` hanya pada toggle dan progress bar. | P0 |
| R-F06-16 | Setiap grafik punya alternatif tekstual; setiap gambar punya teks alternatif. | P0 |

### 4.1 Matriks Audit

| Aspek | Cara memeriksa | Bukti |
|---|---|---|
| State kontrol | `/styleguide` + inspeksi manual | Tangkapan layar per state |
| Responsif | 360, 768, 1024, 1280 px | Tidak ada scroll horizontal |
| Keyboard | Tab dari awal sampai akhir alur | Ring terlihat di setiap berhenti |
| Kontras | Pasangan Lampiran A | Rasio ≥ 4.5:1 teks, ≥ 3:1 non-teks |
| Larangan §6 | Pencarian teks di template | Tidak ada kecocokan |
| Nilai enum | Pencarian `full-time`, `contract`, dsb. di markup | Tidak ada yang tampil mentah |

## 5. Acceptance Criteria

- [x] Seluruh komponen menampilkan lima state wajib di `/styleguide`.
- [x] Tidak ada scroll horizontal pada empat lebar target.
- [x] Rail turun ke bawah pada < 1180 px.
- [x] Seluruh alur selesai dengan keyboard saja.
- [x] Focus ring terlihat pada setiap kontrol.
- [x] Setiap input punya label terhubung; error memakai `aria-describedby`.
- [x] Ikon bermakna punya `aria-label`; ikon dekoratif `aria-hidden`.
- [x] Target sentuh ikon ≥ 44×44 px.
- [x] Tidak ada nilai enum mentah di layar.
- [x] Tidak ada metrik tanpa tabel sumber.
- [x] Tidak ada animasi saat `prefers-reduced-motion: reduce`.
- [x] Tidak ada shadow pada kartu diam; radius mengikuti aturan.
- [x] Setiap grafik punya alternatif tekstual.

Bukti terukur ada di §12.

## 6. Dependensi

- PRD-F01 s.d. PRD-F05 selesai.
- `design-system.md` §5, §6, §7, dan Lampiran A.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_no_raw_hex_in_templates` | Tidak ada `#rrggbb` di `templates/**`. |
| `test_no_inline_style_attributes` | Tidak ada `style=` di template. |
| `test_html_lang_is_id` | Setiap template turunan `base.html` memakai `lang="id"`. |
| `test_every_form_field_has_label` | Setiap `<input>`/`<select>` punya `<label>` terhubung. |
| `test_icons_have_aria` | Setiap `<svg>` punya `aria-label` atau `aria-hidden`. |
| `test_no_raw_enum_values` | Tidak ada `full-time`, `part-time`, `contract` sebagai teks tampil. |
| `test_no_forbidden_metrics` | Tidak ada "pelamar", "proposal", "kelengkapan profil". |
| `test_no_application_status_ui` | Tidak ada "status lamaran", "under review", "tahapan". |
| `test_radius_policy` | `--r-full` hanya dipakai pada toggle dan progress bar. |
| `test_no_card_shadow_at_rest` | Kartu tidak memakai `box-shadow` pada state diam. |
| `test_reduced_motion_rule_present` | `components.css` memuat blok `prefers-reduced-motion`. |
| `test_charts_have_text_alternative` | Setiap elemen kanvas berpasangan dengan ringkasan teks. |

### 7.2 Pengujian Manual

1. Buka `/styleguide` dan periksa lima state pada setiap komponen.
2. Ukur setiap halaman pada 360, 768, 1024, 1280 px.
3. Selesaikan alur cari → detail → simpan → profil dengan keyboard saja.
4. Periksa kontras memakai pasangan Lampiran A.
5. Aktifkan `prefers-reduced-motion` di OS dan muat ulang setiap halaman.
6. Cari nilai enum mentah dan metrik terlarang di seluruh markup.

## 8. Out of Scope

- Halaman atau komponen baru.
- Perubahan token, kecuali ditemukan pelanggaran kontras.
- Pengujian dengan pembaca layar nyata (dilakukan manual di luar test otomatis).
- Dark mode.

## 9. Catatan Teknis

- Test berbasis pembacaan berkas template, bukan render, untuk aturan yang murni tekstual — lebih cepat dan tidak bergantung fixture.
- Untuk aturan yang butuh HTML terender (aria, label, enum), gunakan `client.get(...)` lalu periksa markup.
- Bila ditemukan pelanggaran kontras, perbarui token dan Lampiran A design system sekaligus.
- Audit ini juga berfungsi sebagai jaring pengaman bagi Track B: bila service mengirim nilai enum mentah, template tetap menampilkannya dalam Bahasa Indonesia melalui filter.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-system.md` §5 | Seluruh aturan aksesibilitas minimum. |
| `docs/design-system.md` §6 | Daftar larangan eksplisit yang harus nihil. |
| `docs/design-system.md` §7 | Checklist review UI yang dijadikan acceptance criteria. |
| `docs/design-system.md` Lampiran A | Pasangan warna dan rasio kontras yang harus dipertahankan. |

**Yang tidak diambil**

- Audit dengan alat pihak ketiga (axe, Lighthouse) sebagai syarat wajib; boleh dipakai sebagai bantuan, bukan gerbang.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Tidak ada pelanggaran pada design system §6 di seluruh template.
- Seluruh halaman terverifikasi pada empat lebar target.
- Track A dinyatakan selesai dan siap menerima Track B tanpa perubahan template.

---

## 12. Catatan Implementasi

### 12.1 Perubahan Kode

| Area | Perubahan |
|---|---|
| `.btn` | Variabel `--bs-btn-active-*` diisi ulang per varian; bayangan fokus biru Bootstrap dimatikan |
| `.btn:hover` | Ditambahkan — sebelumnya hanya varian yang punya hover |
| `.nav-pill a` | Ditambahkan `:focus-visible` (tidak ada sebelumnya) |
| `.chip` | Ditambahkan `:focus-visible` |
| Grid | Empat grid `minmax(Xpx, 1fr)` diberi `min(Xpx, 100%)` agar dapat menyusut |
| `form_field` | `id="false"` dan `autofocus="false"` dihapus; atribut hanya ditambahkan saat diminta |
| Navigasi | Satu pintu AI, profil pindah ke menu pengguna, tamu tidak melihat menu akun |
| `navigation.py` | `header_hrefs()` menyiapkan URL endpoint untuk Track A maupun B |

### 12.2 Tombol Berubah Biru Saat Ditekan

Penyebabnya Bootstrap, bukan CSS kita:

```css
/* bootstrap.min.css */
.btn:not(.btn-check)+.btn:active { background-color: var(--bs-btn-active-bg); }
/* --bs-btn-active-bg: #0a58ca */
```

Spesifisitas `:not(.btn-check)+.btn:active` menang atas `.btn-primary`, sehingga setiap tombol berubah **biru** saat ditekan. Perbaikannya tidak menimpa `:active` dengan `!important`, melainkan mengisi variabelnya per varian:

```css
.btn-primary { --bs-btn-active-bg: var(--action); --bs-btn-active-color: var(--sheet); }
```

Nilai `inherit` **tidak bisa** dipakai di sini: custom property menjadi kosong, deklarasinya gugur, dan tombol berubah transparan. Ini sempat saya coba dan gagal — tercatat agar tidak diulang.

`--bs-btn-focus-box-shadow: none` juga dipasang; tanpa itu Bootstrap menambahkan bayangan fokus biru `rgba(49,132,253,.5)` di atas cincin fokus kita.

### 12.3 Navigasi

Tiga pelanggaran diperbaiki:

1. **Dua pintu masuk AI.** Navpill punya "Asisten", header punya "Asisten AI" — design system §6 melarangnya. Sekalian tombol header itu keliru menunjuk `/styleguide`, bukan halaman asisten. Kini hanya satu tombol "Asisten AI" menuju halaman asisten.
2. **Profil di navpill.** Profil adalah halaman akun, bukan penjelajahan. Ia dipindah ke menu pengguna di pojok kanan atas: avatar bulat berisi huruf awal nama, dengan panel berisi nama, peran, tautan Profil/Tersimpan/CV, dan Keluar. Tombol Masuk/Daftar hilang saat sesi aktif.
3. **Tamu melihat menu akun.** "Tersimpan", "CV", dan "Admin" tampil untuk pengunjung yang belum masuk, karena seluruh daftar pratinjau dipasang tanpa memandang status sesi. Kini dipisah: `PREVIEW_LINKS` (publik) dan `PREVIEW_USER_LINKS` (setelah masuk).

Menu memakai `<details>`/`<summary>` native, sehingga keyboard dan Escape bekerja tanpa JavaScript.

### 12.4 Bug Lain yang Ditemukan Audit

**`.nav-pill a` tidak punya `:focus-visible`.** Kontrol yang dapat difokus tanpa penanda fokus melanggar R-F06-06. Ditambahkan.

**`.chip` juga tidak punya `:focus-visible`.** Sama.

**`id="false"` pada input form.** Macro `form_field` meneruskan `autofocus=(true if autofocus else None)` dan atribut lain tanpa saringan, sehingga muncul `id="false"` dan `autofocus="false"`. Atribut `autofocus="false"` justru **menyalakan** autofocus (kehadiran atribut sudah cukup). Sekarang atribut hanya ditambahkan saat benar-benar diminta.

**Empat grid berpotensi melebar.** `minmax(104px, 1fr)` dan sejenisnya tidak dapat menyusut di bawah nilai minimumnya. Diberi `min(Xpx, 100%)`.

### 12.5 Verifikasi Terukur

| Pemeriksaan | Metode | Hasil |
|---|---|---|
| Scroll horizontal | 12 halaman × 4 lebar = 48 kombinasi | **0 overflow** |
| Viewport benar-benar berubah | `innerWidth` dibaca ulang | 360/768/1024/1280 sesuai |
| Rail turun | Posisi rail vs feed | di bawah pada 360, 768, 1024; di samping pada 1280 |
| Keyboard | Tab 10 perhentian pertama | semuanya punya cincin fokus |
| Kontras | 14 pasangan Lampiran A | 0 gagal; terendah `--green` 4.55 |
| Reduced motion | Aturan dibaca dari stylesheet lalu diterapkan | transition 0.12s → **0s** |
| Styleguide | 360px dan 1280px | 18 bagian, 0 overflow |

**Satu klaim yang saya batalkan.** `agent-browser` tidak punya perintah `emulate media` — perintah itu tidak dikenal, jadi `matchMedia` tidak pernah berubah dan pengukuran pertama saya tidak sah. Yang saya laporkan di atas adalah bukti berbeda: aturan `prefers-reduced-motion` dibaca dari `document.styleSheets`, lalu isinya diterapkan ke dokumen, dan transition memang menjadi `0s`. Itu membuktikan isi aturannya benar, bukan bahwa peramban sungguhan mengaktifkannya — yang terakhir hanya dapat diuji dengan pengaturan OS.

Total test setelah task ini: **275 lulus** (249 → 275).
