# PRD-02 — Data Ingestion

| Field | Keterangan |
|---|---|
| ID task | PRD-02 |
| Nama task | Data Ingestion |
| Prioritas | P0 |
| Milestone | M2 Data pipeline (2-3 hari) |
| Dependensi | PRD-01 |
| Task yang bergantung | PRD-03, PRD-10 |
| Status | Belum dimulai |
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

- [ ] `python -m scraper run --source dealls`, `kalibrr`, dan `remotive` masing-masing berjalan dan menghasilkan data valid.
- [ ] `python -m scraper run --source all` menjalankan ketiga adapter; kegagalan satu adapter tidak menghentikan yang lain.
- [ ] Minimal satu proses per sumber tercatat di `scrape_runs` dengan status akhir yang benar.
- [ ] Setiap `jobs` hasil ingestion memiliki `source_url` yang valid dan `scraped_at`.
- [ ] Retry dan backoff teruji dengan simulasi respons 429/500.
- [ ] User agent yang dipakai sesuai konfigurasi dan mudah diidentifikasi.
- [ ] robots.txt yang melarang dihormati (status `skipped`).
- [ ] Unit test parser lulus memakai fixture untuk ketiga sumber.
- [ ] Tidak ada duplikasi baris untuk `source_url` yang sama dalam satu eksekusi.

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
