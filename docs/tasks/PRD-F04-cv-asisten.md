# PRD-F04 — CV dan Asisten AI (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F04 |
| Nama task | CV dan Asisten AI |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01, PRD-F02 |
| Task yang bergantung | PRD-F06 |
| Status | Selesai (Track A, fixture) |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Backend pasangan | [PRD-07](./PRD-07-cv-rekomendasi.md), [PRD-08](./PRD-08-asisten-ai.md) |
| Design system | [Design System KarirLens](../design-system.md) |

---

## 1. Konteks

Dua halaman ini adalah fitur paling personal: unggah CV dengan konfirmasi skill, dan asisten AI. Keduanya perlu rancangan tampilan yang jelas sebelum logika ekstraksi dan pemanggilan LLM ditulis, karena bentuk alur (pratinjau → konfirmasi → rekomendasi) menentukan bentuk data yang dikembalikan service.

Task ini membangun seluruh tampilan `/cv` dan `/assistant`, termasuk tampilan rekomendasi. Ekstraksi CV, pencocokan kamus, skor rekomendasi, dan panggilan DeepSeek dikerjakan pada PRD-07 dan PRD-08.

## 2. Tujuan

1. Membangun alur `/cv`: unggah, pratinjau skill, konfirmasi, rekomendasi.
2. Menampilkan status unggah dan validasi berkas yang jelas di sisi klien.
3. Membangun `/assistant`: antarmuka percakapan sederhana.
4. Menampilkan rekomendasi memakai `JobCard` + `MatchBadge` beserta alasan.
5. Menetapkan kontrak template untuk PRD-07 dan PRD-08.

## 3. Scope

### 3.1 Termasuk

- `/cv`: drop zone, validasi tipe dan ukuran di sisi klien, progres unggah, pratinjau skill, konfirmasi, daftar rekomendasi.
- `/assistant`: area pesan, form pertanyaan, indikator memproses, penanganan galat jaringan.
- Partial `match_badge`, `upload_zone`, `skill_confirm_list`, `chat_message`, `alert_banner` varian data terbatas.
- Pesan jelas untuk pengguna tanpa skill terkonfirmasi.
- Tampilan "data terbatas" saat rekomendasi belum dapat dihitung.

### 3.2 Tidak termasuk

- Ekstraksi teks PDF/DOCX dan kamus skill (PRD-07).
- Panggilan AI fallback untuk skill ambigu (PRD-07).
- Skor dan alasan rekomendasi di sisi server (PRD-07).
- Integrasi DeepSeek, penyusunan konteks, rate limit (PRD-08).
- Penyimpanan berkas atau teks CV dalam bentuk apa pun.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F04-01 | `/cv` menyediakan drop zone yang dapat dipakai dengan keyboard, dengan atribut `accept` untuk PDF dan DOCX. | P0 |
| R-F04-02 | Ukuran maksimum 5 MB ditampilkan di dekat kontrol unggah sebelum berkas dipilih. | P0 |
| R-F04-03 | Berkas dengan tipe salah atau melebihi batas ditolak dengan pesan jelas di sisi klien. | P0 |
| R-F04-04 | Pratinjau skill menampilkan setiap kandidat sebagai `SkillTag` yang dapat dipilih, dengan semua terpilih sebagai bawaan. | P0 |
| R-F04-05 | Pengguna harus mengonfirmasi sebelum skill disimpan; tombol simpan disabled sampai ada pilihan. | P0 |
| R-F04-06 | Halaman menjelaskan bahwa berkas dan teks CV tidak disimpan. | P0 |
| R-F04-07 | Pengguna tanpa skill terkonfirmasi melihat arahan jelas, bukan rekomendasi kosong. | P0 |
| R-F04-08 | Rekomendasi memakai `JobCard` dengan `MatchBadge`, dan setiap badge disertai alasan. | P0 |
| R-F04-09 | Skor rendah tidak memakai warna merah. | P0 |
| R-F04-10 | `/assistant` menyediakan area pesan dengan `aria-live="polite"`, form pertanyaan, dan tombol kirim. | P0 |
| R-F04-11 | Selama permintaan berjalan, tampil indikator memproses dan tombol kirim disabled. | P0 |
| R-F04-12 | Galat jaringan atau timeout ditampilkan sebagai `AlertBanner` yang ramah, tanpa detail internal. | P0 |
| R-F04-13 | Asisten menampilkan sumber/tautan lowongan yang dikutip, bila ada. | P0 |
| R-F04-14 | Tidak ada tampilan riwayat percakapan lintas sesi; riwayat hanya ada di sesi berjalan. | P0 |
| R-F04-15 | Tidak ada UI yang menyiratkan CV disimpan, ditampilkan ke admin, atau dapat dibuka kembali. | P0 |

### 4.1 Kontrak Template

**`cv/index.html`** menerima:

| Variabel | Tipe | Keterangan |
|---|---|---|
| `suggested_skills` | `list[str]` | Kandidat hasil ekstraksi; kosong sebelum unggah |
| `confirmed_skills` | `list[dict]` | `{id, skill, source}` |
| `recommendations` | `list[dict]` | Bentuk `job` PRD-F01 §4.2 dengan `match` terisi |
| `state` | `str` | `idle` \| `extracted` \| `no_skills` \| `ready` |

**`assistant/index.html`** menerima `messages` (`list[dict]` dengan `{role, text, sources}`) dan `error` (opsional).

**`POST /api/cv/extract`** mengembalikan `{"data": {"skills": ["python"], "ambiguous": []}}`.
**`POST /api/assistant`** mengembalikan `{"data": {"reply": "...", "sources": []}}`.

Bentuk respons ini adalah kontrak yang harus dipenuhi PRD-07 dan PRD-08.

## 5. Acceptance Criteria

- [x] `/cv` dapat dipakai dengan keyboard saja sampai konfirmasi skill.
- [x] Batas 5 MB dan tipe berkas dijelaskan sebelum unggah.
- [x] Berkas tipe salah atau terlalu besar mendapat pesan jelas.
- [x] Pratinjau skill menampilkan semua kandidat terpilih secara bawaan.
- [x] Tombol simpan disabled sampai ada skill dipilih.
- [x] Halaman menyatakan berkas dan teks CV tidak disimpan.
- [x] Pengguna tanpa skill terkonfirmasi mendapat arahan jelas.
- [x] Rekomendasi memakai `JobCard` + `MatchBadge` + alasan.
- [x] Skor rendah tidak berwarna merah.
- [x] `/assistant` mengirim pertanyaan dan menampilkan jawaban dalam sesi berjalan.
- [x] Indikator memproses tampil dan tombol disabled selama permintaan.
- [x] Galat jaringan tampil sebagai banner ramah tanpa detail internal.
- [x] Tautan sumber yang dikutip asisten dapat diklik.
- [x] Tidak ada UI yang menyiratkan penyimpanan CV.

Catatan kejujuran: pada Track A halaman berada di `/preview/cv` dan
`/preview/assistant`. Endpoint `/api/cv/extract` dan `/api/assistant` yang
disebut §4.1 **belum ada**; tiruannya hidup di `/preview/api/...` agar tidak
pernah terdaftar di produksi. PRD-07 dan PRD-08 yang mengisi versi aslinya.

## 6. Dependensi

- PRD-F01 (komponen, shell, preview blueprint).
- PRD-F02 (`JobCard` dan `MatchBadge`).
- PRD-01 (sesi pengguna, `login_required`).
- Fixture `tests/fixtures/ui/cv.json`, `assistant.json`.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_cv_upload_accept_attr` | Drop zone membatasi tipe PDF/DOCX. |
| `test_cv_size_hint_present` | Batas 5 MB tampil sebelum unggah. |
| `test_cv_skills_preselected` | Semua kandidat terpilih secara bawaan. |
| `test_cv_confirm_disabled_without_selection` | Tombol simpan disabled saat tidak ada pilihan. |
| `test_cv_states_rendered` | Empat `state` merender blok yang benar. |
| `test_recommendation_has_reason` | Setiap `MatchBadge` diikuti alasan. |
| `test_low_score_not_danger_color` | Kelas warna skor rendah bukan `danger`. |
| `test_assistant_live_region` | Area pesan memakai `aria-live="polite"`. |
| `test_assistant_error_banner` | Galat merender `AlertBanner` tanpa detail internal. |
| `test_no_cv_persistence_ui` | Tidak ada teks yang menyiratkan CV disimpan. |

### 7.2 Pengujian Manual

1. Unggah PDF valid, periksa pratinjau skill dan konfirmasi.
2. Coba berkas .txt dan berkas > 5 MB; periksa pesan.
3. Batalkan semua pilihan skill; pastikan tombol simpan disabled.
4. Buka halaman tanpa skill terkonfirmasi dan periksa arahan.
5. Kirim pertanyaan asisten dan periksa indikator memproses.
6. Simulasikan galat jaringan dan periksa banner.
7. Periksa tautan sumber pada jawaban asisten.

## 8. Out of Scope

- Ekstraksi teks dan pencocokan kamus (PRD-07).
- Skor dan alasan rekomendasi (PRD-07).
- Panggilan DeepSeek, konteks, dan rate limit (PRD-08).
- Riwayat percakapan lintas sesi.
- Penilaian kualitas CV atau saran penulisan CV.

## 9. Catatan Teknis

- Validasi tipe dan ukuran di sisi klien hanya untuk umpan balik cepat; validasi otoritatif tetap di server (PRD-07).
- Unggah memakai `fetch` dengan `FormData`; jangan memakai form multipart biasa agar progres dan galat dapat ditangani tanpa memuat ulang halaman.
- Pertanyaan asisten dikirim ke `/api/assistant`; pada Track A, jalur ini dilayani preview dengan respons tiruan.
- Riwayat pesan disimpan di memori halaman (array JavaScript), tidak di `localStorage`.
- `MatchBadge` tanpa alasan dilarang design system §6.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-preview.html` baris 806–835 | `MatchBadge` dengan persentase dan baris alasan kecocokan. |
| `docs/design-system.md` §4.5 `MatchBadge`, §4.14 `SkeletonCard`, §4.18 `AlertBanner` | Anatomi dan state komponen yang dipakai kedua halaman. |
| BengkelBot — `static/js/chat.js`, `templates/chat.html` | Pola UI chat: pasangan pesan, indikator memproses, penanganan galat jaringan tanpa memuat ulang. |
| BengkelBot — `app.py` `galat(pesan, kode)` | Bentuk respons galat seragam yang ditampilkan sebagai banner. |

**Yang tidak diambil**

- Penyimpanan riwayat chat permanen (PRD-08 R-08-11 menyatakan tidak disimpan).
- Statistik pertanyaan tak dikenali di UI pengguna.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- `/cv` dan `/assistant` dapat ditinjau di browser dengan fixture.
- Kontrak template dan bentuk respons API pada §4.1 tertulis serta dipakai PRD-07 dan PRD-08.

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `templates/cv/index.html` | Empat state, zona unggah, konfirmasi skill, rekomendasi |
| `templates/assistant/index.html` | Percakapan, saran, form, indikator memproses |
| `templates/components/upload_zone.html` | Drop zone + input berkas yang dapat difokus keyboard |
| `templates/components/skill_confirm_list.html` | Checklist kandidat, tombol konfirmasi, daftar ambigu |
| `templates/components/chat_message.html` | Satu pesan beserta sumber yang dikutip |
| `templates/base.html` | `<meta name="csrf-token">` untuk permintaan AJAX |
| `app/preview/routes.py` | Route `cv`, `assistant`, dan dua endpoint API tiruan |
| `static/css/components.css` | Upload, skill confirm, chat, perbaikan nav |
| `tests/fixtures/ui/cv.json`, `assistant.json` | Data contoh kedua halaman |
| `tests/unit/test_cv_assistant_ui.py` | 24 test untuk §7.1 |

### 12.2 Keputusan

**Input berkas disembunyikan secara visual, bukan `display: none`.** `display: none` membuat input tidak dapat difokus keyboard, sehingga alur unggah mustahil diselesaikan tanpa mouse (R-F04-01). Pola yang dipakai: input diposisikan 1×1px dengan `clip`, label berperan sebagai tombol, dan `:focus-visible` pada input memindahkan cincin fokus ke label.

**`accept` tidak cukup, jadi validasi diulang di JavaScript.** `accept` hanya menyaring dialog berkas; berkas yang dijatuhkan lewat drag-and-drop tidak melewatinya. R-F04-03 tetap dipenuhi karena tipe dan ukuran diperiksa di `change` dan `drop`.

**Semua kandidat skill terpilih sebagai bawaan**, termasuk yang sudah tersimpan (R-F04-04). Pilihan disimpan di checkbox asli, bukan kelas, agar dapat dioperasikan keyboard dan dibaca pembaca layar.

**Jawaban asisten disisipkan lewat `textContent`, bukan `innerHTML`.** Teks berasal dari server; menyisipkannya sebagai HTML membuka celah XSS. Tautan sumber dibangun dengan `createElement`.

**Pesan galat jaringan tidak menyebut kode status.** R-F04-12 meminta pesan ramah; `catch` hanya menampilkan "Maaf, jawaban gagal diambil" tanpa `HTTP 500` atau nama exception.

### 12.3 Bug yang Ditemukan Lewat Audit Browser

**Permintaan AJAX ditolak 400 oleh CSRF.** CSRF aktif di development; hanya konfigurasi `testing` yang mematikannya. Test otomatis lolos karena test client tidak memakai CSRF, sementara browser sungguhan gagal — jawaban asisten tidak pernah muncul dan selalu jatuh ke pesan galat. Diperbaiki dengan `<meta name="csrf-token">` di `base.html` dan header `X-CSRFToken` pada kedua `fetch`.

**Halaman melebar 421px pada viewport 360px.** Penyebabnya chip saran asisten: satu kalimat panjang menjadi chip 382px karena `.chip` memakai `white-space: nowrap` dan tidak punya batas lebar. Chip saran sekarang `width: fit-content`, `max-width: 100%`, dan `white-space: normal`.

**Navigasi mendorong halaman melebar.** Setelah menu bertambah menjadi lima, `<nav>` tidak dapat menyusut di dalam header sehingga totalnya 403px. `.top nav` diberi `min-width: 0` dan `overflow-x: auto`, sehingga nav menyusut dan menggulir sendiri di layar sempit alih-alih menyeret halaman.

Ketiganya tidak tertangkap test lama karena test memeriksa markup, bukan hasil render. Empat test baru: `test_fetch_carries_csrf_token`, `test_chat_suggestions_wrap_at_narrow_width`, `test_nav_cannot_widen_page`, dan `test_chat_uses_escaping_not_innerhtml`.

### 12.4 Verifikasi Terukur di Browser

| Pemeriksaan | Hasil |
|---|---|
| Kandidat skill di `?state=extracted` | 7 dari 7 terpilih |
| Tombol konfirmasi saat semua terpilih | aktif (`disabled=false`) |
| Kirim pertanyaan asisten | 200, jawaban muncul, riwayat 3 → 5 pesan |
| Saat berjalan | indikator tampil (`display: flex`), tombol disabled, `aria-busy="true"`, label "Mengirim…" |
| Validasi berkas `.txt` | "Berkas harus PDF atau DOCX. Berkas Anda: text/plain." |
| Validasi berkas 6 MB | "Ukuran berkas 6.0 MB melebihi batas 5 MB." |
| Skor 47% | tier `match-low` (abu-abu), bukan merah |
| `scrollWidth` pada 360px | **360** (sebelum perbaikan: 421) |
| 768px, 1024px, 1280px | tanpa overflow, garis lurus 18/24/32 |

Total test setelah task ini: **223 lulus** (199 → 223).

### 12.5 Jarak Judul ke Subjudul

Kelima halaman dengan pola `h1` + subjudul memakai `.company-sub`, tetapi jaraknya tadinya hanya diberikan pada `.company-head h1` di halaman perusahaan. Empat halaman lain — profil, tersimpan, CV, asisten — tampil dengan jarak **0**, sehingga subjudul menempel pada judul 38px.

Aturan dipindah ke `.company-sub` itu sendiri, jadi satu kelas memberi jarak yang sama di mana pun ia dipakai:

```css
.company-sub { margin: 10px 0 0; }
```

10px, bukan 6px: h1 memakai `line-height: 1.05` pada ukuran 38px, sehingga jarak 6px masih terbaca menempel.

Terukur di browser pada kelima halaman: gap **10px**, konsisten. Dua test menjaga: `test_company_subtitle_has_small_gap` (nilai margin) dan `test_company_sub_used_consistently` (kelima halaman memakai kelas yang sama) — tanpa test kedua, satu halaman bisa kembali menulis paragraf sendiri dan jaraknya jadi 0 lagi.

Total test setelah §12.5: **224 lulus**.
