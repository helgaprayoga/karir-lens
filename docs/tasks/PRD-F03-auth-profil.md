# PRD-F03 — Auth, Profil, dan Tersimpan (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F03 |
| Nama task | Auth, Profil, dan Tersimpan |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01 |
| Task yang bergantung | PRD-F06 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Backend pasangan | [PRD-06](./PRD-06-akun-bookmark.md) |
| Design system | [Design System KarirLens](../design-system.md) |

---

## 1. Konteks

PRD-01 sudah membuat form registrasi, login, dan logout yang berfungsi. Task ini melengkapi sisi tampilannya sesuai design system: state error per field, pesan validasi yang terhubung `aria-describedby`, dan halaman profil serta lowongan tersimpan yang belum ada sama sekali.

Halaman tersimpan memakai `JobCard` yang sama dengan katalog (PRD-F02), tanpa anatomi berbeda. Profil menampilkan skill terkonfirmasi dan daftar bookmark sebagai ringkasan.

## 2. Tujuan

1. Menyelesaikan tampilan form auth dengan state dan pesan validasi sesuai design system.
2. Membangun halaman profil: identitas, skill terkonfirmasi, ringkasan akun.
3. Membangun halaman lowongan tersimpan.
4. Menyediakan `Toast` untuk umpan balik simpan/hapus.
5. Menetapkan kontrak template untuk PRD-06.

## 3. Scope

### 3.1 Termasuk

- `/auth/register`, `/auth/login` dengan state error, loading, dan disabled.
- `/profile`: identitas, skill terkonfirmasi beserta sumbernya, hapus skill.
- `/saved`: daftar bookmark memakai `JobCard`.
- Partial `toast`, `skill_panel`, `form_field`, `button_loading`.
- Umpan balik simpan/hapus bookmark di sisi tampilan (belum persisten).
- Pesan validasi di dekat field dengan `aria-describedby` dan `aria-invalid`.

### 3.2 Tidak termasuk

- Autentikasi nyata: hash password, sesi, CSRF (sudah ada di PRD-01).
- Bookmark persisten, keunikan per pengguna (PRD-06).
- Upload CV (PRD-F04).
- Verifikasi email.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F03-01 | Setiap field form punya `<label>` terhubung, pesan error dengan `aria-describedby`, dan `aria-invalid` saat gagal. | P0 |
| R-F03-02 | Pesan error tampil di dekat field terkait, bukan hanya sebagai banner di atas form. | P0 |
| R-F03-03 | Tombol submit menampilkan state loading dan disabled selama pengiriman. | P0 |
| R-F03-04 | `/profile` menampilkan identitas pengguna, daftar skill terkonfirmasi, dan ringkasan (jumlah skill, jumlah tersimpan). | P0 |
| R-F03-05 | Setiap skill terkonfirmasi menampilkan sumbernya (CV atau manual) dan tombol hapus. | P0 |
| R-F03-06 | `/saved` menampilkan daftar bookmark memakai `JobCard` dengan anatomi yang sama seperti katalog. | P0 |
| R-F03-07 | `/saved` menampilkan `EmptyState` dengan ajakan menjelajahi lowongan bila kosong. | P0 |
| R-F03-08 | Menyimpan dan menghapus bookmark memberi umpan balik `Toast` dengan `role="status"` dan `aria-live="polite"`. | P0 |
| R-F03-09 | Tombol simpan pada kartu menandai state aktif dengan `aria-pressed` dan ikon terisi. | P0 |
| R-F03-10 | Halaman personal menampilkan pesan jelas bila pengguna belum login, bukan halaman kosong. | P0 |
| R-F03-11 | Tidak ada elemen "kelengkapan profil" atau metrik yang tidak punya tabel sumber. | P0 |
| R-F03-12 | Tidak ada status lamaran atau tahapan seleksi di halaman mana pun. | P0 |

### 4.1 Kontrak Template

**`profile/index.html`** menerima:

| Variabel | Tipe | Keterangan |
|---|---|---|
| `profile` | `dict` | `{name, email, created_at}` |
| `skills` | `list[dict]` | `{id, skill, source, is_confirmed, created_at}` |
| `summary` | `dict` | `{skill_count, saved_count}` |

**`profile/saved.html`** menerima `items` (`list[dict]`, bentuk `job` PRD-F01 §4.2) dan `meta` (`{page, per_page, total, has_next}`).

**Form auth** menerima `form` (Flask-WTF) dengan field `name`, `email`, `password`, `remember`, dan `submit`.

## 5. Acceptance Criteria

- [ ] Form registrasi dan login menampilkan pesan error di dekat field yang salah.
- [ ] `aria-invalid` dan `aria-describedby` terpasang saat validasi gagal.
- [ ] Tombol submit disabled dan menampilkan loading saat dikirim.
- [ ] `/profile` menampilkan identitas, skill terkonfirmasi, dan ringkasan.
- [ ] Setiap skill menampilkan sumber dan tombol hapus.
- [ ] `/saved` memakai `JobCard` dengan anatomi identik katalog.
- [ ] `/saved` kosong memakai `EmptyState`.
- [ ] Simpan/hapus bookmark menampilkan `Toast` yang terbaca pembaca layar.
- [ ] Tidak ada metrik kelengkapan profil atau status lamaran di layar.
- [ ] Layout tidak rusak pada 360, 768, 1024, 1280 px.

## 6. Dependensi

- PRD-F01 (komponen, shell, preview blueprint).
- PRD-01 (form auth, sesi, `current_user`).
- Fixture `tests/fixtures/ui/profile.json`, `saved.json`.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cekupan |
|---|---|
| `test_register_shows_field_errors` | Validasi gagal merender pesan dekat field. |
| `test_field_aria_attributes` | `aria-invalid` dan `aria-describedby` terpasang saat error. |
| `test_submit_button_states` | Tombol punya atribut disabled saat state loading. |
| `test_profile_renders_skills` | Skill terkonfirmasi tampil beserta sumber. |
| `test_profile_summary_counts` | Ringkasan sesuai fixture. |
| `test_saved_uses_job_card` | `/saved` memakai partial kartu yang sama. |
| `test_saved_empty_state` | Fixture kosong memicu `EmptyState`. |
| `test_toast_has_live_region` | `Toast` memakai `role="status"` dan `aria-live`. |
| `test_no_application_tracker_ui` | Tidak ada teks/atribut status lamaran. |
| `test_no_profile_completeness_metric` | Tidak ada elemen kelengkapan profil. |

### 7.2 Pengujian Manual

1. Kirim form kosong, password pendek, dan email tidak valid; periksa pesan per field.
2. Navigasi form dengan keyboard saja; pastikan pesan error terbaca.
3. Buka `/profile` dan hapus satu skill; periksa perubahan tampilan.
4. Buka `/saved`, hapus satu bookmark, dan periksa toast.
5. Buka `/saved` dalam keadaan kosong.
6. Akses `/profile` tanpa login dan pastikan pesan jelas.

## 8. Out of Scope

- Logika autentikasi dan sesi (PRD-01).
- Persistensi bookmark dan skill (PRD-06).
- Upload dan ekstraksi CV (PRD-F04, PRD-07).
- Verifikasi email, lupa password, dan ganti password.

## 9. Catatan Teknis

- Error validasi WTForms sudah tersedia di `form.<field>.errors`; template hanya perlu menampilkannya dengan atribut aksesibilitas yang benar.
- `Toast` dibuat sebagai partial yang dipanggil dari `base.html` agar konsisten di seluruh halaman.
- State loading tombol cukup dengan JavaScript kecil yang menambahkan kelas dan `disabled` saat submit; tidak perlu framework.
- Halaman personal memakai dekorator `login_required` dari PRD-01; tampilan hanya perlu menyediakan anchor pesan.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-preview.html` baris 941–957 | Panel profil pada rail: identitas, daftar tag skill, tombol kelola. |
| `docs/design-system.md` §4.15 `Toast` | Anatomi toast, `role="status"`, `aria-live="polite"`. |
| `docs/design-system.md` §5 | Aturan form: label terhubung, `aria-describedby`, focus ring. |
| Bot Utang-Piutang — `templates/` | Pola form dengan pesan validasi dan flash message. |

**Yang tidak diambil**

- Metrik "kelengkapan profil" dari pratinjau (design system §6 melarangnya; tidak ada tabel sumber).
- Status lamaran atau tahapan seleksi (di luar scope PRD induk §4).

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Profil dan halaman tersimpan dapat ditinjau di browser dengan fixture.
- Kontrak template pada §4.1 tertulis dan dipakai PRD-06.
