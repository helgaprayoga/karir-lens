# PRD-02 — Data Ingestion

| Field | Keterangan |
|---|---|
| ID task | PRD-02 |
| Nama task | Data Ingestion |
| Prioritas | P0 |
| Milestone | M2 Data pipeline (2-3 hari) |
| Dependensi | PRD-01 |
| Task yang bergantung | PRD-03, PRD-10 |
| Status | Selesai (terbukti di Supabase) |
| PRD induk | [PRD KarirLens](../PRD.md) |

---

## 1. Konteks

KarirLens menggabungkan lowongan dari tiga sumber: Dealls, Kalibrr, dan Remotive. Setelah fondasi proyek (PRD-01) tersedia, task ini membangun jalur pengambilan data mentah dari ketiga sumber tersebut. Setiap sumber memiliki struktur halaman yang berbeda dan berubah dari waktu ke waktu, sehingga pengambilan data harus dipisahkan per sumber (adapter) dan tidak saling bergantung.

Task ini hanya menghasilkan data mentah yang sudah diparse ke struktur objek seragam serta dicatat dalam `scrape_runs`. Normalisasi mendalam, deduplikasi, dan penggabungan lintas sumber dilakukan pada PRD-03.

## 2. Tujuan

1. Menyediakan adapter terpisah untuk Dealls, Kalibrr, dan Remotive dengan antarmuka yang sama.
2. Mengambil lowongan secara sopan: menghormati robots.txt, batas laju, retry, dan user agent yang jelas.
3. Menyimpan data mentah yang valid ke tabel `jobs` beserta `source_url` dan `source_job_id`.
4. Mencatat setiap proses pengambilan data ke `scrape_runs`.
5. Memastikan kegagalan satu sumber tidak menghentikan sumber lain.

## 3. Scope

### 3.1 Termasuk

- Antarmuka adapter: `fetch(page)`, `parse(item)`, `iter_jobs()`, dan metadata sumber.
- Adapter `dealls`, `kalibrr`, dan `remotive`.
- Lapisan HTTP klien bersama: user agent, timeout, retry dengan backoff, dan batas laju per sumber.
- Pemeriksaan robots.txt sebelum mengambil data.
- Pemetaan hasil parse ke struktur objek `RawJob` seragam.
- Penyimpanan awal ke `jobs` dengan `source_id`, `source_url`, `source_job_id`, dan `scraped_at`.
- Pencatatan `scrape_runs` (mulai, selesai, status, jumlah ditemukan, jumlah disimpan, error).
- CLI `python -m scraper run --source <nama|all>` untuk menjalankan ingestion.
- Fixture HTML/JSON untuk pengujian parser.

### 3.2 Tidak termasuk

- Normalisasi field secara menyeluruh dan `dedup_hash` (PRD-03).
- Penggabungan duplikat lintas sumber (PRD-03).
- Penjadwalan GitHub Actions (PRD-10).
- Clustering dan insight (PRD-05).
- Tampilan katalog publik (PRD-04).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-02-01 | Setiap sumber memiliki adapter terpisah yang mengimplementasikan antarmuka `BaseAdapter`. Menambah sumber baru cukup menambah satu modul adapter. | P0 |
| R-02-02 | Adapter menghasilkan objek `RawJob` dengan field minimal: `title`, `company_name`, `location`, `employment_type`, `description`, `skills`, `salary_min`, `salary_max`, `salary_currency`, `salary_period`, `source_url`, `source_job_id`, `posted_at`. Field yang tidak tersedia bernilai `None` atau list kosong, bukan string palsu. | P0 |
| R-02-03 | Klien HTTP memakai user agent dari `SCRAPER_USER_AGENT`, timeout eksplisit, maksimum retry dari `SCRAPER_MAX_RETRY`, dan backoff eksponensial. | P0 |
| R-02-04 | Batas laju per sumber dapat dikonfigurasi dan tidak melebihi 1 permintaan per detik secara default. | P0 |
| R-02-05 | Sistem memeriksa dan menghormati `robots.txt` sebelum mengambil data; jika dilarang, adapter berhenti dengan status `skipped`. | P0 |
| R-02-06 | Setiap eksekusi membuat satu baris `scrape_runs` per sumber dengan status `running`, lalu diperbarui menjadi `success`, `partial`, atau `failed`. | P0 |
| R-02-07 | `jobs_found` menghitung jumlah item yang berhasil diparse; `jobs_inserted` menghitung baris baru yang tersimpan. | P0 |
| R-02-08 | Kegagalan satu sumber dicatat pada `scrape_runs.error_message` dan tidak menghentikan sumber lain saat `--source all`. | P0 |
| R-02-09 | `source_url` disimpan apa adanya dan tetap unik; jika sudah ada, data dianggap sudah ada (detail pembaruan di PRD-03). | P0 |
| R-02-10 | `scraper run --source all` keluar dengan kode 1 jika semua sumber gagal, 0 jika minimal satu sumber sukses. | P1 |
| R-02-11 | Parser memiliki fixture dan unit test; perubahan struktur sumber terdeteksi melalui test. | P0 |
| R-02-12 | Log mencatat nama sumber, jumlah item, durasi, dan error tanpa menulis data pribadi. | P1 |

### 4.1 Antarmuka Adapter

```python
class BaseAdapter:
    name: str
    base_url: str

    def is_allowed(self) -> bool: ...
    def fetch(self, page: int = 1) -> list[dict]: ...
    def parse(self, item: dict) -> RawJob: ...
    def iter_jobs(self, max_pages: int = 5) -> Iterator[RawJob]: ...
```

`RawJob` adalah dataclass dengan field pada R-02-02. Adapter tidak melakukan normalisasi lanjutan atau deduplikasi.

### 4.2 Alur Eksekusi

```text
run(source)
  -> buat scrape_runs(status=running)
  -> cek robots.txt
  -> for page: fetch -> parse -> kumpulkan RawJob
  -> simpan jobs baru (source_url unik)
  -> update scrape_runs(status, jobs_found, jobs_inserted, error)
```

## 5. Acceptance Criteria

- [x] `python -m scraper run --source dealls`, `kalibrr`, dan `remotive` masing-masing berjalan dan menghasilkan data valid.
- [x] `python -m scraper run --source all` menjalankan ketiga adapter; kegagalan satu adapter tidak menghentikan yang lain.
- [x] Minimal satu proses per sumber tercatat di `scrape_runs` dengan status akhir yang benar.
- [x] Setiap `jobs` hasil ingestion memiliki `source_url` yang valid dan `scraped_at`.
- [x] Retry dan backoff teruji dengan simulasi respons 429/500.
- [x] User agent yang dipakai sesuai konfigurasi dan mudah diidentifikasi.
- [x] robots.txt yang melarang dihormati (status `skipped`).
- [x] Unit test parser lulus memakai fixture untuk ketiga sumber.
- [x] Tidak ada duplikasi baris untuk `source_url` yang sama dalam satu eksekusi.

Semua terbukti terhadap database sungguhan; angkanya ada di §12.7.

## 6. Dependensi

- PRD-01 (struktur proyek, koneksi Supabase, skema `jobs` dan `scrape_runs`).
- Akses jaringan ke Dealls, Kalibrr, dan Remotive.
- Pustaka: `requests`, `beautifulsoup4`, `lxml` (opsional), `tenacity` atau retry manual.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_adapter_registry` | Registry memuat tiga adapter dan nama unik. |
| `test_parse_dealls_fixture` | Parser Dealls menghasilkan `RawJob` dengan field wajib. |
| `test_parse_kalibrr_fixture` | Parser Kalibrr menghasilkan `RawJob` dengan field wajib. |
| `test_parse_remotive_fixture` | Parser Remotive menghasilkan `RawJob` dengan field wajib. |
| `test_missing_fields_become_none` | Field tidak tersedia menjadi `None`/list kosong. |
| `test_retry_backoff` | Simulasi 429/500 memicu retry sesuai batas. |
| `test_robots_disallowed` | Adapter berhenti dengan status `skipped`. |
| `test_run_records_scrape_run` | Satu eksekusi membuat dan memperbarui `scrape_runs`. |
| `test_failure_isolation` | Satu adapter gagal; dua lainnya tetap sukses. |
| `test_no_duplicate_source_url` | `source_url` duplikat dalam satu eksekusi tidak disimpan ganda. |

Pengujian parser memakai fixture lokal dan tidak memanggil jaringan.

### 7.2 Pengujian Manual

1. Jalankan satu sumber dan periksa isi `jobs` di Supabase.
2. Jalankan `--source all` dua kali berturut-turut dan pastikan tidak ada baris baru berlebih untuk `source_url` sama.
3. Putuskan jaringan saat satu adapter berjalan dan pastikan dua lainnya tetap selesai.
4. Periksa `scrape_runs` berisi status, jumlah, dan error yang sesuai.

## 8. Out of Scope

- Normalisasi format dan `dedup_hash`.
- Penggabungan lowongan lintas sumber.
- Pembaruan terjadwal dan deployment.
- UI katalog dan insight.
- Fitur pengguna, CV, AI, admin, dan API.

## 9. Catatan Teknis

- Adapter tidak boleh saling memanggil; hanya `scraper/runner.py` yang mengorkestrasi.
- Simpan `source_job_id` bila sumber menyediakannya untuk mempercepat pembaruan pada PRD-03.
- Batasi `max_pages` melalui konfigurasi agar eksekusi lokal tidak terlalu lama.
- Jangan menulis HTML mentah ke log; log cukup berisi ringkasan.
- Perubahan struktur situs sumber dimitigasi dengan fixture dan test parser.

## 10. Referensi Proyek

Proyek utama: **Bot Rekap Lowongan Dealls** (`D:\Semester 5\Praktik Scripting\Pertemuan 9`). Proyek ini sudah mengambil lowongan dari Dealls dengan pola yang sangat dekat dengan kebutuhan PRD-02.

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `scraper.py` — `JobPosting`, `SourceResult`, `ScrapeOutcome` | Struktur dataclass hasil parsing, termasuk `skills: list[str]` dengan factory list kosong, dan pemisahan hasil per sumber sehingga status agregat bisa dihitung dari `sources`. |
| `scraper.py` — `parse_listing()` / `parse_card()` | Pemisahan parser murni (hanya teks HTML, tanpa jaringan) dari kelas pengambil halaman. Parser mengembalikan `None` untuk kartu yang bukan lowongan dan menduplikasi hasil dengan `seen: set[str]`. |
| `scraper.py` — `DeallsScraper` | Implementasi konkret R-02-03 sampai R-02-05: `requests.Session` dengan `HEADERS` dari konfigurasi, `_polite_sleep()` untuk jeda acak, `_backoff(attempt)` eksponensial, `RobotFileParser` untuk `robots.txt`, serta `STOP_STATUS_CODES = {403, 429}` untuk menghentikan pengambilan. |
| `scraper.py` — `scrape_source()` | Kegagalan satu halaman tidak membuang halaman yang sudah terbaca; status turun menjadi `gagal` bila belum ada data, `sebagian` bila sudah ada. |
| `scraper.py` — `run()` | Isolasi kegagalan antar sumber: `RobotsDisallowedError` menghentikan seluruh run, `ScrapeError` hanya menandai sumber itu dan lanjut ke sumber berikutnya. Ini persis R-02-08. |
| `db.py` — `save_outcome()`, `ScrapeOutcome.status` | Nilai status baku (`sukses`, `sebagian`, `gagal`, `diblokir`, `dilarang`) dan pencatatan `scrape_runs` per sumber beserta `pages_scraped`, `jobs_found`, `jobs_new`. |
| `config.py` — `SOURCES`, selector HTML | Sumber data dideklarasikan sebagai list of dict sehingga menambah sumber cukup menambah entri; seluruh selector dikumpulkan di konfigurasi. |
| `scraper.py` — `main()` | Pola CLI dengan `argparse`: `--dry-run`, `--pages`, `--detail`, `--source`, `--json`. Padanan langsung untuk `python -m scraper run --source all`. |
| `tests/test_parser.py` + `tests/fixtures/listing.html`, `tests/fixtures/detail.html` | Parser diuji dengan HTML asli yang disimpan sebagai fixture, tanpa internet. Ini menjadi acuan R-02-11. |

**Cara mengadaptasi ke KarirLens**

1. Ubah `BaseAdapter` menjadi antarmuka dengan `fetch/parse/iter_jobs`, lalu buat `DeallsAdapter`, `KalibrrAdapter`, dan `RemotiveAdapter` mengikuti gaya kelas `DeallsScraper`.
2. Pindahkan `_polite_sleep`, `_backoff`, `load_robots`, dan `ensure_allowed` ke kelas dasar bersama agar ketiga adapter tidak menduplikasi kode.
3. Pakai `RawJob` dengan field PRD-02 sebagai pengganti `JobPosting`, dan `SourceResult`/`ScrapeOutcome` sebagai struktur hasil.
4. Ganti `INSERT OR IGNORE` berbasis `slug` menjadi berbasis `source_url` sesuai skema Supabase.

**Yang tidak diambil**

- SQLite dan skema `jobs` proyek referensi (kolom `slug`, `miss_count`, `is_active`, `detail_checked`). KarirLens memakai Supabase dengan skema PRD-01; konsep `is_active`/`miss_count` tidak termasuk scope.
- Bot Telegram, penjadwalan `JobQueue`, dan `BotTahanGangguan`; penjadwalan KarirLens memakai GitHub Actions di PRD-10.
- Sumber tunggal Dealls. KarirLens memerlukan tiga adapter, dan Kalibrr serta Remotive belum punya proyek referensi — bagian itu dikerjakan tanpa acuan.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Tiga adapter dapat dijalankan melalui CLI.
- `scrape_runs` terisi untuk setiap eksekusi.

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `scraper/http.py` | `ScraperHTTP`: session, user agent, timeout, retry, backoff, robots.txt |
| `scraper/errors.py` | `ScrapeError`, `RobotsDisallowedError`, `ScrapeBlockedError` |
| `scraper/adapters/base.py` | `RawJob` dan `BaseAdapter` dengan `iter_jobs` bersama |
| `scraper/adapters/dealls.py` | Parser HTML + `parse_salary` lima kondisi |
| `scraper/adapters/kalibrr.py` | Parser JSON `kjs/job_board/search` |
| `scraper/adapters/remotive.py` | Parser JSON-LD halaman `/remote-jobs` |
| `scraper/runner.py` | Orkestrasi, isolasi kegagalan, kode keluar |
| `scraper/pipeline/persist.py` | `scrape_runs`, `sources`, dan insert `jobs` |
| `scraper/cli.py` | Logging untuk entrypoint non-web |
| `tests/unit/test_scraper.py` | 35 test untuk §7.1 |
| `tests/fixtures/scraper/` | Fixture HTML dan JSON ketiga sumber |

### 12.2 Keputusan

**`iter_jobs` ada di kelas dasar, bukan di tiap adapter.** Dedup `source_url`, isolasi kegagalan per halaman, dan aturan "halaman kosong berarti habis" berlaku sama untuk ketiga sumber. Menyalinnya tiga kali berarti tiga tempat yang bisa lupa diperbarui.

**`RawJob` punya field `source`.** Skema `jobs` menyimpan `source_id`, bukan nama. Runner memetakannya; adapter tidak perlu tahu id database.

**Nilai yang tidak ada tetap `None`.** Halaman daftar Remotive tidak menyertakan gaji atau perusahaan. Nilai itu dibiarkan kosong, bukan diisi `0` atau `"-"` — angka nol akan lolos ke statistik gaji PRD-05 dan tampil sebagai data yang seolah ada.

**`--dry-run` tidak menyentuh database sama sekali**, termasuk `record_outcome`. Ini membuat perintah itu aman dijalankan berkali-kali untuk memeriksa parser.

**Status `failed` juga dipakai saat nol lowongan berhasil diparse.** Ketiadaan data bukan keberhasilan: bisa berarti struktur halaman berubah dan parser tidak menemukan apa pun. Tanpa penanda ini, kegagalan senyap akan lolos sebagai "sukses".

### 12.3 Temuan Penting: robots.txt Remotive

Endpoint JSON resmi Remotive **dilarang** untuk bot:

```text
# https://remotive.com/robots.txt
User-agent: *
Disallow: /api/*
```

Implementasi pertama saya memakai `/api/remote-jobs` — dan runner **menolaknya** dengan status `skipped`, tepat seperti R-02-05 meminta. Sistemnya benar; rancangan saya yang salah.

Jalur yang diizinkan adalah halaman daftar `/remote-jobs`, yang memuat `ItemList` JSON-LD berisi judul dan URL setiap lowongan. Adapter sekarang memakai itu. Konsekuensinya dinyatakan terbuka: halaman daftar tidak menyertakan perusahaan, gaji, atau deskripsi, sehingga field itu `None`. Pengayaan dari halaman detail dapat ditambahkan kemudian tanpa mengubah kontrak `RawJob`.

`robots.txt` Dealls (`Allow: /`) dan Kalibrr (hanya melarang `/root` dan `/candidate/profile`) memang mengizinkan jalur yang dipakai.

### 12.4 Endpoint Kalibrr

`/api/v1/job_posts` yang saya tulis pertama kali **404**. Endpoint yang benar adalah:

```text
https://www.kalibrr.com/kjs/job_board/search?limit=20&offset=0
```

Diperiksa langsung, bukan ditebak: responsnya JSON berisi `count: 2303` dan larik `jobs` dengan 20 entri. Pemetaan field ditulis setelah melihat bentuk aslinya (`tenure`, `base_salary`, `salary_interval` berupa kode angka, `google_location` berupa JSON string, `job_sds_skills` berupa JSON string).

### 12.5 Tiga Bug yang Hanya Muncul Saat Menulis ke Database Sungguhan

Bagian ini awalnya berjudul "Yang Belum Terbukti". Saya menganggap tidak ada
kredensial Supabase, lalu ternyata `.env` sudah terisi dan seluruh tabel sudah
terbentuk. Menjalankan ingestion sungguhan langsung memunculkan tiga bug yang
tidak tertangkap test mana pun.

**1. CLI tidak pernah mengonfigurasi koneksi Supabase.** Aplikasi web
melakukannya di `create_app`, tetapi pipeline berjalan di luar Flask sehingga
tidak pernah memanggilnya. Akibatnya setiap penulisan gagal dengan "Koneksi
Supabase belum dikonfigurasi" padahal `.env` benar — dan karena kegagalan itu
tertangkap `except` di `pipeline.record_outcome`, hasilnya hanya terlihat
sebagai `partial` di log. Ditambahkan `persist.configure_from_settings()` di
`runner.run` sebelum ada yang menulis.

**2. Parser Dealls hanya berhasil mengambil judul.** Selector saya ditebak
(`[class*='company']`, `[class*='meta']`), sedangkan Dealls memakai kelas
Tailwind sehingga tidak ada kelas semantik sama sekali. Hasilnya 18 baris
tersimpan dengan `company_name`, `location`, dan `employment_type` **NULL
semuanya**. Parser ditulis ulang berdasarkan HTML asli: judul di `<h2>`,
perusahaan di `<div>` setelahnya, dan meta di deretan `<span>`. Sekarang
18/18 untuk ketiga field itu.

**3. `jobs.source_id` kosong pada semua baris.** `RawJob.as_row()` tidak
memuat kolom itu, sehingga relasi ke tabel `sources` hilang meski `source_url`
dan `source_job_id` benar. Diperbaiki dengan mencari `source_id` di
`persist_run` dan meneruskannya ke `as_row(source_id=...)`.

Pelajaran yang saya catat untuk diri sendiri: **test dengan fixture tidak
membuktikan apa pun tentang kode yang berjalan terhadap dunia nyata.** Ketiga
bug ini lolos dari 23 test karena fixture saya menggambarkan HTML yang saya
*kira*, bukan yang ada.

### 12.6 Verifikasi Terukur

`python -m scraper run --source all --pages 1` terhadap Supabase sungguhan:

| Sumber | Status | Ditemukan | Baru |
|---|---|---|---|
| dealls | success | 18 | 18 |
| kalibrr | success | 20 | 20 |
| remotive | success | 20 | 20 |

Isi database setelahnya, dibaca langsung lewat PostgREST:

| Tabel | Baris |
|---|---|
| `sources` | 3 |
| `jobs` | 58 |
| `scrape_runs` | 3 (semua `success`) |

Sebaran `jobs.source_id`: 18 / 20 / 20.

Kualitas field pada 58 baris:

| Field | Terisi | Catatan |
|---|---|---|
| `source_job_id` | 58/58 | |
| `company_name` | 38/58 | Remotive tidak menyertakannya di halaman daftar |
| `location` | 38/58 | sama |
| `employment_type` | 38/58 | sama |
| `posted_at` | 20/58 | hanya Remotive yang menyertakan tanggal |
| `salary_min` | 2/58 | Dealls menulis "Tidak Ditampilkan" untuk sebagian besar |

Keenam angka itu bukan kegagalan: sumbernya memang tidak menyediakan datanya,
dan nilai kosong dibiarkan `None` sesuai R-02-02 alih-alih diisi tebakan.

**Idempotensi.** Menjalankan perintah yang sama dua kali menghasilkan
`baru=0` untuk ketiga sumber; jumlah baris tetap 58. `source_url` unik bekerja
sebagai kunci.

### 12.7 Parser HTML untuk Kalibrr dan Remotive

Revisi setelah user meminta keduanya diambil dari HTML, bukan JSON.

**Kalibrr ternyata memakai ``__NEXT_DATA__``** — konsep yang sama persis dengan
proyek referensi. Satu-satunya beda: tag `<script>` kini membawa atribut
`nonce`, jadi pola `id="__NEXT_DATA__"` harus dicari di mana pun di dalam tag.
Kesalahan itu sempat membuat saya menyimpulkan data Dealls "sudah tidak ada".

| | Sebelum (JSON API) | Sesudah (HTML) |
|---|---|---|
| Kalibrr | `/kjs/job_board/search` | `/job-board` → `__NEXT_DATA__` |
| Remotive | JSON-LD `ItemList` | kartu HTML `li[data-joburl]` |

**Remotive memang tidak punya JSON yang memuat data lengkap.** `ItemList` di
halaman daftar hanya berisi judul dan URL. Yang memuat perusahaan, tipe kerja,
gaji, dan lokasi adalah kartu HTML-nya. Detailnya dari `JobPosting` JSON-LD.

Enam bug yang ditemukan saat mengerjakan ini — semuanya lolos dari fixture
karangan:

1. **`__NEXT_DATA__` dianggap tidak ada** karena regex mengharapkan bentuk tag
   lama. Diperbaiki dan diuji (`test_next_data_survives_nonce_attribute`).
2. **URL detail Kalibrr salah bentuk.** Yang saya susun `/c/{id}`; yang benar
   `/id-ID/c/<perusahaan>/jobs/<id>/<slug>` — dua slug berbeda. Diperbaiki
   dengan menyusun dari `companyInfo.code`; terukur 15/15 valid.
3. **Deskripsi Remotive masuk sebagai HTML mentah** (37.326 karakter berisi
   `<p>`, `<ul>`, `&amp;`). Ditambahkan pembersih yang mempertahankan baris per
   butir; sekarang teks bersih 4.203 karakter.
4. **Tanggal Dealls tidak pernah terisi.** Kartu daftar hanya punya "1h lalu";
   `publishedAt` absolut ada di `__NEXT_DATA__` halaman detail.
5. **Deskripsi Dealls kosong.** Tidak ada field `description`; isinya terbagi
   menjadi `responsibilities` dan `requirements`.
6. **Skill Dealls tidak terambil.** Ada di `candidatePreference.skills` halaman
   detail, bukan di kartu daftar.

### 12.8 Kualitas Data Terukur

`python -m scraper run --source all --pages 1 --detail`, hasil dibaca dari
database:

| Field | Total | Dealls | Kalibrr | Remotive |
|---|---|---|---|---|
| `company_name` | 49/49 | 18/18 | 15/15 | 16/16 |
| `location` | 49/49 | 18/18 | 15/15 | 16/16 |
| `employment_type` | 49/49 | 18/18 | 15/15 | 16/16 |
| `posted_at` | 49/49 | 18/18 | 15/15 | 16/16 |
| `description` | 49/49 | 18/18 | 15/15 | 16/16 |
| `skills` | 17/49 | 17/18 | 0/15 | 0/16 |

Empat field pertama kini **lengkap di ketiga sumber**, dari sebelumnya 38/58
karena Remotive hanya memberi judul.

Skill 0 di Kalibrr/Remotive bukan kegagalan: keduanya tidak punya field skill,
dan penurunannya dikerjakan PRD-03 lewat `core/skills.py` yang sudah siap.
Rinciannya di [`TEMUAN-sumber-skill.md`](./TEMUAN-sumber-skill.md).

Total test setelah task ini: **327 lulus**.
