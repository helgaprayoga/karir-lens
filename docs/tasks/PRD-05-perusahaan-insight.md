# PRD-05 — Perusahaan dan Insight

| Field | Keterangan |
|---|---|
| ID task | PRD-05 |
| Nama task | Perusahaan dan Insight (Backend) |
| Track | B — Backend |
| Prioritas | P0 |
| Milestone | M4 Insight (2 hari) |
| Dependensi | PRD-03, PRD-04, PRD-F05 |
| Task yang bergantung | PRD-08, PRD-09 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F05](./PRD-F05-insight-admin.md) |

---

## 1. Konteks

Halaman `/insights`, `/companies/<slug>`, dan seluruh tampilan insight sudah dibangun pada PRD-F05 dan PRD-F02, termasuk grafik Chart.js, kartu statistik, dan state "data terbatas". Task ini mengisi perhitungan di belakangnya: pipeline clustering TF-IDF/PCA/KMeans, agregasi kategori dan skill, serta statistik gaji.

Prinsip yang sudah tertanam di template: statistik gaji tidak muncul bila sampel kurang dari lima, mata uang tidak dicampur, dan tidak ada angka prediksi. Task ini memastikan service menghasilkan data yang membuat template itu bekerja benar — bukan sebaliknya.

Keluaran task ini wajib memenuhi **kontrak template PRD-F05 §4.1**.

## 2. Tujuan

1. Mengelompokkan lowongan memakai TF-IDF, PCA, dan KMeans.
2. Menghitung distribusi kategori dan skill populer.
3. Menghitung statistik gaji faktual dengan aturan sampel minimum.
4. Menyediakan hasil clustering yang dapat ditinjau admin.
5. Menyediakan service insight yang dipakai ulang REST API.

## 3. Scope

### 3.1 Termasuk

- `scraper/cluster.py`: TF-IDF → PCA → KMeans, label dan kata kunci per cluster, penyimpanan idempoten.
- `app/insights/repository.py`: query agregasi kategori, skill, gaji, dan perusahaan.
- `app/insights/salary.py`: median, P25, P75, aturan sampel ≥ 5, pemisahan mata uang.
- `app/insights/service.py`: fungsi yang mengisi kontrak PRD-F05 §4.1 dan PRD-F02 §4.1.
- CLI `python -m scraper cluster`.
- Menonaktifkan route preview untuk insight dan perusahaan.

### 3.2 Tidak termasuk

- Markup, CSS, JavaScript, dan konfigurasi Chart.js (selesai pada PRD-F05).
- Profil resmi perusahaan, logo, rating, jumlah karyawan.
- Tinjauan UI cluster di admin (tampilan di PRD-F05, data di sini).
- Rekomendasi berbasis CV (PRD-07).
- Prediksi gaji dalam bentuk apa pun.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-05-01 | Clustering memakai TF-IDF atas `title` + `description` + `skills` dengan preprocessing dari `core/text.py` dan `core/skills.py`. | P0 |
| R-05-02 | PCA diterapkan sebelum KMeans; `n_clusters` dan komponen PCA dibaca dari konfigurasi. | P0 |
| R-05-03 | Setiap cluster memiliki `label` dan `keywords` yang dapat dibaca manusia. | P0 |
| R-05-04 | Setiap lowongan memiliki paling banyak satu `cluster_id`. | P0 |
| R-05-05 | Menjalankan clustering dua kali tidak menggandakan cluster (idempoten). | P0 |
| R-05-06 | `get_categories()` mengembalikan `cluster_id`, `label`, `job_count`, `keywords`. | P0 |
| R-05-07 | `get_top_skills(limit)` mengembalikan skill dan jumlah lowongan. | P0 |
| R-05-08 | `get_salary_stats()` hanya memakai lowongan bergaji dan menyembunyikan kelompok dengan sampel < 5. | P0 |
| R-05-09 | Statistik gaji mengembalikan median, P25, P75, dan sampel, dipisah per `salary_currency` dan `salary_period`. | P0 |
| R-05-10 | Tidak ada field prediksi pada keluaran mana pun. | P0 |
| R-05-11 | `sample_sufficient` bernilai `false` bila tidak ada kelompok yang memenuhi syarat, agar template menampilkan pesan data terbatas. | P0 |
| R-05-12 | `get_company(slug)` mengembalikan `name`, `slug`, `job_count`, `locations`, `employment_types`, `top_skills`, `jobs`. | P0 |
| R-05-13 | Clustering dijalankan sebagai proses terpisah, tidak pernah dari request web. | P0 |
| R-05-14 | Keluaran service memenuhi kontrak PRD-F05 §4.1 tanpa perubahan template. | P0 |
| R-05-15 | Insight dapat dihitung ulang dari PRD-10 tanpa mengubah kode web. | P1 |

### 4.1 Aturan Statistik Gaji

| Aturan | Nilai |
|---|---|
| Sumber data | Hanya `jobs` dengan `salary_min` dan/atau `salary_max` valid. |
| Sampel minimum | 5 lowongan per kelompok statistik. |
| Ukuran | Median, P25, P75, jumlah sampel. |
| Pemisahan | Per `salary_currency`; tidak mencampur mata uang. |
| Periode | Statistik dipisah per `salary_period` bila campuran. |
| Prediksi | Tidak ada. |

### 4.2 Struktur Hasil Insight

```json
{
  "categories": [ { "cluster_id": 1, "label": "Backend", "job_count": 120, "keywords": ["python", "api"] } ],
  "skills": [ { "skill": "python", "job_count": 210 } ],
  "salary": [ { "currency": "IDR", "period": "month", "sample": 42, "median": 9000000, "p25": 7000000, "p75": 12000000 } ]
}
```

## 5. Acceptance Criteria

- [ ] Proses clustering menghasilkan cluster yang dapat ditampilkan dan ditinjau.
- [ ] Setiap lowongan memiliki paling banyak satu `cluster_id` utama.
- [ ] Menjalankan clustering dua kali tidak menggandakan cluster.
- [ ] Service mengembalikan kategori dan skill yang sesuai isi database.
- [ ] Statistik gaji tidak dikembalikan bila sampel < 5, dan tidak ada nilai prediksi.
- [ ] Mata uang dan periode tidak dicampur dalam satu kelompok statistik.
- [ ] `sample_sufficient` bernilai `false` saat data belum mencukupi.
- [ ] `get_company` hanya mengembalikan data turunan `jobs`.
- [ ] Keluaran service memenuhi kontrak PRD-F05 §4.1 tanpa mengubah template.
- [ ] Clustering hanya berjalan lewat CLI, tidak dari request web.

## 6. Dependensi

- PRD-03 (data ternormalisasi dan konsisten).
- PRD-04 (service query dasar dan `core/pagination.py`).
- PRD-F05 (template dan kontrak data insight serta admin).
- Pustaka: `scikit-learn`, `pandas`, `numpy`.
- Data lowongan yang cukup untuk clustering dan statistik dasar.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_tfidf_vectorization` | Vektor TF-IDF terbentuk dari input gabungan. |
| `test_clustering_labels_generated` | Setiap cluster memiliki label dan keywords tidak kosong. |
| `test_clustering_idempotent` | Menjalankan ulang tidak menggandakan cluster. |
| `test_single_cluster_per_job` | Lowongan memiliki paling banyak satu `cluster_id`. |
| `test_salary_min_sample_rule` | Kelompok dengan sampel < 5 tidak dikembalikan. |
| `test_salary_currency_separation` | Mata uang tidak dicampur. |
| `test_salary_period_separation` | Periode berbeda tidak dicampur. |
| `test_salary_quartiles` | Median, P25, P75 dihitung benar pada fixture. |
| `test_no_prediction_output` | Tidak ada field prediksi pada hasil. |
| `test_sample_sufficient_flag` | Flag `false` saat tidak ada kelompok memenuhi syarat. |
| `test_insights_counts_match_db` | Jumlah kategori dan skill sesuai data uji. |
| `test_company_derived_from_jobs_only` | Keluaran perusahaan hanya dari data `jobs`. |
| `test_service_matches_insight_contract` | Kunci `dict` sama dengan kontrak PRD-F05 §4.1. |

Pengujian statistik memakai fixture dataset kecil yang deterministik.

### 7.2 Pengujian Manual

1. Jalankan clustering pada data uji dan tinjau label serta kata kunci.
2. Buka `/insights` dan cocokkan angka dengan query database.
3. Periksa tampilan grafik pada 360 px dan 1280 px.
4. Uji kondisi sampel gaji < 5 dan pastikan pesan data terbatas tampil.
5. Buka halaman perusahaan dan periksa daftar lowongan, skill, tipe kerja, dan lokasi.

## 8. Out of Scope

- Prediksi gaji dan analisis sentimen.
- Ulasan perusahaan dan profil resmi perusahaan (logo, rating, jumlah karyawan, alamat).
- Katalog publik dasar dan detail lowongan (PRD-04).
- Tinjauan UI cluster di admin (data disediakan; UI di PRD-09).
- Rekomendasi berbasis CV (PRD-07).

## 9. Catatan Teknis

- Clustering dijalankan sebagai proses terpisah (`python -m scraper cluster`) dan tidak dijalankan per permintaan web.
- Simpan parameter clustering (`n_clusters`, komponen PCA) di konfigurasi agar dapat diulang.
- Statistik gaji dapat di-cache, tetapi harus dapat dihitung ulang.
- Label cluster sebaiknya diberi nama manual atau berbasis kata kunci teratas agar dapat dipahami.
- Pisahkan service insight dari route agar dapat dipakai API.

## 10. Referensi Proyek

Dua proyek referensi, dipakai untuk bagian yang berbeda.

### 10.1 Clustering — Dashboard Analisis PLN (`D:\Semester 5\Praktik Aplikasi Web\pln_analysis`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `tabs/tab_clustering.py` — `get_stopwords()` | Penggabungan stopword Bahasa Indonesia dan Inggris plus `EXTRA_STOPWORDS` (kata informal seperti `yg`, `aja`, `banget`). Acuan R-05-01 untuk preprocessing teks lowongan. |
| `tabs/tab_clustering.py` — `create_wordcloud_frequencies()` | `TfidfVectorizer(stop_words=..., min_df=2, max_df=0.9)` atas `clean_text`, lalu selisih rata-rata vektor cluster terhadap cluster lain (`np.clip(cluster_center - other_centers, 0, None)`) untuk mendapatkan kata dominan per cluster. Ini acuan langsung R-05-03 (label dan kata kunci per cluster). |
| `tabs/tab_clustering.py` — `create_cluster_coordinates()` | `PCA(n_components=2, random_state=42).fit_transform(matrix.toarray())` beserta fallback bila dimensi fitur kurang dari dua. Acuan R-05-02. |
| `tabs/tab_clustering.py` — `show_cluster_visualization()`, `show_wordclouds()` | Penyajian sebaran cluster dan wordcloud per cluster, termasuk penanganan cluster tanpa kata dominan (`st.info("Tidak ada kata dominan.")`). Acuan R-05-11. |
| `tabs/tab_clustering.py` — `render_tab_clustering()` | Pesan data terbatas: `st.warning("File ... belum ditemukan")` dan `st.error(...)` untuk kolom yang hilang, bukan grafik kosong. Ini persis R-05-11. |
| `tabs/tab_clustering.py` — blok "Tema dan Kata Dominan" | Kolom `nama_tema` dibaca dari hasil clustering, ditampilkan sebagai label cluster yang dapat dipahami. Acuan R-05-03. |
| `requirements.txt` | `scikit-learn`, `pandas`, `numpy`. Konfirmasi pustaka yang dipakai; KarirLens menambahkan `wordcloud` hanya bila grafik kata diperlukan. |

### 10.2 Grafik dan Ringkasan Insight — Bot Utang-Piutang (`D:\Semester 5\Praktik Scripting\Pertemuan 8`)

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `static/js/dashboard.js` — `state.charts`, `destroyChart()`, `tampilkanChart()` | Pola Chart.js: satu registry `state.charts`, hancurkan grafik lama sebelum membuat yang baru (`destroyChart(key)`), lalu `new Chart(canvas, config)`. Ini acuan R-05-13 agar grafik aman saat data diperbarui. |
| `static/js/dashboard.js` — `WARNA` | Palet warna terpusat untuk konsistensi antar grafik, termasuk versi transparan (`rgba(...)`) untuk area. |
| `static/js/dashboard.js` — `formatRupiah()`, `formatRupiahSingkat()`, `formatBulan()` | `Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR" })` dan `notation: "compact"` untuk sumbu grafik. Acuan R-05-09 agar median dan kuartil gaji tampil konsisten. |
| `database.py` — `ringkasan_web()` | Ringkasan agregat dalam satu query dengan `COALESCE(SUM(CASE WHEN ...))`, mengembalikan dict siap tampil ke kartu dashboard. Pola yang sama dipakai untuk ringkasan insight. |
| `database.py` — `sisa_per_nama()`, `pembayaran_per_bulan()` | Agregasi `GROUP BY` untuk grafik, termasuk pengisian bulan kosong dengan nilai nol agar grafik tetap rapi. Padanan untuk distribusi kategori dan tren. |
| `web.py` — `api_dashboard()` | Satu endpoint JSON menyatukan `ringkasan`, daftar, dan semua seri grafik. Acuan R-05-15 (service insight untuk `/api/insights/*`). |
| `templates/dashboard.html`, `static/vendor/chart.umd.min.js` | Chart.js dipakai secara lokal (vendor), bukan CDN, sehingga tidak bergantung jaringan saat demo. |

**Cara mengadaptasi ke KarirLens**

1. Buat `scraper/cluster.py` dengan alur TF-IDF → PCA → KMeans. Ambil `get_stopwords()` dan `create_wordcloud_frequencies()` dari `tab_clustering.py`, lalu simpan label dan `keywords` ke tabel `clusters`.
2. Karena `pln_analysis` membaca hasil clustering dari CSV yang dibuat di Colab, KarirLens memindahkan prosesnya ke CLI agar dapat dijalankan ulang terhadap Supabase.
3. Untuk statistik gaji, hitung median/P25/P75 di Python (`numpy.percentile`), lalu kirim ke template; Chart.js hanya merender, tidak menghitung.
4. Pakai pola `state.charts` + `destroyChart()` dari Pertemuan 8 agar grafik dapat diperbarui tanpa akumulasi canvas.

**Yang tidak diambil**

- Analisis sentimen, regresi, dan prediksi (`tab_sentimen.py`, `tab_regresi.py`). Di luar scope KarirLens (non-tujuan PRD induk).
- Streamlit sebagai kerangka antarmuka. KarirLens memakai Flask + Jinja.
- Visualisasi wordcloud sebagai fitur wajib. Kata kunci per cluster tetap dihitung, tetapi tampilan daring bisa dilewati bila waktu terbatas; Chart.js yang dipakai untuk distribusi.
- Prediksi gaji dan normalisasi kurs. Tetap dipisah per mata uang sesuai R-05-09.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Insight sesuai isi database dan tidak memuat prediksi.
- Hasil clustering tersimpan di `clusters` dan `jobs.cluster_id`.
