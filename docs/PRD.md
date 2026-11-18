# PRD KarirLens

## Platform Agregasi Lowongan Kerja dengan Kategorisasi Otomatis, Insight Gaji, dan Rekomendasi Berbasis CV

| Field | Keterangan |
|---|---|
| Nama produk | KarirLens |
| Jenis dokumen | Product Requirements Document (PRD) keseluruhan |
| Versi | 1.0 |
| Status | Final untuk scope web |
| Pemilik | Helga Arya Prayoga |
| Mata kuliah | Praktik Aplikasi Web |
| Tanggal | 18 November 2026 |
| Dokumen sumber | [Perencanaan KarirLens](../../24051130022_Helga%20Arya%20Prayoga_Perencanaan%20KarirLens.md) |

---

## 1. Ringkasan Eksekutif

KarirLens adalah aplikasi web yang mengumpulkan lowongan kerja dari Dealls, Kalibrr, dan Remotive, lalu menyajikannya dalam satu antarmuka pencarian. Aplikasi membantu pencari kerja memahami pasar kerja melalui pengelompokan lowongan, insight kategori dan skill, statistik gaji faktual, serta rekomendasi lowongan berdasarkan skill yang sudah dikonfirmasi dari CV.

Pengguna publik dapat mencari dan melihat lowongan tanpa akun. Pengguna terdaftar dapat menyimpan lowongan sebagai bookmark, mengunggah CV untuk mengekstrak skill, mengonfirmasi skill, dan menerima rekomendasi. Admin dapat memantau data lowongan, pengguna, dan proses pembaruan data. Sistem juga menyediakan REST API untuk data lowongan, kategori, statistik gaji, dan rekomendasi.

Dokumen ini menjadi acuan produk dan teknis tingkat tinggi. Rincian pekerjaan akan dipecah menjadi PRD per task yang lebih kecil.

---

## 2. Latar Belakang dan Masalah

Informasi lowongan kerja tersebar di banyak platform. Pencari kerja harus membuka beberapa situs, membandingkan informasi secara manual, dan sering kesulitan melihat gambaran umum tentang:

- kategori pekerjaan yang tersedia,
- skill yang paling banyak dicari,
- kisaran gaji yang realistis,
- lowongan yang relevan dengan skill yang dimiliki,
- dan sumber asli lowongan.

KarirLens menyatukan informasi tersebut dalam satu aplikasi. Data diambil secara otomatis, dibersihkan, digabungkan, dikelompokkan, dan disajikan dalam halaman publik serta fitur personal.

---

## 3. Tujuan Produk

1. Menyatukan lowongan dari tiga sumber ke dalam satu database.
2. Mempermudah pencarian dan penyaringan lowongan.
3. Membantu pengguna memahami kategori, skill, dan kisaran gaji faktual.
4. Menyediakan rekomendasi lowongan berdasarkan kategori, skill lowongan, dan skill CV yang dikonfirmasi.
5. Menyediakan asisten AI yang menjawab berdasarkan data lowongan yang tersedia.
6. Menyediakan panel admin untuk memantau dan mengelola data.
7. Menyediakan REST API untuk konsumsi data lowongan dan insight.
8. Menjalankan pembaruan data secara terjadwal.

## 4. Non-Tujuan

Fitur berikut tidak termasuk dalam scope web final:

- Tracker lamaran dan status lamaran pengguna.
- Prediksi gaji.
- Analisis sentimen atau ulasan perusahaan.
- Ulasan perusahaan dari pengguna.
- Scraping profil resmi perusahaan dari LinkedIn, Glassdoor, atau situs perusahaan.
- Pendaftaran lamaran otomatis ke situs sumber.
- Penyimpanan file atau teks CV.
- Pembayaran atau langganan.

---

## 5. Target Pengguna

| Persona | Kebutuhan Utama | Akses |
|---|---|---|
| Pencari kerja publik | Mencari, memfilter, dan membaca detail lowongan tanpa hambatan. | Tanpa akun |
| Pencari kerja terdaftar | Menyimpan lowongan, mengunggah CV, mengonfirmasi skill, dan menerima rekomendasi. | Akun pengguna |
| Admin | Memantau data lowongan, pengguna, pengelompokan, dan proses pembaruan. | Akun admin |
| Pengembang atau konsumen data | Mengambil data lowongan, kategori, statistik gaji, dan rekomendasi melalui API. | REST API |

---

## 6. Ruang Lingkup dan Prioritas

Prioritas menggunakan dua tingkat:

- **P0**: wajib untuk rilis akademik dan harus selesai sebelum fitur P1.
- **P1**: penting, dikerjakan setelah alur utama P0 stabil. Tetap termasuk dalam target akhir.

| ID | Fitur | Prioritas | Hasil yang Diharapkan |
|---|---|---|---|
| F-01 | Agregasi lowongan dari Dealls, Kalibrr, dan Remotive | P0 | Data dari tiga sumber tersedia di database. |
| F-02 | Pembersihan dan penggabungan data | P0 | Format data seragam dan duplikat terkendali. |
| F-03 | Pembaruan data terjadwal | P0 | Data diperbarui otomatis melalui GitHub Actions. |
| F-04 | Pencarian lowongan | P0 | Pengguna dapat mencari berdasarkan posisi, perusahaan, atau skill. |
| F-05 | Filter lowongan | P0 | Pengguna dapat memfilter kota, tipe kerja, dan sumber. |
| F-06 | Detail lowongan | P0 | Informasi lengkap dan tautan sumber asli tersedia. |
| F-07 | Halaman perusahaan | P0 | Ringkasan perusahaan dihitung dari data lowongan. |
| F-08 | Pengelompokan otomatis lowongan | P0 | Lowongan terbagi ke kategori yang dapat dipahami. |
| F-09 | Insight kategori dan skill | P0 | Jumlah lowongan per kategori dan skill populer tersedia. |
| F-10 | Rekomendasi lowongan | P0 | Rekomendasi memakai kategori, skill lowongan, dan skill CV. |
| F-11 | Statistik gaji faktual | P0 | Median, P25-P75, dan jumlah sampel tampil jika data cukup. |
| F-12 | Akun pengguna | P0 | Registrasi, login, dan logout berjalan aman. |
| F-13 | Simpan lowongan | P0 | Pengguna dapat menyimpan dan menghapus bookmark lowongan. |
| F-14 | Upload CV dan ekstraksi skill | P0 | Skill diekstrak, dikonfirmasi pengguna, dan CV tidak disimpan. |
| F-15 | Asisten AI | P1 | Pengguna dapat bertanya berdasarkan data lowongan. |
| F-16 | Panel admin | P0 | Admin dapat memantau data, pengguna, dan proses pembaruan. |
| F-17 | REST API | P0 | Data lowongan, kategori, gaji, dan rekomendasi dapat diakses. |

---

## 7. User Journey

### 7.1 Pengunjung publik

1. Membuka beranda.
2. Mencari lowongan atau memilih kategori.
3. Memfilter berdasarkan kota, tipe kerja, atau sumber.
4. Membuka detail lowongan.
5. Membuka halaman perusahaan atau tautan sumber asli.
6. Melihat insight kategori, skill, dan gaji.

### 7.2 Pengguna terdaftar

1. Registrasi atau login.
2. Mencari lowongan.
3. Menyimpan lowongan sebagai bookmark.
4. Mengunggah CV.
5. Meninjau dan mengonfirmasi skill hasil ekstraksi.
6. Melihat rekomendasi lowongan.
7. Menggunakan asisten AI jika diperlukan.
8. Mengelola lowongan tersimpan dan skill profil.

### 7.3 Admin

1. Login ke panel admin.
2. Melihat ringkasan jumlah lowongan, pengguna, dan hasil pembaruan.
3. Meninjau lowongan yang tidak valid.
4. Meninjau daftar pengguna.
5. Memantau riwayat pembaruan data dan error.
6. Meninjau hasil pengelompokan.

### 7.4 Sistem

1. Mengambil data dari tiga sumber.
2. Menormalisasi dan membersihkan data.
3. Menghapus atau menggabungkan duplikat.
4. Menyimpan data ke Supabase.
5. Memperbarui pengelompokan dan statistik.
6. Mencatat hasil pembaruan ke riwayat proses.

---

## 8. Kebutuhan Fungsional

### FR-01 Agregasi Lowongan

- Sistem mengambil lowongan dari Dealls, Kalibrr, dan Remotive.
- Setiap sumber memiliki adapter terpisah.
- Sistem menghormati robots.txt, batas laju, dan user agent yang jelas.
- Setiap pengambilan data dicatat dalam riwayat proses.
- Kegagalan satu sumber tidak menghentikan sumber lain.

**Kriteria penerimaan:** minimal satu proses pengambilan data per sumber berhasil menghasilkan data lowongan yang valid dan tercatat.

### FR-02 Pembersihan dan Penggabungan Data

- Judul, perusahaan, lokasi, tipe kerja, deskripsi, skill, dan gaji dinormalisasi.
- Lowongan dengan tautan sumber yang sama tidak disimpan ganda.
- Lowongan yang sama dari sumber berbeda digabungkan atau ditandai sebagai duplikat.
- Tautan sumber asli tetap disimpan.
- Data yang tidak lengkap tetap dapat disimpan dengan nilai kosong yang jelas.

**Kriteria penerimaan:** tidak ada duplikat berdasarkan `source_url` atau `dedup_hash`, dan data yang tampil memiliki format yang konsisten.

### FR-03 Pembaruan Data Terjadwal

- Pembaruan data dijalankan melalui GitHub Actions.
- Jadwal minimal satu kali per hari.
- Hasil proses dicatat: waktu mulai, waktu selesai, status, jumlah ditemukan, jumlah disimpan, jumlah diperbarui, dan error.
- Proses harus idempoten agar pengambilan ulang tidak membuat duplikat.

**Kriteria penerimaan:** workflow berjalan sesuai jadwal dan riwayat proses dapat dilihat admin.

### FR-04 Pencarian dan Filter

- Pencarian berdasarkan kata kunci posisi, perusahaan, atau skill.
- Filter berdasarkan kota, tipe kerja, dan sumber.
- Hasil dapat diurutkan berdasarkan tanggal atau relevansi.
- Hasil menggunakan pagination.
- Kondisi kosong menampilkan pesan yang jelas.

**Kriteria penerimaan:** kombinasi pencarian dan filter mengembalikan hasil yang sesuai tanpa error.

### FR-05 Detail Lowongan

- Menampilkan judul, perusahaan, lokasi, tipe kerja, deskripsi, skill, gaji jika tersedia, dan sumber.
- Menyediakan tautan ke lowongan asli.
- Menampilkan lowongan serupa.
- Menampilkan atribusi sumber, termasuk Remotive, dan tautan asli.

**Kriteria penerimaan:** setiap lowongan yang tampil memiliki tautan sumber asli yang valid.

### FR-06 Halaman Perusahaan

- Halaman perusahaan dibuat dari data lowongan yang tersimpan.
- Menampilkan nama perusahaan, jumlah lowongan yang tersedia, lokasi, tipe kerja, skill yang sering muncul, dan daftar lowongan.
- Tidak mengambil profil resmi perusahaan dari situs eksternal.
- Tidak menampilkan deskripsi, logo, rating, jumlah karyawan, atau alamat yang tidak tersedia di sumber lowongan.

**Kriteria penerimaan:** halaman perusahaan hanya menampilkan informasi yang dapat diturunkan dari data lowongan.

### FR-07 Pengelompokan Otomatis Lowongan

- Sistem menggunakan TF-IDF, KMeans, dan PCA.
- Input pengelompokan: judul, deskripsi, dan skill.
- Setiap cluster memiliki label dan kata kunci.
- Hasil cluster dapat ditinjau admin.
- Lowongan dapat memiliki satu cluster utama.

**Kriteria penerimaan:** proses pengelompokan menghasilkan cluster yang dapat ditampilkan dan ditinjau.

### FR-08 Insight Kategori dan Skill

- Menampilkan jumlah lowongan per kategori.
- Menampilkan skill yang paling banyak dicari.
- Menampilkan grafik distribusi.
- Menampilkan pesan data terbatas jika jumlah data belum mencukupi.

**Kriteria penerimaan:** halaman insight menampilkan data yang sesuai dengan isi database.

### FR-09 Statistik Gaji Faktual

- Menampilkan median, rentang P25-P75, dan jumlah sampel.
- Hanya memakai lowongan yang mencantumkan gaji.
- Hanya menampilkan statistik jika jumlah sampel minimal lima.
- Tidak memprediksi gaji.
- Tidak mencampur mata uang yang berbeda dalam satu statistik.

**Kriteria penerimaan:** statistik gaji tidak muncul jika sampel kurang dari lima, dan tidak ada nilai prediksi.

### FR-10 Akun Pengguna

- Registrasi dengan email dan password.
- Login dan logout.
- Password disimpan dalam bentuk hash.
- Validasi input dan pesan error yang jelas.
- Sesi aman dan tidak menyimpan password mentah.

**Kriteria penerimaan:** pengguna dapat registrasi, login, logout, dan mengakses halaman personal.

### FR-11 Simpan Lowongan

- Pengguna dapat menyimpan lowongan.
- Pengguna dapat menghapus lowongan dari daftar tersimpan.
- Satu pengguna tidak dapat menyimpan lowongan yang sama dua kali.
- Daftar tersimpan hanya berisi bookmark.
- Tidak ada status lamaran pada lowongan tersimpan.

**Kriteria penerimaan:** simpan dan hapus bookmark bekerja, dan tidak ada data status lamaran yang diminta atau disimpan.

### FR-12 Upload CV dan Ekstraksi Skill

- Menerima file PDF dan DOCX.
- Mengekstrak teks dan skill secara lokal menggunakan kamus skill.
- AI hanya digunakan sebagai fallback untuk skill yang ambigu.
- Pengguna harus mengonfirmasi skill sebelum dipakai untuk rekomendasi.
- File dan teks CV tidak disimpan setelah proses selesai.
- File sementara dihapus.
- CV tidak ditampilkan di panel admin.

**Kriteria penerimaan:** skill berhasil diekstrak dan dikonfirmasi, sementara file serta teks CV tidak tersimpan.

### FR-13 Rekomendasi Lowongan

- Rekomendasi memakai skill CV yang sudah dikonfirmasi, kategori lowongan, dan skill lowongan.
- Rekomendasi dapat menampilkan alasan singkat, misalnya kecocokan skill.
- Perhitungan rekomendasi tidak memanggil AI untuk setiap permintaan.
- Rekomendasi hanya tersedia untuk pengguna yang sudah login.

**Kriteria penerimaan:** pengguna dengan skill terkonfirmasi menerima rekomendasi yang relevan dan dapat dijelaskan.

### FR-14 Asisten AI

- Menjawab pertanyaan tentang lowongan dan pasar kerja berdasarkan data aplikasi.
- Tidak mengambil data langsung dari internet.
- Tidak mengarang gaji, perusahaan, atau tautan.
- Dapat memakai skill yang sudah dikonfirmasi, tetapi tidak memakai isi CV mentah.
- Menolak atau meminta klarifikasi jika data tidak tersedia.
- Memiliki pembatasan penggunaan untuk mencegah penyalahgunaan.
- Hanya tersedia untuk pengguna yang sudah login.

**Kriteria penerimaan:** jawaban asisten hanya merujuk pada data yang tersedia dan tidak membuat klaim di luar data.

### FR-15 Panel Admin

- Login admin terpisah dari pengguna biasa.
- Ringkasan jumlah lowongan, pengguna, dan proses pembaruan.
- Daftar dan pengelolaan lowongan.
- Daftar pengguna.
- Riwayat pembaruan data dan error.
- Tinjauan hasil cluster.
- Tidak menampilkan file atau teks CV.

**Kriteria penerimaan:** admin dapat memantau data dan melakukan tindakan pengelolaan dasar.

### FR-16 REST API

- Menyediakan data lowongan, detail lowongan, perusahaan, kategori, skill, statistik gaji, dan rekomendasi.
- Mendukung pagination pada endpoint daftar.
- Format error konsisten.
- Endpoint personal memerlukan autentikasi.
- Endpoint publik tidak memerlukan autentikasi.

**Kriteria penerimaan:** endpoint utama mengembalikan JSON yang valid dan dapat digunakan.

---

## 9. Kebutuhan Non-Fungsional

### 9.1 Performa

- Halaman publik target dimuat di bawah 2 detik setelah instance aktif.
- Pencarian target selesai di bawah 1,5 detik untuk sekitar 5.000 lowongan.
- Daftar lowongan wajib menggunakan pagination.
- Proses pengambilan data tidak boleh memblokir halaman web.

### 9.2 Keamanan

- Password menggunakan algoritma hash yang kuat.
- Form POST dilindungi CSRF.
- Cookie sesi menggunakan atribut yang aman.
- Input divalidasi di server.
- Query database menggunakan parameter, bukan string mentah.
- Secret disimpan di environment variable, bukan di repository.
- Endpoint AI dan autentikasi memiliki rate limit.

### 9.3 Privasi

- File dan teks CV tidak disimpan.
- File sementara dihapus setelah ekstraksi.
- Isi CV tidak ditulis ke log.
- Hanya skill yang dikonfirmasi yang disimpan.
- Data pengguna tidak dibagikan ke pihak ketiga selain kebutuhan pemrosesan AI.

### 9.4 Keandalan

- Pengambilan data memiliki retry dan backoff.
- Kegagalan satu sumber tidak menghentikan sumber lain.
- Proses pengambilan data idempoten.
- Error dicatat dan dapat dilihat admin.
- Halaman menampilkan pesan error yang ramah.

### 9.5 Usability dan Aksesibilitas

- Antarmuka menggunakan Bahasa Indonesia.
- Layout responsif mulai dari lebar 360 piksel.
- Form memiliki label dan pesan validasi.
- Navigasi dapat digunakan dengan keyboard.
- Warna dan kontras memenuhi keterbacaan dasar.
- Kondisi kosong dan loading memiliki pesan yang jelas.

### 9.6 Maintainability

- Adapter sumber dipisahkan per sumber.
- Logika normalisasi dan deduplikasi dapat diuji terpisah.
- Konfigurasi menggunakan environment variable.
- Kode utama memiliki pengujian untuk parser, logika, dan endpoint penting.

### 9.7 Observability

- Proses pengambilan data mencatat jumlah data dan error.
- Admin dapat melihat riwayat proses.
- Log aplikasi tidak memuat data sensitif.

---

## 10. Arsitektur dan Teknologi

### 10.1 Gambaran Arsitektur

```text
Dealls / Kalibrr / Remotive
            |
            v
   GitHub Actions scraper
            |
            v
        Supabase
            |
            v
   Flask app di Render  <---->  DeepSeek API
            |
            v
         Browser
```

### 10.2 Komponen Utama

| Komponen | Tanggung Jawab |
|---|---|
| Source adapter | Mengambil data dari setiap sumber. |
| Normalizer | Menyeragamkan format data. |
| Deduplicator | Menghapus atau menggabungkan duplikat. |
| Clustering service | TF-IDF, KMeans, dan PCA. |
| Salary insight service | Menghitung median, P25-P75, dan jumlah sampel. |
| Web app | Halaman publik, autentikasi, fitur personal, dan admin. |
| CV service | Ekstraksi teks dan skill, konfirmasi pengguna. |
| Recommendation service | Menghitung rekomendasi tanpa AI per permintaan. |
| AI service | Menjawab pertanyaan berdasarkan data lowongan. |
| REST API | Menyediakan data untuk konsumen eksternal. |
| Scheduler | Menjalankan pembaruan data melalui GitHub Actions. |

### 10.3 Stack Teknologi

| Kategori | Teknologi |
|---|---|
| Bahasa | Python |
| Backend | Flask |
| Database | Supabase |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Grafik | Chart.js |
| Pengolahan data | pandas, scikit-learn |
| Ekstraksi CV | pypdf, python-docx |
| AI | DeepSeek API |
| Deployment | Render |
| Otomatisasi | GitHub Actions |
| Pengujian | pytest |

---

## 11. Model Data

### 11.1 Entitas

| Entitas | Field Penting | Catatan |
|---|---|---|
| `sources` | `id`, `name`, `base_url`, `last_scraped_at` | Metadata sumber lowongan. |
| `jobs` | `id`, `title`, `company_name`, `company_slug`, `location`, `employment_type`, `description`, `skills`, `salary_min`, `salary_max`, `salary_currency`, `salary_period`, `source_id`, `source_url`, `source_job_id`, `posted_at`, `scraped_at`, `dedup_hash`, `cluster_id` | Data lowongan utama. |
| `scrape_runs` | `id`, `source_id`, `started_at`, `finished_at`, `status`, `jobs_found`, `jobs_inserted`, `jobs_updated`, `error_message` | Riwayat pembaruan data. |
| `users` | `id`, `email`, `password_hash`, `name`, `created_at`, `updated_at` | Akun pengguna. |
| `saved_jobs` | `user_id`, `job_id`, `created_at` | Bookmark; kombinasi unik per pengguna dan lowongan. |
| `user_skills` | `id`, `user_id`, `skill`, `source`, `is_confirmed`, `created_at`, `updated_at` | Skill hasil CV atau input manual. |
| `clusters` | `id`, `label`, `keywords`, `job_count`, `created_at` | Hasil pengelompokan lowongan. |

### 11.2 Aturan Data

- Tidak ada tabel `applications`.
- Tidak ada penyimpanan file atau teks CV.
- Halaman perusahaan tidak memakai tabel profil perusahaan; data diturunkan dari `jobs`.
- Statistik gaji dihitung dari `jobs` dan dapat di-cache jika diperlukan.
- Statistik gaji dipisahkan berdasarkan mata uang.
- Duplikat dicegah menggunakan `source_url` dan `dedup_hash`.

---

## 12. Information Architecture

| Route | Halaman | Akses |
|---|---|---|
| `/` | Beranda | Publik |
| `/jobs` | Daftar dan pencarian lowongan | Publik |
| `/jobs/<id>` | Detail lowongan | Publik |
| `/companies/<slug>` | Halaman perusahaan | Publik |
| `/insights` | Insight kategori, skill, dan gaji | Publik |
| `/auth/register` | Registrasi | Publik |
| `/auth/login` | Login | Publik |
| `/profile` | Profil dan skill terkonfirmasi | Pengguna |
| `/saved` | Lowongan tersimpan | Pengguna |
| `/cv` | Upload CV, konfirmasi skill, rekomendasi | Pengguna |
| `/assistant` | Asisten AI | Pengguna |
| `/admin` | Ringkasan admin | Admin |
| `/admin/jobs` | Pengelolaan lowongan | Admin |
| `/admin/users` | Daftar pengguna | Admin |
| `/admin/runs` | Riwayat pembaruan | Admin |

Tidak ada halaman tracker lamaran atau status lamaran.

---

## 13. Rancangan REST API

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

Format respons daftar menggunakan struktur data dan metadata pagination. Format error harus konsisten dan tidak membocorkan detail internal.

---

## 14. Aturan CV dan AI

### 14.1 CV

- Format yang didukung: PDF dan DOCX.
- Ukuran file maksimum: 5 MB.
- Ekstraksi teks dan skill dilakukan secara lokal terlebih dahulu.
- Kamus skill menjadi sumber utama pencocokan.
- AI hanya menjadi fallback untuk skill yang ambigu.
- Pengguna wajib mengonfirmasi skill sebelum dipakai.
- File dan teks CV tidak disimpan.
- File sementara dihapus setelah diproses.
- Isi CV tidak boleh masuk ke log.
- Panel admin tidak menampilkan CV.

### 14.2 Asisten AI

- Menggunakan DeepSeek API dengan model yang dikonfigurasi melalui environment variable.
- Konteks berasal dari data lowongan, cluster, statistik gaji, dan skill terkonfirmasi pengguna.
- Tidak mengambil data langsung dari internet.
- Tidak memakai isi CV mentah.
- Tidak mengarang gaji, perusahaan, atau tautan.
- Menyertakan tautan lowongan jika relevan.
- Menjawab dalam Bahasa Indonesia.
- Meminta klarifikasi atau menolak jika data tidak cukup.
- Memiliki rate limit per pengguna.
- Tidak dipakai untuk menghitung rekomendasi lowongan.

---

## 15. Panel Admin

Panel admin harus menyediakan:

- Login admin.
- Ringkasan jumlah lowongan, pengguna, dan proses pembaruan.
- Daftar lowongan dengan kemampuan meninjau dan menghapus data yang tidak valid.
- Daftar pengguna.
- Riwayat pembaruan data, termasuk status dan error.
- Tinjauan hasil cluster.
- Tidak ada akses ke file atau teks CV.

---

## 16. Batasan, Asumsi, dan Dependensi

### 16.1 Batasan

- Proyek dikerjakan secara individu.
- Target waktu pengembangan 12-14 hari kerja.
- Data bergantung pada tiga sumber: Dealls, Kalibrr, dan Remotive.
- Aplikasi tidak melakukan scraping profil perusahaan.
- Statistik gaji hanya memakai data yang mencantumkan gaji.
- Statistik gaji minimal lima sampel.
- AI hanya memakai data aplikasi.
- File dan teks CV tidak disimpan.
- Tracker lamaran tidak termasuk.

### 16.2 Asumsi

- Sumber lowongan dapat diakses dengan laju yang wajar.
- Data lowongan mencukupi untuk clustering dan statistik dasar.
- Pengguna bersedia mengonfirmasi skill hasil ekstraksi.
- Render Free dan Supabase Free cukup untuk kebutuhan akademik.

### 16.3 Dependensi

- Koneksi internet untuk pengambilan data dan pemanggilan AI.
- Kredensial Supabase.
- Kredensial DeepSeek.
- Akses GitHub Actions.
- Akun Render.
- Perubahan struktur situs sumber dapat memengaruhi adapter.

---

## 17. Metrik Keberhasilan

- Data dari tiga sumber berhasil diambil, dibersihkan, dan disimpan tanpa duplikat yang mengganggu.
- Pengguna dapat mencari, memfilter, dan membuka detail lowongan.
- Halaman perusahaan menampilkan ringkasan yang hanya berasal dari data lowongan.
- Pengelompokan menghasilkan kategori yang dapat dipahami.
- Statistik gaji hanya tampil saat data mencukupi.
- Pengguna dapat registrasi, login, dan menyimpan lowongan sebagai bookmark.
- Pengguna dapat mengunggah CV, mengonfirmasi skill, dan menerima rekomendasi.
- File dan teks CV tidak tersimpan setelah ekstraksi.
- Asisten AI menjawab berdasarkan data lowongan.
- Admin dapat memantau data dan proses pembaruan.
- REST API mengembalikan data yang valid.
- Aplikasi berhasil di-deploy ke Render.
- Dokumentasi dan petunjuk penggunaan tersedia.
- Tidak ada fitur tracker lamaran atau status lamaran di aplikasi.

---

## 18. Timeline dan Milestone

| Milestone | Cakupan | Perkiraan |
|---|---|---|
| M1 Fondasi | Struktur proyek, database, autentikasi, layout dasar. | 1-2 hari |
| M2 Data pipeline | Tiga adapter, normalisasi, deduplikasi, riwayat proses. | 2-3 hari |
| M3 Katalog publik | Beranda, pencarian, filter, detail, halaman perusahaan. | 2 hari |
| M4 Insight | Clustering, kategori, skill, statistik gaji. | 2 hari |
| M5 Akun dan bookmark | Registrasi, login, profil, simpan lowongan. | 1-2 hari |
| M6 CV dan rekomendasi | Upload, ekstraksi, konfirmasi skill, rekomendasi. | 2 hari |
| M7 AI, admin, API | Asisten AI, panel admin, REST API. | 2 hari |
| M8 Rilis | Pengujian, dokumentasi, deployment, pemeriksaan akhir. | 1-2 hari |

Total perkiraan: **12-14 hari kerja**.

---

## 19. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Struktur situs sumber berubah | Scraper gagal | Adapter terpisah, fixture, pengujian parser, logging error. |
| Anti-bot atau pembatasan sumber | Data tidak lengkap | Hormati robots, batas laju, retry, dan user agent. |
| Duplikat lintas sumber | Data ganda | `dedup_hash`, normalisasi judul dan perusahaan, penggabungan tautan. |
| Data gaji sedikit | Insight tidak muncul | Tampilkan pesan data terbatas dan minimal lima sampel. |
| Ekstraksi CV tidak akurat | Rekomendasi kurang relevan | Kamus skill, AI fallback, konfirmasi pengguna. |
| AI berhalusinasi | Informasi menyesatkan | Batasi konteks, larang klaim di luar data, tampilkan tautan sumber. |
| Render Free lambat atau tidur | Akses awal lambat | Terima cold start, gunakan proses terjadwal di GitHub Actions. |
| Supabase Free pause | Aplikasi tidak dapat diakses | Aktifkan data harian dan backup. |
| Scope creep tracker lamaran | Waktu habis | Tracker tetap di luar scope. |
| Kebocoran data CV | Masalah privasi | Tidak menyimpan file atau teks CV, hapus file sementara. |

---

## 20. Rencana PRD per Task

PRD per task disimpan di `docs/tasks/` dengan pola nama `PRD-XX-nama-task.md`. Setiap PRD task harus memuat konteks, tujuan, scope, requirement, acceptance criteria, dependensi, test plan, dan out of scope.

Daftar lengkap dan urutan pengerjaan tersedia di [docs/tasks/README.md](./tasks/README.md).

Spesifikasi visual — token warna, tipografi, anatomi komponen, dan state wajib — ada di [Design System KarirLens](./design-system.md). PRD menetapkan fitur; design system menetapkan tampilannya.

| ID | Task PRD | Cakupan |
|---|---|---|
| PRD-01 | Fondasi proyek | Struktur Flask, konfigurasi, koneksi Supabase, layout, autentikasi dasar. |
| PRD-02 | Data ingestion | Tiga adapter sumber, pembersihan awal, penyimpanan data mentah. |
| PRD-03 | Normalisasi dan deduplikasi | Normalisasi field, `dedup_hash`, penggabungan duplikat, riwayat proses. |
| PRD-04 | Katalog publik | Beranda, pencarian, filter, detail lowongan, pagination. |
| PRD-05 | Perusahaan dan insight | Halaman perusahaan, clustering, kategori, skill, statistik gaji. |
| PRD-06 | Akun dan bookmark | Registrasi, login, profil, simpan dan hapus lowongan. |
| PRD-07 | CV dan rekomendasi | Upload CV, ekstraksi skill, konfirmasi, rekomendasi. |
| PRD-08 | Asisten AI | Integrasi DeepSeek, konteks data, rate limit, pengujian. |
| PRD-09 | Admin dan API | Panel admin, REST API, pengelolaan data. |
| PRD-10 | Kualitas dan rilis | Pengujian, dokumentasi, GitHub Actions, deployment Render. |

Urutan pengerjaan mengikuti dependensi: fondasi, data pipeline, katalog publik, insight, fitur pengguna, AI, admin/API, lalu rilis.

---

## 21. Pertanyaan Terbuka

1. Berapa target minimum jumlah lowongan unik yang harus tersedia sebelum demo?
2. Berapa batas rate limit akhir untuk asisten AI per pengguna?
3. Apakah registrasi memerlukan verifikasi email atau cukup email dan password?
4. Apakah admin terdiri dari satu akun atau beberapa peran?
5. Apakah data lowongan perlu retensi atau pembersihan berkala?
6. Bagaimana aturan penggabungan nama perusahaan yang berbeda penulisan?
7. Apakah statistik gaji perlu normalisasi kurs untuk mata uang berbeda, atau dipisah per mata uang?

---

## 22. Definisi Selesai

Proyek dinyatakan selesai jika:

- Semua fitur P0 berfungsi.
- Fitur P1 asisten AI berfungsi.
- Tidak ada fitur tracker lamaran atau status lamaran.
- File dan teks CV tidak tersimpan.
- Aplikasi dapat diakses melalui Render.
- Data dapat diperbarui melalui GitHub Actions.
- Pengujian utama lulus.
- Dokumentasi penggunaan tersedia.
- PRD per task dan catatan implementasi tersimpan di repository.

---

## 23. Glosarium

| Istilah | Arti |
|---|---|
| Lowongan | Data pekerjaan dari sumber yang di-scrape. |
| Deduplikasi | Proses menghapus atau menggabungkan data yang sama. |
| Clustering | Pengelompokan lowongan berdasarkan kemiripan teks dan skill. |
| Skill terkonfirmasi | Skill yang sudah disetujui pengguna setelah ekstraksi CV. |
| Simpan lowongan | Bookmark lowongan, bukan pencatatan lamaran. |
| Tracker lamaran | Fitur status lamaran yang tidak termasuk dalam scope. |
| Statistik gaji faktual | Statistik dari lowongan yang mencantumkan gaji, bukan prediksi. |

---

## 24. Referensi

- [Dokumen perencanaan KarirLens](../../24051130022_Helga%20Arya%20Prayoga_Perencanaan%20KarirLens.md)
- Dokumentasi Flask
- Dokumentasi Supabase
- Dokumentasi DeepSeek API
- Dokumentasi scikit-learn
- Dokumentasi Chart.js
- Dokumentasi Bootstrap
- Dokumentasi Render
- Dokumentasi GitHub Actions

---

## 25. Riwayat Dokumen

| Versi | Tanggal | Perubahan |
|---|---|---|
| 1.0 | 18 November 2026 | PRD keseluruhan dibuat berdasarkan scope web final. Tracker lamaran dihapus, simpan lowongan menjadi bookmark, halaman perusahaan memakai data lowongan, dan CV menjadi fitur inti. |
