# PRD-09 — Admin dan API (Backend)

| Field | Keterangan |
|---|---|
| ID task | PRD-09 |
| Nama task | Admin dan API (Backend) |
| Track | B — Backend |
| Prioritas | P0 |
| Milestone | M7 AI, admin, API (2 hari) |
| Dependensi | PRD-04, PRD-05, PRD-06, PRD-07, PRD-08, PRD-F05 |
| Task yang bergantung | PRD-10 |
| Status | Selesai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F05](./PRD-F05-insight-admin.md) |

---

## 1. Konteks

Seluruh halaman `/admin/*` sudah dibangun pada PRD-F05: kartu ringkasan, tabel lowongan, pengguna, riwayat run, tinjauan cluster, `DataTable`, dan dialog konfirmasi hapus. Task ini mengisi akses dan datanya: pengecekan peran admin, query agregat, aksi hapus, serta REST API yang memakai service yang sama dengan halaman web.

Panel admin tidak boleh menampilkan file atau teks CV. Aturan itu sudah ditegakkan di template (PRD-F05 R-F05-13); task ini memastikan backend juga tidak menyediakan datanya.

Dua kontrak wajib dipenuhi: **PRD-F05 §4.1** untuk halaman admin, dan bentuk respons `{"data", "meta"}` / `{"error"}` untuk API.

## 2. Tujuan

1. Menyediakan pengecekan peran admin melalui `admin_required`.
2. Menyediakan data ringkasan, daftar lowongan, pengguna, run, dan cluster.
3. Menyediakan aksi hapus lowongan tidak valid dengan konfirmasi.
4. Menyediakan REST API publik dan personal memakai service yang sama.
5. Menjaga agar API dan web tidak menduplikasi logika (R-09-15).

## 3. Scope

### 3.1 Termasuk

- `app/admin/repository.py`: query agregat dan daftar dengan pagination.
- `app/admin/service.py`: ringkasan, penghapusan lowongan.
- Dekorator `admin_required` dan migrasi kolom `users.role`.
- Route `/admin*` yang mengisi kontrak PRD-F05 §4.1.
- `app/api/routes.py` untuk seluruh endpoint §4.3.
- `app/api/response.py` untuk format `{"data","meta"}` dan `{"error"}`.
- Menonaktifkan route preview untuk `/admin/*`.

### 3.2 Tidak termasuk

- Markup, CSS, JavaScript, `DataTable`, dan dialog admin (selesai pada PRD-F05).
- Menampilkan file atau teks CV.
- Status lamaran atau tracker lamaran.
- Endpoint admin di API publik.
- Manajemen pembayaran atau langganan.

## 4. Requirement

### 4.1 Panel Admin

| ID | Requirement | Prioritas |
|---|---|---|
| R-09-01 | Login admin terpisah; akun non-admin tidak dapat mengakses `/admin*`. | P0 |
| R-09-02 | `/admin` menampilkan jumlah lowongan, pengguna, dan proses pembaruan terbaru. | P0 |
| R-09-03 | `/admin/jobs` menampilkan daftar lowongan dengan pencarian dan pagination. | P0 |
| R-09-04 | Admin dapat meninjau dan menghapus lowongan tidak valid dengan konfirmasi. | P0 |
| R-09-05 | `/admin/users` menampilkan daftar pengguna dengan pagination; tidak menampilkan password atau CV. | P0 |
| R-09-06 | `/admin/runs` menampilkan riwayat pembaruan: waktu, status, jumlah ditemukan/disimpan/diperbarui, error. | P0 |
| R-09-07 | `/admin/clusters` menampilkan hasil cluster yang dapat ditinjau. | P0 |
| R-09-08 | Error dan aksi admin dicatat ke log tanpa data sensitif. | P0 |
| R-09-09 | Tidak ada route atau data CV pada panel admin. | P0 |
| R-09-10 | Panel admin responsif dan konsisten dengan layout utama. | P1 |

### 4.2 REST API

| ID | Requirement | Prioritas |
|---|---|---|
| R-09-11 | API menyediakan endpoint pada §4.3. | P0 |
| R-09-12 | Endpoint daftar mendukung pagination dengan metadata seragam. | P0 |
| R-09-13 | Format error konsisten dan tidak membocorkan detail internal. | P0 |
| R-09-14 | Endpoint publik tidak memerlukan autentikasi; endpoint personal memerlukannya. | P0 |
| R-09-15 | API memakai service layer yang sama dengan halaman web (tanpa duplikasi logika). | P0 |
| R-09-16 | Respons JSON valid dan dapat dikonsumsi. | P0 |
| R-09-17 | Endpoint personal menolak permintaan tanpa sesi dengan 401. | P0 |
| R-09-18 | Query API memakai parameter terikat dan aman dari injeksi. | P0 |

### 4.3 Daftar Endpoint

| Method | Endpoint | Akses | Fungsi |
|---|---|---|---|
| GET | `/api/jobs` | Publik | Daftar lowongan dengan pencarian, filter, dan pagination. |
| GET | `/api/jobs/<id>` | Publik | Detail lowongan. |
| GET | `/api/companies/<slug>` | Publik | Ringkasan perusahaan dari data lowongan. |
| GET | `/api/insights/categories` | Publik | Distribusi kategori. |
| GET | `/api/insights/skills` | Publik | Skill paling banyak dicari. |
| GET | `/api/insights/salary` | Publik | Statistik gaji faktual. |
| GET | `/api/recommendations` | Pengguna | Rekomendasi berdasarkan skill terkonfirmasi. |
| GET | `/api/saved-jobs` | Pengguna | Daftar lowongan tersimpan. |
| POST | `/api/saved-jobs` | Pengguna | Menyimpan lowongan. |
| DELETE | `/api/saved-jobs/<job_id>` | Pengguna | Menghapus lowongan tersimpan. |
| POST | `/api/cv/extract` | Pengguna | Ekstraksi skill dari CV tanpa menyimpan file. |
| POST | `/api/assistant` | Pengguna | Pertanyaan ke asisten AI. |

### 4.4 Format Respons

```json
{
  "data": {},
  "meta": { "page": 1, "per_page": 12, "total": 120, "has_next": true }
}
```

```json
{
  "error": { "code": "NOT_FOUND", "message": "Lowongan tidak ditemukan." }
}
```

## 5. Acceptance Criteria

- [ ] Admin dapat login dan mengakses panel, pengguna biasa tidak dapat.
- [ ] Ringkasan admin menampilkan jumlah yang sesuai database.
- [ ] Admin dapat menghapus lowongan tidak valid dengan konfirmasi.
- [ ] `/admin/runs` menampilkan status dan error pembaruan.
- [ ] Panel admin tidak menampilkan file atau teks CV.
- [ ] Semua endpoint pada §4.3 mengembalikan JSON valid.
- [ ] Pagination dan format error konsisten.
- [ ] Endpoint personal menolak permintaan tanpa sesi (401).
- [ ] API memakai service layer yang sama dengan halaman web.
- [ ] Tidak ada endpoint tracker atau status lamaran.

## 6. Dependensi

- PRD-01 (layout, autentikasi, CSRF).
- PRD-04 (service query lowongan).
- PRD-05 (service insight dan cluster).
- PRD-06 (bookmark dan sesi pengguna).
- PRD-07 (ekstraksi CV dan rekomendasi).
- PRD-08 (asisten AI).
- Migrasi kolom `users.role` untuk peran admin.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_admin_requires_role` | Pengguna biasa ditolak dari `/admin*`. |
| `test_admin_summary_counts` | Ringkasan sesuai data uji. |
| `test_admin_delete_invalid_job` | Lowongan terhapus dengan konfirmasi. |
| `test_admin_no_cv_access` | Tidak ada route/data CV di admin. |
| `test_api_jobs_pagination` | Metadata pagination benar. |
| `test_api_job_detail` | Detail JSON valid; 404 format konsisten. |
| `test_api_insights` | Endpoint insight mengembalikan data sesuai. |
| `test_api_personal_requires_auth` | Endpoint personal menolak tanpa sesi (401). |
| `test_api_saved_jobs_crud` | Simpan/hapus bookmark melalui API. |
| `test_api_error_format` | Format error konsisten dan tanpa detail internal. |
| `test_api_salary_min_sample` | Statistik gaji tidak muncul saat sampel < 5. |
| `test_api_uses_same_service` | API dan halaman web memakai service yang sama. |

### 7.2 Pengujian Manual

1. Login admin dan buka seluruh halaman admin.
2. Login sebagai pengguna biasa dan pastikan ditolak dari `/admin`.
3. Hapus satu lowongan tidak valid dan periksa daftar.
4. Panggil setiap endpoint API dengan `curl` dan periksa JSON.
5. Panggil endpoint personal tanpa sesi dan pastikan 401.
6. Periksa tidak ada data CV di panel admin.

## 8. Out of Scope

- Menampilkan file atau teks CV.
- Status lamaran dan tracker lamaran.
- Endpoint admin publik pada API.
- Analitik lanjutan dan ekspor data besar.

## 9. Catatan Teknis

- Tambahkan `users.role` (default `user`) dengan nilai `admin` untuk akun admin.
- Endpoint API memakai autentikasi berbasis sesi; dokumentasikan pada README API.
- Untuk API personal mutasi, gunakan mekanisme yang aman terhadap CSRF (mis. token header) dan dokumentasikan.
- Format error seragam di seluruh endpoint, termasuk 400/401/404/429/500.
- Jangan menduplikasi query; API memanggil service yang sama dengan route web.

## 10. Referensi Proyek

Proyek utama: **BengkelBot** (`D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot`) — punya dashboard admin berbasis statistik dan REST API JSON di aplikasi Flask yang sama.

### 10.1 Panel Admin — BengkelBot (`D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `app.py` — `admin()` | Satu payload statistik dipakai untuk kartu ringkasan, tabel, dan daftar sekaligus (`ringkasan = history.statistik()`), lalu dirender ke `templates/admin.html`. Acuan R-09-02. |
| `app.py` — `admin_diizinkan()` | Pengecekan akses admin dengan `hmac.compare_digest` untuk mencegah kebocoran lewat perbedaan waktu, dan kembalikan halaman 403 bila gagal. Acuan R-09-01. |
| `chatbot/database.py` — `statistik()` | Agregasi admin: total, jumlah dikenali, persen, jumlah sesi unik, distribusi per kelompok lewat `GROUP BY`, serta **batas jumlah baris** yang ditampilkan (`LIMIT`, `batas_tidak_dikenali=50`). Acuan R-09-05 dan R-09-06. |
| `chatbot/database.py` — `per_intent` dengan `persen_bar` | Menghitung proporsi relatif terhadap nilai terbanyak untuk lebar batang grafik, terpisah dari persen terhadap total. Pola ini dipakai untuk ringkasan admin KarirLens. |
| `app.py` — `galat(pesan, kode)`, `halaman_galat(kode, judul, pesan)` | Pemisahan tegas antara respons JSON untuk `/api/*` dan halaman HTML untuk route web, termasuk `errorhandler(404)` dan `(500)` yang berbeda per jenis route. Acuan R-09-13 dan R-09-16. |
| `app.py` — `api_stats()` | Endpoint statistik admin yang memakai pengecekan izin yang sama seperti halaman admin, bukan jalur terpisah. Acuan R-09-15. |
| `templates/admin.html`, `templates/error.html` | Struktur dashboard admin (kartu ringkasan, tabel distribusi, daftar baris terbaru) dan halaman galat yang ramah. Acuan R-09-07 dan R-09-10. |
| `tests/test_web.py` | Uji endpoint admin dan API dengan `app.test_client()`, termasuk kasus akses ditolak. Acuan test plan §7.1. |
| `README.md` — bagian variabel lingkungan | Dokumentasi tabel variabel (`SECRET_KEY`, `ADMIN_KEY`, `DATABASE`, `HOST`, `PORT`) sebagai pola untuk `docs/API.md` dan README KarirLens. Acuan R-09-13 tidak membocorkan detail internal: kunci admin dibandingkan, bukan ditampilkan. |

### 10.2 Pagination dan Kontrak JSON — Bot Rekap Lowongan Dealls (`D:\Semester 5\Praktik Scripting\Pertemuan 9`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `app.py` — `api_lowongan()`, `api_statistik()` | Kontrak JSON ringkas (`total`, `halaman`, `total_halaman`, `data`) yang memakai fungsi Python yang sama dengan halaman HTML. Acuan R-09-11 dan R-09-12. |
| `app.py` — `_lowongan()` | Pagination server-side dan validasi query string defensif, dipakai ulang oleh endpoint API. |
| `tests/test_web.py` — `@pytest.mark.parametrize` | Pengujian beberapa jenis ekspor/endpoint dalam satu test, mengurangi duplikasi. |

**Cara mengadaptasi ke KarirLens**

1. Buat `admin_required` dengan pola `admin_diizinkan()` — bandingkan peran dari sesi, kembalikan 403 dengan halaman ramah untuk route web dan JSON untuk route API.
2. Satukan statistik admin dalam satu service yang mengembalikan dict siap render (`jumlah lowongan`, `pengguna`, `runs` terbaru), mengikuti `history.statistik()`.
3. Untuk API, pakai satu helper `galat()` dan satu bentuk `{"data": ..., "meta": {...}}` sesuai §4.4 agar konsisten dengan PRD-04.
4. Batasi jumlah baris yang ditampilkan di halaman admin (pagination) seperti `batas_tidak_dikenali=50`, agar tidak memuat seluruh tabel.

**Yang tidak diambil**

- Login admin berbasis `?key=` di query string. KarirLens memakai akun admin dengan peran pada tabel `users`; kunci di URL terlalu lemah untuk aplikasi multi-pengguna.
- Statistik intent chatbot dan penyimpanan riwayat chat. Tidak ada padanan di KarirLens; admin KarirLens menampilkan data lowongan, pengguna, dan `scrape_runs`.
- Penyimpanan dan eksposur isi CV. Tidak diterapkan; R-09-09 tetap berlaku.
- Tidak ada referensi untuk meninjau hasil cluster dan menghapus lowongan tidak valid; bagian itu dikerjakan tanpa acuan.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Panel admin berfungsi dan tidak memuat data CV.
- Semua endpoint pada §4.3 mengembalikan JSON valid.
