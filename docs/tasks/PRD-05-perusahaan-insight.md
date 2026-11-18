# PRD-05 — Perusahaan dan Insight

| Field | Keterangan |
|---|---|
| ID task | PRD-05 |
| Nama task | Perusahaan dan Insight |
| Prioritas | P0 |
| Milestone | M4 Insight (2 hari) |
| Dependensi | PRD-03, PRD-04 |
| Task yang bergantung | PRD-08, PRD-09 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |

---

## 1. Konteks

Setelah katalog publik tersedia, pengguna membutuhkan gambaran pasar kerja: kategori lowongan, skill yang paling dicari, dan kisaran gaji faktual. Task ini menambahkan proses pengelompokan otomatis (TF-IDF, KMeans, PCA), halaman insight dengan grafik, serta halaman perusahaan yang diturunkan dari data lowongan.

Halaman perusahaan dibangun penuh di task ini, termasuk daftar lowongan per perusahaan dan ringkasan skill serta tipe kerja. Data insight yang dihasilkan juga dipakai ulang oleh REST API pada PRD-09.

## 2. Tujuan

1. Mengelompokkan lowongan ke kategori yang dapat dipahami menggunakan TF-IDF, KMeans, dan PCA.
2. Menampilkan jumlah lowongan per kategori dan skill populer.
3. Menampilkan statistik gaji faktual (median, P25-P75, jumlah sampel) dengan aturan minimal lima sampel.
4. Menampilkan grafik distribusi dengan Chart.js.
5. Menyediakan halaman perusahaan dari data lowongan tanpa profil resmi eksternal.
6. Menyediakan hasil clustering yang dapat ditinjau admin (ditampilkan pada PRD-09).
7. Menjaga agar insight tidak menampilkan prediksi atau klaim di luar data.

## 3. Scope

### 3.1 Termasuk

- Pipeline clustering: input judul, deskripsi, dan skill; TF-IDF → PCA → KMeans; penentuan label dan kata kunci per cluster.
- Penyimpanan hasil ke tabel `clusters` dan `jobs.cluster_id`.
- CLI untuk menjalankan clustering ulang.
- Halaman `/insights`: jumlah lowongan per kategori, skill populer, grafik distribusi.
- Statistik gaji: median, P25, P75, jumlah sampel, per kategori, dipisah per mata uang.
- Aturan data terbatas: pesan jelas bila sampel < 5 atau data belum mencukupi.
- Route `/companies/<slug>`: nama perusahaan, jumlah lowongan, lokasi, tipe kerja, skill yang sering muncul, dan daftar lowongan.
- Bagian insight pada halaman perusahaan (skill sering muncul, tipe kerja, distribusi).
- Service layer insight yang dipakai ulang REST API.

### 3.2 Tidak termasuk

- Katalog publik dasar dan detail lowongan (PRD-04).
- Profil resmi perusahaan, logo, rating, jumlah karyawan, atau alamat di luar data lowongan.
- Tinjauan admin atas cluster (UI di PRD-09; task ini hanya menyediakan datanya).
- Rekomendasi berbasis CV (PRD-07).
- Prediksi gaji dalam bentuk apa pun.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-05-01 | Clustering memakai TF-IDF atas `title` + `description` + `skills` dengan preprocessing konsisten (lowercase, stopword Bahasa Indonesia/Inggris ringan). | P0 |
| R-05-02 | Reduksi dimensi memakai PCA sebelum KMeans; jumlah komponen dan `n_clusters` dapat dikonfigurasi. | P0 |
| R-05-03 | Setiap cluster memiliki `label` dan `keywords` yang dapat dibaca manusia. | P0 |
| R-05-04 | Setiap lowongan dapat memiliki satu `cluster_id` utama; hasil disimpan ke `jobs` dan `clusters`. | P0 |
| R-05-05 | Hasil clustering dapat dijalankan ulang (idempoten) melalui CLI dan tidak memblokir halaman web. | P0 |
| R-05-06 | `/insights` menampilkan jumlah lowongan per kategori yang sesuai isi database. | P0 |
| R-05-07 | `/insights` menampilkan skill paling banyak dicari (top N) dengan grafik. | P0 |
| R-05-08 | Statistik gaji hanya memakai lowongan yang mencantumkan gaji dan hanya tampil jika sampel ≥ 5. | P0 |
| R-05-09 | Statistik gaji menampilkan median, P25, P75, dan jumlah sampel, dipisah per mata uang. | P0 |
| R-05-10 | Tidak ada prediksi gaji; hanya statistik faktual dari data. | P0 |
| R-05-11 | Jika data tidak mencukupi, halaman menampilkan pesan data terbatas yang jelas, bukan grafik kosong. | P0 |
| R-05-12 | Halaman perusahaan menampilkan skill yang sering muncul, tipe kerja yang muncul, dan distribusi lowongan per lokasi dari data `jobs`. | P0 |
| R-05-13 | Grafik memakai Chart.js dan tetap terbaca pada layar 360 px. | P0 |
| R-05-14 | Insight dapat dihitung ulang terjadwal (dipanggil dari PRD-10) tanpa mengubah kode web. | P1 |
| R-05-15 | Service insight menyediakan fungsi yang dipakai ulang oleh `/api/insights/*` pada PRD-09. | P0 |
| R-05-16 | `/companies/<slug>` menampilkan nama perusahaan, jumlah lowongan tersedia, lokasi yang muncul, tipe kerja yang muncul, skill yang sering muncul, dan daftar lowongan. | P0 |
| R-05-17 | `/companies/<slug>` tidak menampilkan deskripsi, logo, rating, jumlah karyawan, atau alamat yang tidak berasal dari data lowongan. | P0 |
| R-05-18 | Halaman perusahaan dibuat dari data `jobs`; tidak ada tabel profil perusahaan dan tidak ada pengambilan profil resmi eksternal. | P0 |

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
- [ ] `/insights` menampilkan jumlah lowongan per kategori dan skill populer sesuai database.
- [ ] Statistik gaji tidak muncul jika sampel < 5 dan tidak ada nilai prediksi.
- [ ] Mata uang berbeda tidak dicampur dalam satu statistik.
- [ ] Pesan data terbatas tampil saat data belum mencukupi.
- [ ] Halaman perusahaan menampilkan skill, tipe kerja, dan lokasi dari data lowongan.
- [ ] Grafik Chart.js terbaca pada 360 px.
- [ ] Menjalankan clustering dua kali tidak menggandakan cluster.

## 6. Dependensi

- PRD-03 (data ternormalisasi dan konsisten).
- PRD-04 (kartu lowongan, navigasi, dan service query dasar).
- Pustaka: `scikit-learn`, `pandas`, `numpy`, Chart.js.
- Data lowongan yang cukup untuk clustering dan statistik dasar.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_tfidf_vectorization` | Vektor TF-IDF terbentuk dari input gabungan. |
| `test_clustering_labels_generated` | Setiap cluster memiliki label dan keywords tidak kosong. |
| `test_clustering_idempotent` | Menjalankan ulang tidak menggandakan cluster. |
| `test_single_cluster_per_job` | Lowongan memiliki paling banyak satu `cluster_id`. |
| `test_salary_min_sample_rule` | Statistik tidak muncul saat sampel < 5. |
| `test_salary_currency_separation` | Mata uang tidak dicampur. |
| `test_salary_quartiles` | Median, P25, P75 dihitung benar pada fixture. |
| `test_no_prediction_output` | Tidak ada field prediksi pada hasil. |
| `test_insights_counts_match_db` | Jumlah kategori dan skill sesuai data uji. |
| `test_company_page_from_jobs_only` | Halaman perusahaan hanya menampilkan data turunan `jobs`. |
| `test_company_page_no_external_profile` | Tidak ada deskripsi, logo, rating, atau alamat di luar data lowongan. |
| `test_company_insight_from_jobs` | Bagian insight perusahaan memakai data `jobs`. |

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
