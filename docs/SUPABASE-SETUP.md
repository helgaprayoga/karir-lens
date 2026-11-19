# Panduan Setup Supabase — KarirLens

| Field | Keterangan |
|---|---|
| Dokumen | Panduan setup Supabase |
| Diperbarui | 18 November 2026 |
| PRD terkait | [PRD-01 §4.2](../tasks/PRD-01-fondasi-proyek.md) |
| Skema | [`migrations/001_initial_schema.sql`](../../migrations/001_initial_schema.sql) |

Panduan ini menutup satu-satunya acceptance criteria PRD-01 yang belum terbukti: **"Semua tabel pada §4.2 terbentuk setelah migrasi dijalankan."**

---

## 1. Yang Perlu Diketahui Sebelum Mulai

Supabase memberi **dua jalur akses** yang berbeda, dan keduanya dipakai proyek ini:

| Jalur | Protokol | Bisa apa | Dipakai oleh |
|---|---|---|---|
| **PostgREST** | HTTP + kunci API | Baca/tulis **baris**; tidak bisa DDL | Aplikasi web (`core/db.py`) |
| **Koneksi langsung** | Protokol Postgres + password DB | Termasuk `CREATE TABLE` | `python -m db migrate` (`core/db_direct.py`) |

Banyak tutorial hanya menyebut jalur pertama, lalu menyimpulkan migrasi harus lewat dashboard. Itu keliru: **DDL bisa dijalankan dari program** lewat jalur kedua — sama seperti `php artisan migrate` pada Laravel.

| Pekerjaan | Dikerjakan oleh |
|---|---|
| Membuat project | Dashboard Supabase |
| Membuat tabel dan index | `python -m db migrate` |
| Membaca dan menulis data | Aplikasi lewat `supabase` client |
| Memverifikasi skema | `python scripts/verify_supabase.py` |

SQL Editor dashboard tetap tersedia sebagai cadangan, tetapi bukan jalur utama.

---

## 2. Membuat Project

1. Buka <https://supabase.com/dashboard> dan masuk.
2. Klik **New project**.
3. Isi:

   | Field | Nilai |
   |---|---|
   | Name | `karirlens` |
   | Database Password | *(buat yang kuat — **wajib dicatat**, dipakai migrasi)* |
   | Region | `Southeast Asia (Singapore)` — terdekat ke Indonesia |
   | Plan | Free |

4. Tunggu sampai provisioning selesai (sekitar satu menit).

**Database Password ini penting.** Ia bukan kunci API. Ia dipakai `python -m db migrate` untuk konek langsung ke Postgres. Tanpa password ini, migrasi dari program tidak bisa jalan.

---

## 3. Mengambil Kredensial

Ada **tiga** nilai yang dibutuhkan, dari dua tempat berbeda.

### 3.1 URL dan kunci API (untuk aplikasi web)

Dashboard Supabase sudah berubah. Halaman **Settings → API** dengan kunci `anon` berformat JWT panjang (`eyJhbGciOi...`) **sudah tidak ada** pada project baru. Yang ada sekarang **Settings → API Keys**.

1. Buka project → **Settings** → **API Keys**.
2. Ambil:

   | Di dashboard | Masuk ke `.env` sebagai | Bentuk |
   |---|---|---|
   | **Project URL** (di **Settings → Data API**, atau dialog **Connect**) | `SUPABASE_URL` | `https://xxxx.supabase.co` |
   | **Publishable key** | `SUPABASE_KEY` | `sb_publishable_...` |

Cara tercepat: dialog **Connect** menampilkan URL dan publishable key siap salin.

**Publishable atau anon?**

| | Publishable (`sb_publishable_...`) | anon (`eyJ...`) |
|---|---|---|
| Status | Format baru, dianjurkan | Warisan, dihentikan akhir 2026 |
| Aman di browser | Ya | Ya |
| Didukung `supabase-py` | Ya — client mengirim header `apiKey` dan `Authorization` | Ya |

Pakai **publishable**.

### 3.2 Kredensial database (untuk migrasi)

1. Buka **Settings** → **Database** → **Connection string**.
2. Pilih tab **Session pooler** (port `5432`).
3. Catat:

   | Di dashboard | Masuk ke `.env` sebagai | Contoh |
   |---|---|---|
   | Host | `SUPABASE_DB_HOST` | `aws-0-ap-southeast-1.pooler.supabase.com` |
   | Port | `SUPABASE_DB_PORT` | `5432` |
   | User | `SUPABASE_DB_USER` | `postgres.abcdefghijklm` |
   | Password | `SUPABASE_DB_PASSWORD` | *(password dari langkah 2)* |
   | Database | `SUPABASE_DB_NAME` | `postgres` |

**Jangan tertukar:** `SUPABASE_KEY` adalah kunci API; `SUPABASE_DB_PASSWORD` adalah password database. Keduanya berbeda dan tidak bisa saling menggantikan.

**Jangan pakai `secret` key** (`sb_secret_...`) atau `service_role`. Keduanya melewati Row Level Security dan tidak boleh ada di aplikasi web.


---

## 4. Membuat Tabel

Setelah kredensial database terisi di `.env`, jalankan:

```powershell
python -m db status      # lihat migrasi dan statusnya
python -m db migrate     # terapkan yang belum dijalankan
```

Keluaran yang diharapkan:

```text
Target: postgres.abcdefghijklm@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres (sslmode=require)

  JALAN  001_initial_schema ... OK

Selesai. 1 migrasi diterapkan.
```

Perintah lain:

| Perintah | Fungsi |
|---|---|
| `python -m db status` | Tampilkan setiap migrasi: `OK`, `BELUM`, atau `UBAH` |
| `python -m db migrate` | Terapkan migrasi yang belum dijalankan |
| `python -m db migrate --dry-run` | Tampilkan yang akan dijalankan, tanpa menulis |

### Bagaimana runner bekerja

```text
python -m db migrate
  -> baca migrations/*.sql, urut menurut nama
  -> buat tabel pelacak schema_migrations (bila belum ada)
  -> untuk tiap berkas yang belum tercatat:
         jalankan isi berkas + catat versi & checksum, dalam SATU transaksi
  -> berkas yang sudah tercatat dilewati
```

Tiga sifat yang penting:

| Sifat | Artinya |
|---|---|
| **Idempoten** | Menjalankan `migrate` dua kali tidak berefek kedua kali. `schema_migrations` mencegah pengulangan. |
| **Atomik per berkas** | Jika satu migrasi gagal, transaksi dibatalkan. Database tidak tertinggal separuh jadi. |
| **Terdeteksi perubahan** | Bila berkas yang sudah diterapkan diubah, `status` menandainya `UBAH`. Berguna saat mengembangkan migrasi baru. |

### Cadangan: SQL Editor

Bila koneksi langsung tidak memungkinkan (mis. password database hilang), isi [`migrations/001_initial_schema.sql`](../../migrations/001_initial_schema.sql) dapat ditempel ke **SQL Editor** → **Run**. Hasil "Success. No rows returned." adalah normal: `CREATE TABLE` tidak mengembalikan baris.

Konsekuensinya, `schema_migrations` tidak terisi, sehingga `python -m db status` akan melaporkan `BELUM` untuk berkas itu. Perilaku ini tidak berbahaya karena seluruh pernyataan memakai `IF NOT EXISTS`, tetapi jalur utama tetap `python -m db migrate`.

### Tabel yang terbentuk

| Tabel | Isi |
|---|---|
| `sources` | Metadata tiga sumber: Dealls, Kalibrr, Remotive |
| `clusters` | Hasil pengelompokan: label, kata kunci, jumlah lowongan |
| `jobs` | Data lowongan utama |
| `scrape_runs` | Riwayat setiap proses pengambilan data |
| `users` | Akun pengguna, termasuk kolom `role` untuk admin |
| `saved_jobs` | Bookmark, unik per pengguna dan lowongan |
| `user_skills` | Skill pengguna beserta status konfirmasi |
| `schema_migrations` | Pelacak migrasi yang sudah diterapkan |

### 4.1 Grants untuk PostgREST (penting)

Tabel yang dibuat lewat koneksi Postgres langsung **dimiliki role `postgres`**. Role `anon` dan `authenticated` yang dipakai PostgREST tidak otomatis mendapat izin, sehingga aplikasi gagal dengan:

```text
permission denied for table sources  (kode 42501)
```

Karena itu ada migrasi kedua, [`migrations/002_grants.sql`](../../migrations/002_grants.sql), yang memberi `usage`/`select`/`insert`/`update`/`delete` pada schema `public` beserta `alter default privileges` untuk tabel baru. `python -m db migrate` menjalankannya otomatis.

Bila kamu pernah menjalankan migrasi sebelum berkas `002_grants.sql` ada, jalankan `python -m db migrate` sekali lagi; runner akan menerapkannya tanpa mengulang `001`.

### Tabel yang sengaja tidak dibuat

| Tidak ada | Alasan |
|---|---|
| `applications` | Tracker lamaran di luar scope produk |
| Tabel profil perusahaan | Halaman perusahaan diturunkan dari `jobs` |
| Kolom CV apa pun | Berkas dan teks CV tidak pernah disimpan |

### Aman dijalankan berulang?

Ya, pada dua lapis. `schema_migrations` mencegah berkas dijalankan dua kali, dan seluruh pernyataan memakai `CREATE TABLE IF NOT EXISTS` serta `CREATE INDEX IF NOT EXISTS`. Diuji oleh `test_migration_is_idempotent` dan `test_second_run_skips_everything`.

---

## 5. Mengisi `.env`

```powershell
Copy-Item .env.example .env
```

Lalu isi enam nilai:

```dotenv
# Aplikasi web (PostgREST)
SECRET_KEY=hasil-dari-perintah-di-bawah
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=sb_publishable_...

# Migrasi (koneksi langsung)
SUPABASE_DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
SUPABASE_DB_USER=postgres.abcdefghijklm
SUPABASE_DB_PASSWORD=password-database-anda
```

Membuat `SECRET_KEY` yang layak:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nilai lain boleh dibiarkan bawaan. `DEEPSEEK_API_KEY` boleh kosong sampai PRD-08 dikerjakan.

`.env` sudah masuk `.gitignore`, jadi tidak akan ter-commit.

---

## 6. Memverifikasi

Aplikasi akan menolak start bila kredensial belum diisi — itu perilaku yang benar (R-01-04). Untuk memeriksa skema secara langsung:

```powershell
python scripts/verify_supabase.py
```

Keluaran yang diharapkan:

```text
Memverifikasi https://xxxxxxxxxxxx.supabase.co

Tabel:
  OK     tabel sources
  OK     tabel clusters
  OK     tabel jobs
  OK     tabel scrape_runs
  OK     tabel users
  OK     tabel saved_jobs
  OK     tabel user_skills

Kolom:
  OK     jobs: 19 kolom wajib
  OK     users: 7 kolom wajib
  ...

Batasan scope:
  OK     tabel applications tidak ada (sesuai scope)

Skema lengkap. Acceptance criteria PRD-01 §5 baris migrasi terpenuhi.
```

Skrip ini hanya membaca. Ia tidak pernah membuat atau mengubah tabel.

---

## 6.1 Dua Jalur Verifikasi

Keduanya memeriksa hal berbeda, dan keduanya sebaiknya dijalankan:

| Perintah | Memeriksa | Membutuhkan |
|---|---|---|
| `python -m db status` | Migrasi mana yang sudah diterapkan, dan apakah berkasnya berubah | Kredensial database |
| `python scripts/verify_supabase.py` | Tabel, kolom, dan batasan scope benar-benar ada di database | Kunci API |

`db status` menjawab "apakah migrasi sudah dijalankan"; `verify_supabase` menjawab "apakah hasilnya benar". Kalau seseorang menjalankan SQL lewat dashboard, `db status` akan bilang `BELUM` padahal tabelnya ada — di situlah `verify_supabase` yang menentukan.

---

## 7. Menjalankan Aplikasi

```powershell
python -m flask --app wsgi run --debug
```

Buka <http://127.0.0.1:5000>. Halaman beranda tampil, dan `/auth/register` dapat membuat akun sungguhan di tabel `users`.

Untuk memastikan pendaftaran benar-benar tersimpan, buka **Table Editor** → `users` di dashboard setelah mendaftar.

---

## 8. Yang Belum Aktif Setelah Setup Ini

Setup ini hanya menyiapkan **penyimpanan**. Tabel akan tetap kosong sampai Track B mengisinya.

| Masih kosong | Diisi oleh |
|---|---|
| `jobs`, `sources`, `scrape_runs` | PRD-02 dan PRD-03 (ingestion) |
| `clusters` | PRD-05 (clustering) |
| `user_skills` | PRD-07 (CV) |
| `saved_jobs` | PRD-06 (bookmark) |

Halaman katalog, profil, CV, insight, dan admin belum ada. Sesuai [README task](../tasks/README.md), antarmuka dikerjakan lebih dulu di Track A (PRD-F01 s.d. F06), dan selama itu data contoh berasal dari `tests/fixtures/ui/` — bukan dari tabel ini.

---

## 9. Pemecahan Masalah

| Gejala | Sebab | Solusi |
|---|---|---|
| `RuntimeError: Konfigurasi KarirLens belum lengkap` | `.env` belum ada atau `SECRET_KEY`/`SUPABASE_URL`/`SUPABASE_KEY` kosong | Ulangi langkah 5 |
| `Koneksi database langsung belum dikonfigurasi` padahal `.env` sudah diisi | Bug lama: `load_dotenv()` tidak dipanggil di entrypoint CLI | Sudah diperbaiki di `core/config.py: load_env()`; pastikan `python -m db status` dijalankan dari akar repo |
| `permission denied for table ...` (42501) | Grants PostgREST belum diterapkan | Jalankan `python -m db migrate` (menerapkan `002_grants.sql`) |
| `password authentication failed` | `SUPABASE_DB_PASSWORD` salah, atau memakai kunci API | Pakai password database, bukan `SUPABASE_KEY` |
| `could not translate host name` | Host pooler salah ketik | Salin ulang dari dashboard |
| `connection timed out` saat migrate | Memakai port 6543 (transaction pooler) | Migrasi butuh **Session pooler**, port 5432 |
| `db status` bilang `BELUM` padahal tabel ada | Migrasi dijalankan lewat SQL Editor, bukan `db migrate` | Wajar; jalankan `verify_supabase.py` untuk memastikan tabelnya |
| `db migrate` gagal di tengah | Sintaks SQL tidak cocok dengan versi Postgres | Transaksi sudah dibatalkan; perbaiki berkas, ulangi |
| `verify_supabase.py` melaporkan tabel tidak ditemukan | Migrasi belum dijalankan, atau di project lain | Jalankan `python -m db migrate`, periksa nama project |
| `PGRST205` / `42P01` | Tabel belum ada | Sama seperti di atas |
| Aplikasi jalan tetapi mendaftar gagal | `SUPABASE_KEY` salah, atau tabel `users` belum ada | Jalankan verifikasi, periksa kunci `publishable` |
| Project tidak dapat diakses setelah beberapa hari | Supabase Free menjeda project yang tidak aktif | Buka dashboard untuk membangunkan; sudah diperkirakan PRD §19 |
| `verify_supabase.py` melaporkan `applications` ADA | Ada yang membuat tabel di luar scope | Hapus tabel tersebut; lihat PRD §4 |

---

## 10. Keamanan

- Kunci `secret` (`sb_secret_...`) dan `service_role` **tidak** dipakai di aplikasi ini. Keduanya melewati Row Level Security.
- `SUPABASE_DB_PASSWORD` hanya dipakai runner migrasi, tidak pernah oleh aplikasi web.
- `.env` tidak boleh di-commit. Sudah di-ignore sejak PRD-01.
- Pada produksi (PRD-10), kredensial disimpan di environment Render dan GitHub Secrets, bukan di repository.
- Password database dan kunci API adalah dua hal berbeda; jangan mencampurnya.
- Migrasi berjalan dengan hak penuh atas database. Jangan menjalankan `python -m db migrate` pada database produksi tanpa memeriksa `--dry-run` lebih dulu.
