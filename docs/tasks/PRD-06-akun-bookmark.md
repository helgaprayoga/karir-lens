# PRD-06 — Akun dan Bookmark (Backend)

| Field | Keterangan |
|---|---|
| ID task | PRD-06 |
| Nama task | Akun dan Bookmark (Backend) |
| Track | B — Backend |
| Prioritas | P0 |
| Milestone | M5 Akun dan bookmark (1-2 hari) |
| Dependensi | PRD-01, PRD-04, PRD-F03 |
| Task yang bergantung | PRD-07, PRD-08, PRD-09 |
| Status | Selesai (terbukti di Supabase) |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F03](./PRD-F03-auth-profil.md) |

---

## 1. Konteks

Halaman profil dan lowongan tersimpan sudah dibangun pada PRD-F03, termasuk state kosong, toast, dan tombol simpan pada kartu. Autentikasi dasar (registrasi, login, logout, CSRF, sesi) sudah berfungsi sejak PRD-01.

Task ini mengisi **perilaku di belakang halaman itu**: penyimpanan bookmark yang unik per pengguna, pembacaan skill terkonfirmasi, pengelolaan skill, dan aksi simpan/hapus dari daftar maupun detail. Semua query hidup di `app/profile/repository.py`.

Penting: "simpan lowongan" di KarirLens berarti bookmark, bukan pencatatan lamaran. Tidak ada status lamaran, tahapan lamaran, atau tracker lamaran di aplikasi ini.

Keluaran task ini wajib memenuhi **kontrak template PRD-F03 §4.1**.

## 2. Tujuan

1. Menyediakan operasi bookmark yang unik per pengguna dan lowongan.
2. Menyediakan pembacaan skill terkonfirmasi untuk profil dan rekomendasi.
3. Menyediakan aksi simpan/hapus dari halaman daftar dan detail.
4. Menjaga halaman personal hanya dapat diakses pengguna login.
5. Menyediakan service yang dipakai ulang REST API pada PRD-09.

## 3. Scope

### 3.1 Termasuk

- `app/profile/repository.py`: query dan mutasi `saved_jobs` serta `user_skills`.
- `app/profile/service.py`: aturan keunikan bookmark, pembacaan hanya skill terkonfirmasi, hapus skill.
- Route `/profile` dan `/saved` yang mengisi kontrak PRD-F03 §4.1.
- Endpoint aksi simpan/hapus bookmark dari daftar dan detail.
- Perubahan nama pengguna.
- Indikator jumlah bookmark untuk navigasi.
- Menonaktifkan route preview untuk profil dan tersimpan.

### 3.2 Tidak termasuk

- Markup, CSS, dan JavaScript halaman (selesai pada PRD-F03).
- Upload CV, ekstraksi, dan konfirmasi skill dari CV (PRD-07).
- Rekomendasi dan asisten AI (PRD-07, PRD-08).
- Panel admin (PRD-09).
- Status lamaran atau tracker lamaran (di luar scope produk).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-06-01 | `get_profile(user_id)` mengembalikan `profile` dan `summary` (`skill_count`, `saved_count`) sesuai kontrak PRD-F03 §4.1. | P0 |
| R-06-02 | Pengguna dapat mengubah `name`; email bersifat tetap pada task ini. | P1 |
| R-06-03 | Pengguna dapat menyimpan lowongan sebagai bookmark dari daftar maupun detail lowongan. | P0 |
| R-06-04 | Pengguna dapat menghapus bookmark dari `/saved` dan dari tombol pada kartu/detail. | P0 |
| R-06-05 | Kombinasi `user_id` dan `job_id` unik; menyimpan dua kali tidak membuat baris baru. | P0 |
| R-06-06 | `/saved` hanya menampilkan bookmark; tidak ada status lamaran. | P0 |
| R-06-07 | `/saved` memakai pagination dan kondisi kosong dengan pesan jelas. | P0 |
| R-06-08 | Aksi simpan/hapus memakai POST dengan CSRF dan mengembalikan pengguna ke halaman asal dengan pesan sukses. | P0 |
| R-06-09 | Seluruh route personal memakai `login_required`; pengunjung diarahkan ke login dengan pesan. | P0 |
| R-06-10 | Navigasi menampilkan state berbeda untuk publik, pengguna login, dan admin. | P0 |
| R-06-11 | Simpan bookmark untuk lowongan yang tidak ada menghasilkan error ramah, bukan 500. | P0 |
| R-06-12 | Skill terkonfirmasi hanya dibaca pada task ini; perubahan skill terjadi di PRD-07. | P0 |
| R-06-13 | Tidak ada pengambilan data CV dari panel profil. | P0 |

### 4.1 Aturan Bookmark

| Aturan | Nilai |
|---|---|
| Unik | `(user_id, job_id)` unik di database. |
| Simpan dua kali | Tidak menambah baris; mengembalikan status "sudah tersimpan". |
| Hapus | Menghapus satu baris bookmark pengguna tersebut saja. |
| Konten | Hanya relasi bookmark + timestamp. |
| Status lamaran | Tidak ada. |

### 4.2 Route Task Ini

| Route | Akses | Fungsi |
|---|---|---|
| `/profile` | Pengguna | Profil dan skill terkonfirmasi. |
| `/saved` | Pengguna | Daftar bookmark. |
| `/saved/<job_id>/add` | Pengguna | Simpan bookmark. |
| `/saved/<job_id>/remove` | Pengguna | Hapus bookmark. |

## 5. Acceptance Criteria

- [x] Pengguna login dapat menyimpan dan menghapus bookmark.
- [x] Menyimpan lowongan yang sama dua kali tidak membuat duplikat.
- [x] `list_saved_jobs` mengembalikan `items` dan `meta` sesuai pagination.
- [x] `get_profile` mengembalikan `profile`, `skills`, dan `summary` sesuai kontrak PRD-F03 §4.1.
- [x] Hanya skill `is_confirmed = true` yang dikembalikan ke fitur lain.
- [x] Pengunjung yang membuka route personal diarahkan ke login.
- [x] Aksi POST dilindungi CSRF.
- [x] Keluaran service memenuhi kontrak template PRD-F03 §4.1 tanpa mengubah template.
- [x] Tidak ada status lamaran atau tracker lamaran di database maupun service.

Bukti terukur ada di §12.

## 6. Dependensi

- PRD-01 (autentikasi, sesi, layout, CSRF).
- PRD-04 (service katalog dan detail lowongan).
- PRD-F03 (template profil dan tersimpan, serta kontrak data).
- Tabel `saved_jobs` dan `user_skills` dari PRD-01.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_profile_requires_login` | Pengunjung diarahkan ke login. |
| `test_profile_shows_confirmed_skills_readonly` | Skill terkonfirmasi tampil, tidak dapat diubah. |
| `test_save_bookmark` | Bookmark tersimpan untuk pengguna login. |
| `test_save_bookmark_twice_no_duplicate` | Kombinasi unik menahan duplikat. |
| `test_remove_bookmark` | Bookmark terhapus hanya untuk pengguna tersebut. |
| `test_saved_page_pagination_and_empty` | Pagination dan kondisi kosong benar. |
| `test_save_nonexistent_job_error` | Error ramah, bukan 500. |
| `test_csrf_on_bookmark_post` | POST tanpa token ditolak. |
| `test_nav_state_variants` | Navigasi berbeda untuk publik, pengguna, admin. |
| `test_no_application_status_fields` | Tidak ada field/status lamaran pada respons dan skema. |

### 7.2 Pengujian Manual

1. Login, simpan tiga lowongan, periksa `/saved`.
2. Simpan lowongan yang sama dua kali dan pastikan tidak ada duplikat.
3. Hapus satu bookmark dan periksa daftar serta jumlah pada navigasi.
4. Buka `/profile` dan cocokkan skill terkonfirmasi dengan database.
5. Logout, buka `/saved`, dan pastikan diarahkan ke login.
6. Uji tampilan pada 360 px, 768 px, dan 1280 px.

## 8. Out of Scope

- Ekstraksi dan konfirmasi skill dari CV (PRD-07).
- Rekomendasi lowongan.
- Asisten AI.
- Panel admin dan REST API (endpoint bookmark disediakan di PRD-09).
- Status lamaran, tracker lamaran, dan pengingat lamaran.

## 9. Catatan Teknis

- Gunakan `insert ... on conflict do nothing` atau pemeriksaan pra-insert untuk mencegah duplikat.
- Semua aksi mutasi memakai POST + CSRF; gunakan pola PRG (Post/Redirect/Get).
- Endpoint API untuk bookmark akan memakai service yang sama (PRD-09).
- Jangan menyimpan atau menampilkan isi CV di profil.

## 10. Referensi Proyek

Tidak ada proyek referensi dengan registrasi email/password. Yang dapat dirujuk hanya pola sesi, pembatasan akses, dan data per pengguna.

### 10.1 Sesi dan Pembatasan Akses — Bot Utang-Piutang (`D:\Semester 5\Praktik Scripting\Pertemuan 8`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `web.py` — `butuh_login(view)` | Decorator berbasis `functools.wraps` yang membaca `session.get("chat_id")`, membedakan respons `/api/` (`jsonify(...), 401`) dari halaman HTML (`render_template("error.html", ...), 403`), dan membersihkan sesi bila pengguna tidak lagi valid. Acuan langsung R-06-09. |
| `web.py` — `create_app()` | Konfigurasi cookie sesi (`SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE="Lax"`, `PERMANENT_SESSION_LIFETIME`) dan `@app.after_request` untuk `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`. Acuan R-06-08 dan konsistensi dengan PRD-01. |
| `web.py` — `api_dashboard()`, `api_debt()` | Setiap query selalu mengambil `chat_id = int(session["chat_id"])` dari sesi, tidak dari parameter klien. Pola ini dipakai untuk memastikan `/saved` hanya menampilkan bookmark milik pengguna (R-06-05). |
| `database.py` — `koneksi()` | Context manager yang meng-commit saat sukses dan rollback saat gagal, dengan `PRAGMA foreign_keys = ON`. Acuan agar operasi simpan/hapus bookmark atomik. |
| `database.py` — `daftar_atau_buat_user()` | Upsert `INSERT ... ON CONFLICT(chat_id) DO UPDATE SET nama = COALESCE(excluded.nama, users.nama)` yang mempertahankan data lama. Berguna saat memperbarui profil (R-06-02). |
| `tests/test_web.py` | Uji endpoint yang memastikan data pengguna lain tidak bocor dan permintaan tanpa sesi ditolak. Acuan test plan §7.1. |

### 10.2 Pendaftaran Pengguna — Bot Rekap Lowongan Dealls (`D:\Semester 5\Praktik Scripting\Pertemuan 9`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `db.py` — `ensure_user(chat_id)` | `INSERT OR IGNORE INTO users (...)`, pola idempoten untuk memastikan satu pengguna hanya dibuat sekali. Padanan untuk mencegah duplikat bookmark (R-06-05). |
| `db.py` — `set_subscription()` | Pola update sederhana dengan `UPDATE ... WHERE` yang hanya menyentuh baris pengguna tersebut. Acuan untuk R-06-04 (hapus bookmark hanya milik pengguna). |

**Cara mengadaptasi ke KarirLens**

1. Terapkan pola `butuh_login` sebagai `@login_required` di seluruh route personal (`/profile`, `/saved`), termasuk pembedaan respons JSON untuk route `/api/`.
2. Ambil `user_id` dari sesi di service layer, bukan dari form, agar bookmark tidak dapat dipalsukan.
3. Untuk unik `(user_id, job_id)`, gunakan constraint database ditambah pemeriksaan pra-insert; pola `ensure_user` menunjukkan pendekatan idempoten yang sama.
4. Karena KarirLens memakai Supabase, `ON CONFLICT` dipetakan ke `upsert(..., on_conflict="user_id,job_id")`.

**Yang tidak diambil**

- Login lewat token bertanda tangan dari bot Telegram. KarirLens memakai email/password, jadi `web_auth.py` tidak dipakai; hanya pola sesinya yang menjadi acuan.
- Data piutang/utang dan skema `debts`/`payments`. Tidak relevan; KarirLens memakai `saved_jobs`.
- Status langganan notifikasi (`subscribed`). Tidak ada padanan di KarirLens.
- Tidak ada referensi untuk hash password dan CSRF; bagian itu tetap mengikuti PRD induk.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Bookmark bekerja tanpa duplikat dan tanpa status lamaran.
- Navigasi konsisten di seluruh halaman.

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `app/profile/repository.py` | Query `saved_jobs`, `user_skills`, `users`, `jobs` milik modul ini |
| `app/profile/service.py` | Aturan bookmark, profil, pagination tersimpan |
| `app/profile/routes.py` | `/profile`, `/profile/name`, `/saved`, `add`, `remove` |
| `app/auth/repository.py` | `update_name` (R-06-02) |
| `app/jobs/service.py` | `_tandai_tersimpan` untuk katalog, detail, beranda |
| `app/jobs/repository.py` | `saved_ids_for_user` |
| `app/navigation.py` | `saved_count` untuk indikator navigasi |
| `app/templating.py` | Pemetaan endpoint dua arah |
| `templates/base.html` | Tombol simpan benar-benar mengirim POST |
| `templates/profile/index.html` | Panel ubah nama |
| `tests/unit/test_profile_bookmark.py` | 21 test PRD-06 §7.1 |

### 12.2 Keputusan

**Bookmark adalah penanda, bukan lamaran.** Tidak ada kolom status, tahapan,
atau tanggal melamar — dan test menegaskannya dengan memeriksa nama kolom pada
baris yang disimpan (§3.2, R-06-13).

**Keunikan dijaga berlapis.** `upsert(on_conflict="user_id,job_id")` mencegah
duplikat pada dua permintaan bersamaan; `find_saved_job` lebih dulu membuat
pesan "sudah tersimpan" dapat dibedakan dari "disimpan". Pemeriksaan pra-insert
saja tidak cukup: dua klik cepat dapat lolos keduanya sebelum salah satu
menulis.

**Urutan `/saved` menurut waktu disimpan**, bukan tanggal terbit lowongan.
Halaman ini menjawab "apa yang baru saya tandai", dan yang baru ditandai paling
relevan bagi pengguna.

**`user_id` selalu dari sesi, tidak pernah dari form.** Mengambilnya dari input
akan membuat bookmark dapat dipalsukan untuk akun lain.

**Pagination di service, bukan database.** Jumlah bookmark satu pengguna kecil,
dan urutannya berasal dari `saved_jobs` sementara isi kartunya dari `jobs` —
memotong di database memerlukan join yang tidak tersedia lewat client ini.

### 12.3 Bug yang Ditemukan Verifikasi

**`NotFoundError` tertelan menjadi redirect.** Route `add` menangkap `AppError`
untuk menampilkan pesan, sehingga lowongan yang tidak ada menghasilkan 302 ke
`/saved` alih-alih 404. Pengguna mengira bookmark-nya bermasalah, padahal
lowongannya memang tidak ada. Sekarang `NotFoundError` dibiarkan naik ke handler
global (R-06-11).

**Tautan pratinjau bercampur dengan produksi.** Setelah `profile.index` dan
`profile.saved` terdaftar, halaman `/preview/profile` menaut ke `/saved`
(produksi) alih-alih `/preview/saved`. Penerjemah endpoint di `templating.py`
sebelumnya hanya satu arah. Sekarang dua arah: halaman pratinjau tetap di
pratinjau, halaman produksi tetap di produksi.

**Larangan arsitektur:** `profile/service.py` sempat mengimpor
`app.auth.repository` dan `app.jobs.repository`. Aturan §4 butir 2 membatasi
setiap service pada repository modulnya sendiri. Query yang dibutuhkan
dipindahkan ke `profile/repository.py`.

**Kelas CSS yang tidak ada.** Panel ubah nama memakai `.inline-form`,
`.field-label`, dan `.input` — ketiganya tidak ada di `components.css`, sehingga
input tampil sempit dan tombol memenuhi lebar. Diganti `.field` yang sudah
dipakai form auth.

**`"now()"` sebagai nilai kolom.** `update_name` semula mengirim string
`"now()"` untuk `updated_at`. PostgREST memakai parameter terikat, jadi string
itu akan tersimpan sebagai teks, bukan dipanggil sebagai fungsi SQL.

### 12.4 Verifikasi Terukur

Terhadap Supabase sungguhan, lewat test client:

| Langkah | Hasil |
|---|---|
| Daftar pengguna | 302, pengguna dibuat |
| `/profile` | 200, memuat identitas, ringkasan, panel ubah nama |
| Simpan 3 lowongan | 302, `saved_jobs` = 3 |
| Simpan ulang lowongan yang sama | pesan "sudah tersimpan", **tetap 3 baris** |
| Hapus satu | 302, `saved_jobs` = 2 |
| Simpan lowongan `999999` | **404**, bukan redirect |
| Tamu buka `/saved` | 302 → `/auth/login?next=%2Fsaved` |
| Ubah nama | 200, judul berubah, email tidak berubah |

Diperiksa di browser: tamu melihat nav `Lowongan, Insight`; setelah masuk
menjadi `Lowongan, Insight, Tersimpan, CV, Admin` (R-06-10). Klik tombol simpan
menambah `aria-pressed="true"` dari 2 menjadi 3 dan memunculkan toast, dan
`/saved` menampilkan 3 kartu yang semuanya bertanda tersimpan — cocok dengan
database. Tidak ada luberan pada 360px di `/profile`, `/saved`, maupun `/jobs`.

Data uji dihapus setelah verifikasi (1 pengguna, 3 bookmark).

Total test setelah task ini: **523 lulus**.
