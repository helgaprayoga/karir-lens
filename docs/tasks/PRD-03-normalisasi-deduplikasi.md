# PRD-03 — Normalisasi dan Deduplikasi

| Field | Keterangan |
|---|---|
| ID task | PRD-03 |
| Nama task | Normalisasi dan Deduplikasi |
| Prioritas | P0 |
| Milestone | M2 Data pipeline (2-3 hari) |
| Dependensi | PRD-01, PRD-02 |
| Task yang bergantung | PRD-04, PRD-05, PRD-07, PRD-08 |
| Status | Selesai (terbukti di Supabase) |
| PRD induk | [PRD KarirLens](../PRD.md) |

---

## 1. Konteks

Data mentah dari PRD-02 memiliki format berbeda per sumber. Judul, perusahaan, lokasi, tipe kerja, deskripsi, skill, dan gaji perlu diseragamkan sebelum dapat ditampilkan. Selain itu, lowongan yang sama dapat muncul lebih dari sekali: dari tautan yang sama, atau dari sumber berbeda dengan penulisan berbeda.

Task ini menambahkan lapisan normalisasi dan deduplikasi yang dapat diuji terpisah, menghasilkan `dedup_hash`, serta memperbarui data yang sudah ada tanpa membuat duplikat (idempoten).

## 2. Tujuan

1. Menyeragamkan seluruh field lowongan ke format konsisten di database.
2. Mencegah duplikat berdasarkan `source_url` dan `dedup_hash`.
3. Menggabungkan atau menandai duplikat lintas sumber tanpa menghilangkan tautan asli.
4. Membuat proses ingestion idempoten: pengambilan ulang memperbarui, bukan menggandakan.
5. Mencatat hasil pembersihan pada `scrape_runs`.

## 3. Scope

### 3.1 Termasuk

- Normalizer untuk `title`, `company_name`, `company_slug`, `location`, `employment_type`, `description`, `skills`, `salary_*`, dan `posted_at`.
- Pembersihan teks: whitespace, HTML entity, tag HTML, dan kapitalisasi yang tidak relevan.
- Normalisasi tipe kerja ke himpunan nilai baku.
- Normalisasi gaji: `salary_min`, `salary_max`, `salary_currency`, `salary_period`.
- `dedup_hash` berbasis judul + perusahaan + lokasi yang sudah dinormalisasi.
- Logika insert-or-update berdasarkan `source_url` dan `dedup_hash`.
- Penandaan duplikat lintas sumber (kolom atau catatan keputusan).
- Pengujian unit untuk normalizer dan deduplikator.

### 3.2 Tidak termasuk

- Pengambilan data mentah (PRD-02).
- Clustering dan statistik (PRD-05).
- Tampilan katalog dan filter (PRD-04).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-03-01 | Normalizer adalah fungsi murni yang dapat diuji tanpa database. | P0 |
| R-03-02 | `title` dan `company_name` di-trim, whitespace ganda dirapikan, dan HTML entity di-decode. | P0 |
| R-03-03 | `company_slug` diturunkan dari `company_name`: lowercase, karakter non-alfanumerik menjadi `-`, tanpa `-` di awal/akhir. | P0 |
| R-03-04 | `employment_type` dipetakan ke himpunan baku: `full-time`, `part-time`, `contract`, `internship`, `freelance`, `unknown`. Varian seperti "Full Time", "Fulltime", "Kontrak", dipetakan konsisten. | P0 |
| R-03-05 | `description` dibersihkan dari tag HTML, whitespace berlebih, dan baris kosong berlebih. Panjang maksimum disimpan wajar (mis. 20.000 karakter) dengan pemotongan yang jelas. | P0 |
| R-03-06 | `skills` dinormalisasi: lowercase, trim, deduplikasi, dan diurutkan. Skill kosong atau terlalu pendek dibuang. | P0 |
| R-03-07 | Gaji dinormalisasi ke angka: `salary_min <= salary_max`, angka negatif atau nol tidak valid, mata uang uppercase tiga huruf, periode pada himpunan `month`, `year`, `hour`, `day`, `project`. Gaji parsial (hanya min atau maks) disimpan apa adanya dengan field lain kosong. | P0 |
| R-03-08 | `dedup_hash` dihitung dari gabungan `title`, `company_name`, dan `location` yang sudah dinormalisasi menggunakan hash stabil. | P0 |
| R-03-09 | Baris dengan `source_url` sama diperbarui (bukan digandakan). Baris dengan `dedup_hash` sama dan sumber berbeda ditandai sebagai duplikat. | P0 |
| R-03-10 | Tautan asli (`source_url`) tetap disimpan untuk semua baris; penggabungan tidak menghapus sumber. | P0 |
| R-03-11 | Data tidak lengkap tetap disimpan dengan `None`/list kosong yang jelas; tidak diisi nilai palsu. | P0 |
| R-03-12 | Proses insert-or-update idempoten: menjalankan ingestion dua kali tidak menambah baris duplikat. | P0 |
| R-03-13 | `scrape_runs.jobs_updated` mencatat jumlah baris yang diperbarui. | P0 |
| R-03-14 | Normalisasi tidak memanggil AI atau layanan eksternal. | P0 |

### 4.1 Aturan Normalisasi

| Field | Aturan |
|---|---|
| `title` | Trim, collapse whitespace, decode entity, pertahankan kapitalisasi asli. |
| `company_name` | Trim, collapse whitespace, hapus sufiks legal umum (`PT`, `Inc`, `Ltd`) secara konsisten bila perlu. |
| `company_slug` | Lowercase, `[^a-z0-9]+` → `-`, trim `-`. |
| `location` | Trim, pisahkan kota dan negara bila tersedia; simpan bentuk baku `Kota, Negara` bila keduanya ada. |
| `employment_type` | Petakan ke himpunan baku; nilai tak dikenal → `unknown`. |
| `description` | Strip HTML, decode entity, rapikan whitespace dan baris kosong. |
| `skills` | Lowercase, trim, dedup, sort, buang kosong dan < 2 karakter. |
| `salary_min`, `salary_max` | Numerik, tidak negatif, `min <= max`. |
| `salary_currency` | Uppercase ISO-4217 bila dapat dikenali; kosong jika tidak. |
| `salary_period` | Salah satu dari `month`, `year`, `hour`, `day`, `project`; kosong jika tidak jelas. |
| `posted_at` | ISO-8601 UTC; kosong jika tidak tersedia. |

### 4.2 Alur Deduplikasi

```text
RawJob
  -> normalize()
  -> dedup_hash = hash(title|company_name|location)
  -> if source_url exists: update baris
  -> elif dedup_hash exists dengan sumber berbeda: tandai duplikat (simpan tautan asli)
  -> else: insert baris baru
```

## 5. Acceptance Criteria

- [x] Tidak ada baris ganda berdasarkan `source_url`.
- [x] Baris dengan `dedup_hash` sama dan sumber berbeda tertandai sebagai duplikat, bukan dihapus diam-diam.
- [x] Semua lowongan yang tampil memiliki format konsisten (tipe kerja baku, skill lowercase, gaji valid).
- [x] Ingestion dijalankan dua kali berturut-turut tidak menambah baris baru untuk data yang sama.
- [x] `jobs_updated` bertambah saat data yang sama diambil ulang dengan perubahan.
- [x] Data tidak lengkap tersimpan dengan nilai kosong yang jelas.
- [x] Setiap baris tetap memiliki `source_url` asli.
- [x] Unit test normalizer dan deduplikator lulus dan tidak memerlukan jaringan.

Bukti terukur ada di §12.

## 6. Dependensi

- PRD-01 (skema database).
- PRD-02 (adapter dan struktur `RawJob`).
- Pustaka: `beautifulsoup4`/`lxml` untuk strip HTML, `python-dateutil` untuk parsing tanggal bila diperlukan.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_normalize_title_whitespace` | Whitespace dan entity dirapikan. |
| `test_company_slug_generation` | Slug konsisten untuk penulisan berbeda. |
| `test_employment_type_mapping` | Seluruh varian terpetakan ke himpunan baku. |
| `test_description_strip_html` | Tag HTML dan entity hilang. |
| `test_skills_dedup_and_order` | Skill lowercase, unik, terurut. |
| `test_salary_normalization` | `min <= max`, nilai tidak valid ditolak, periode baku. |
| `test_dedup_hash_stable` | Hash stabil untuk input setara dan berbeda untuk input berbeda. |
| `test_insert_or_update_idempotent` | Dua eksekusi tidak menambah duplikat. |
| `test_cross_source_duplicate_flag` | Duplikat lintas sumber tertandai dan tautan asli tetap ada. |
| `test_incomplete_data_saved` | Field kosong tersimpan sebagai `None`/list kosong. |

### 7.2 Pengujian Manual

1. Jalankan ingestion satu sumber, periksa konsistensi field di `jobs`.
2. Jalankan ulang dan pastikan `jobs_updated` bertambah tanpa baris baru.
3. Cari satu lowongan yang muncul dari dua sumber dan periksa penandaan duplikat.
4. Periksa gaji pada data campuran (hanya min, hanya maks, lengkap).

## 8. Out of Scope

- Clustering, insight, dan rekomendasi.
- UI pencarian dan detail lowongan.
- Penjadwalan dan deployment.
- Pembersihan retensi berkala atas data lama.

## 9. Catatan Teknis

- Normalizer dan deduplikator adalah modul murni di bawah `scraper/pipeline/normalize.py` dan `scraper/pipeline/dedup.py`, sehingga dapat diuji tanpa jaringan maupun database ([Arsitektur Kode §6](../ARCHITECTURE.md)).
- `dedup_hash` menggunakan hash stabil (mis. SHA-256 atas string ternormalisasi), bukan hash Python yang bergantung seed.
- Aturan penggabungan perusahaan berbeda penulisan (pertanyaan terbuka PRD induk) memakai pendekatan konservatif: normalisasi ringan, tidak menggabungkan entitas secara agresif.
- Kolom pencatatan duplikat ditambahkan melalui migrasi; jangan menghapus baris otomatis.

## 10. Referensi Proyek

Tidak ada proyek referensi yang melakukan deduplikasi lintas sumber. Yang tersedia hanya pola penyimpanan akumulatif dan normalisasi skill dari **Bot Rekap Lowongan Dealls** (`D:\Semester 5\Praktik Scripting\Pertemuan 9`).

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `db.py` — `save_outcome()` | Pola insert-or-update idempoten: `INSERT OR IGNORE` lalu `UPDATE ... WHERE slug IN (...)` untuk memperbarui `last_seen_at` tanpa menggandakan baris. Ini acuan langsung R-03-09 dan R-03-12. |
| `db.py` — `skills_to_json()`, `skills_from_text()`, `skills_to_display()` | Skill disimpan sebagai JSON karena nama skill sumber mengandung koma (`Excel (VLOOKUP, HLOOKUP, PIVOT...)`). Pembacaan mendukung format JSON baru dan format koma lama agar data lama tetap terbaca. Menjadi acuan R-03-06. |
| `db.py` — `mark_detail_checked()` | Menyimpan skill hasil pengambilan detail hanya bila daftar tidak kosong (`CASE WHEN ? <> '' THEN ? ELSE skills_text END`), supaya pengambilan ulang tidak menghapus skill yang sudah ada. |
| `db.py` — `_migrasi()` | Pola menambah kolom baru pada tabel lama tanpa membuang data, relevan untuk kolom penanda duplikat pada R-03-09. |
| `scraper.py` — `_clean()`, `slug_from_href()`, `_split_location()` | Utilitas normalisasi teks: `WHITESPACE_RE.sub(" ", text).strip()`, pemisahan mode kerja dan kota dengan `LOCATION_SEPARATOR`, serta pembentukan slug dari URL. Menjadi acuan R-03-02 dan R-03-03. |
| `scraper.py` — `parse_card()` | Klasifikasi baris meta berdasarkan isi (bukan urutan) memakai `_is_job_type()`, `_is_experience()`, `_is_salary()`. Ini acuan R-03-04 dan R-03-07. |
| `tests/test_skill_backfill.py` | Pola pengujian backfill skill yang belum tersimpan, berguna untuk menguji idempotensi tanpa jaringan. |

**Cara mengadaptasi ke KarirLens**

1. Pindahkan `_clean`, `_split_location`, dan pembentukan slug ke modul `scraper/normalize.py` sebagai fungsi murni.
2. Pakai pola JSON untuk `jobs.skills` — di Supabase gunakan kolom `text[]`, tetapi logika deduplikasi dan pengurutan tetap mengikuti `skills_to_json`.
3. Terapkan pola `INSERT` lalu `UPDATE` dari `save_outcome()` sebagai acuan insert-or-update berbasis `source_url`.
4. Tambahkan `dedup_hash` sebagai lapisan baru di atas pola tersebut; proyek referensi tidak memilikinya, jadi bagian ini dikerjakan tanpa acuan.

**Yang tidak diambil**

- `is_active` dan `miss_count` (penonaktifan lowongan setelah N run). Di luar scope KarirLens; lowongan tidak ditandai tidak aktif.
- Kunci unik berbasis `slug`. KarirLens memakai `source_url` dan `dedup_hash` sesuai skema PRD-01.
- Pendekatan penggabungan agresif antar perusahaan. Proyek referensi hanya memakai satu sumber, sehingga aturan penggabungan lintas sumber tidak punya acuan dan tetap konservatif sesuai §9.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Proses ingestion terbukti idempoten.
- `dedup_hash` dan aturan normalisasi terdokumentasi di README teknis.

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `core/text.py` | Bersihkan teks, `slugify`, `split_location` |
| `core/skills.py` | `normalize_skills` untuk skill deklaratif (dari PRD-02 lanjutan) |
| `scraper/pipeline/normalize.py` | Seluruh aturan §4.1, fungsi murni |
| `scraper/pipeline/dedup.py` | `compute_hash` SHA-256, `is_duplicate`, `group_by_hash` |
| `scraper/pipeline/persist.py` | `upsert`, `find_duplicate`, penandaan duplikat |
| `scraper/pipeline/__init__.py` | Menyambungkan `normalize` + `dedup` ke `persist_run` |
| `scraper/runner.py` | Hitungan `inserted`/`updated`/`duplicate` per sumber |
| `migrations/003_dedup_marker.sql` | Kolom `duplicate_of` dan `dedup_source` |
| `migrations/004_skill_origin.sql` | Kolom `skills_source` (`declared`/`inferred`) |
| `tests/unit/test_normalize.py` | 29 test untuk §7.1 dan asal skill |

### 12.2 Keputusan

**SHA-256, bukan `hash()`.** ``hash()`` untuk string diacak per proses sejak
Python 3.3 (PYTHONHASHSEED). Hash yang berubah setiap proses akan membuat
seluruh baris terlihat baru pada setiap eksekusi — tepat masalah yang ingin
dicegah R-03-12.

**Pemisah `\x1f` antar-field.** Tanpa itu, ``title="AB"`` + ``company="C"``
bertabrakan dengan ``title="A"`` + ``company="BC"``. Diuji
(`test_dedup_hash_field_separator`).

**Gaji `min > max` ditukar, bukan dibuang.** Kemungkinan besar urutannya
tertukar di sumber, dan datanya tetap berguna. Nol dan negatif dibuang: itu
ketiadaan data, bukan gaji.

**`employment_type` mengeluarkan `unknown`, bukan `None`.** Tampilan perlu
membedakan "tidak disebutkan" dari "belum dicoba"; `None` menyamakan keduanya.

**`slugify` terpisah dari `normalize_text`.** `normalize_text` sengaja
mempertahankan `+`, `#`, `.` untuk nama skill (`c++`, `node.js`). Pada slug,
"PT. Digivana" harus menjadi `pt-digivana`, bukan `pt.-digivana`. Bug ini
ditemukan dari data nyata, bukan dari test.

### 12.3 Satu Asumsi yang Terbukti Salah

Rencana awal: "satu sumber tidak menduplikasi dirinya sendiri", sehingga
`find_duplicate` menyaring per `source_id`. Data nyata membantahnya — Remotive
memuat **dua lowongan kembar** dengan ID berbeda:

| `source_job_id` | Judul | Perusahaan |
|---|---|---|
| 2091166 | Content Reviewer - United States | TELUS Digital |
| 2091177 | Content Reviewer - United States | TELUS Digital |

Penyaringan per sumber karena itu dihapus; yang disaring hanya `source_url`
yang sama, karena itu baris yang sama. Sekarang keduanya tersimpan dengan
`duplicate_of` menunjuk yang pertama.

### 12.4 Verifikasi Terukur

Dua eksekusi berturut-turut dari database kosong:

| Run | Dealls | Kalibrr | Remotive |
|---|---|---|---|
| 1 | 18 baru | 15 baru | 15 baru + **1 duplikat** |
| 2 | 0 baru, 18 diperbarui | 0 baru, 15 diperbarui | 0 baru, 16 diperbarui |

Total tetap **49 baris** setelah run kedua. Isi database:

| Pemeriksaan | Hasil |
|---|---|
| `dedup_hash` terisi | 49/49, panjang 64 karakter |
| `company_slug` terisi | 49/49 |
| `title`/`company_name`/`description` berisi HTML | 0 |
| `employment_type` di luar himpunan baku | 0 |
| Baris bertanda duplikat | 1, `duplicate_of` menunjuk baris induk |

`employment_type` akhir: `full-time` 36, `contract` 6, `part-time` 2,
`freelance` 1, `internship` 1, `unknown` 3. Ketiga `unknown` berasal dari
Remotive yang memang tidak mencantumkan tipe kerja pada kartunya — bukan bug
pemetaan.

Total test setelah task ini: **391 lulus**.

### 12.5 Inferensi Skill untuk Sumber Tanpa Field Skill

Dealls menyatakan skill-nya sendiri (`candidatePreference.skills`); Kalibrr dan
Remotive hanya punya prosa. Sebelum bagian ini, `core/skills.py` sudah ada dan
diuji tetapi **tidak pernah dipanggil**, sehingga 32 dari 49 lowongan tampil
tanpa satu pun skill di kartunya sementara kartu Dealls penuh.

`normalize()` sekarang memutuskan asalnya lewat
`normalize_skills_with_origin()`:

| Kondisi | `skills` | `skills_source` |
|---|---|---|
| Sumber menyatakan skill | hasil normalisasi | `declared` |
| Sumber hanya punya prosa | hasil `infer_skills()` | `inferred` |
| Tidak ada yang ditemukan | `[]` | `None` |

`infer_skills()` memakai tiga tingkat presisi (judul → bagian syarat → kalimat
ber-penanda), dan membuang dua sumber salah cocok yang terukur pada data nyata:
*boilerplate* perekrut di atas syarat sebenarnya, serta syarat perangkat
("smartphone (Android 5.0, iOS 14 or higher)"). Alias kamus `rest` dan `dl`
dihapus karena keduanya kata biasa dalam prosa Inggris.

Hasil terukur: 19 `declared`, 8 `inferred`, 27 kosong dari 54 baris. Rincian
dan alasan memilih presisi di atas cakupan ada di
[TEMUAN-sumber-skill.md](./TEMUAN-sumber-skill.md).
