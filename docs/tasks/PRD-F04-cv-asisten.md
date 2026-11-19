# PRD-F04 — CV dan Asisten AI (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F04 |
| Nama task | CV dan Asisten AI |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01, PRD-F02 |
| Task yang bergantung | PRD-F06 |
| Status | Belum dimulai |
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

- [ ] `/cv` dapat dipakai dengan keyboard saja sampai konfirmasi skill.
- [ ] Batas 5 MB dan tipe berkas dijelaskan sebelum unggah.
- [ ] Berkas tipe salah atau terlalu besar mendapat pesan jelas.
- [ ] Pratinjau skill menampilkan semua kandidat terpilih secara bawaan.
- [ ] Tombol simpan disabled sampai ada skill dipilih.
- [ ] Halaman menyatakan berkas dan teks CV tidak disimpan.
- [ ] Pengguna tanpa skill terkonfirmasi mendapat arahan jelas.
- [ ] Rekomendasi memakai `JobCard` + `MatchBadge` + alasan.
- [ ] Skor rendah tidak berwarna merah.
- [ ] `/assistant` mengirim pertanyaan dan menampilkan jawaban dalam sesi berjalan.
- [ ] Indikator memproses tampil dan tombol disabled selama permintaan.
- [ ] Galat jaringan tampil sebagai banner ramah tanpa detail internal.
- [ ] Tautan sumber yang dikutip asisten dapat diklik.
- [ ] Tidak ada UI yang menyiratkan penyimpanan CV.

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
