# Catatan Implementasi KarirLens

Dokumen ini mencatat **keputusan yang diambil beserta alasannya**, batasan yang
diterima, dan pertanyaan terbuka yang sudah diselesaikan. Bukan panduan
penggunaan (itu di [README](../README.md)) dan bukan kontrak API (itu di
[API.md](API.md)).

---

## 1. Arsitektur

### Modular monolith, tiga lapisan per modul

```
routes.py  ->  service.py  ->  repository.py  ->  core/db.py  ->  Supabase
   HTTP        aturan bisnis      query
```

Aturan yang dijaga otomatis oleh `tests/unit/test_architecture.py`:

1. `service.py` **tidak** boleh mengimpor Flask.
2. `service.py` **tidak** boleh menyentuh Supabase langsung.
3. Sebuah service hanya boleh memakai repository **modulnya sendiri**.

**Aturan 3 dilanggar tiga kali** selama pengerjaan (`insights`, `profile`,
`jobs` mengambil query yang bukan miliknya). Setiap pelanggaran diperbaiki
dengan menambahkan query ke repository modul yang bersangkutan, bukan dengan
melonggarkan aturannya. Alasannya: tanpa aturan ini, satu perubahan skema
menuntut penyuntingan di tempat yang tidak terduga.

### Dua track (frontend lebih dulu)

Track A mengisi template dari fixture (`tests/fixtures/ui/*.json`) lewat
blueprint `preview`; Track B mengisi backend sungguhan. Keduanya merender
**template yang sama**.

Akibat yang tidak terhindarkan: template memanggil `url_for('preview.jobs')`,
sementara di produksi endpoint itu tidak terdaftar. Solusinya
`app/templating.py` — penerjemah nama endpoint di lapisan Jinja, bukan
menyunting 8 baris template atau menambah percabangan flag. Dengan begitu
R-04-11 ("template katalog tidak boleh berubah") tetap dipenuhi.

---

## 2. Pipeline data

### Tiga sumber, tiga cara berbeda

| Sumber | Mekanisme | Jumlah IT |
|---|---|---|
| Dealls | HTML daftar + `__NEXT_DATA__` di halaman detail | 40 dari 900 |
| Kalibrr | API `kjs/job_board/search` di balik tombol "Load more" | 253 dari 2290 |
| Remotive | Halaman kategori (bukan paginasi) | 65 dari 171 |

**Produk dipersempit ke lowongan IT saja** sejak PRD-04. Bukan preferensi: 96%
hasil Dealls non-IT (860 dari 900), sehingga katalog tanpa filter bukan katalog
karir teknologi.

**Saringan IT berjalan sebelum halaman detail diambil**, memakai bukti
berurutan: kategori sumber → judul → skill. Non-IT tidak memakan satu pun
permintaan HTTP.

### Kesalahan yang hanya terlihat dari data sungguhan

| Gejala | Penyebab sebenarnya |
|---|---|
| "Kalibrr dibatasi 26 lowongan" | Salah membaca parameter URL. Mekanisme sebenarnya adalah tombol "Load more" → 253 lowongan dalam 7 detik, bukan 26 dalam 410 detik |
| Paging Kalibrr mengembalikan non-IT | Server **membuang filter `function`** setelah offset ~254. Paging kini berhenti sendiri saat itu terjadi |
| 19 dari 35 kartu Remotive hilang | Parser bergantung pada `span.remotive-bold`; 13 kartu tidak punya kelas itu. Kini dibaca dari struktur `li[data-joburl]` |
| Median gaji USD 141 | Gaji di kartu **dipotong server pada 95 karakter**, sehingga `/year` vs `/hour` hilang dan keduanya tercampur. Diambil dari JSON-LD halaman detail; hasilnya USD/tahun, n=28, median 125.000 |
| Clustering mati saat data sedikit | `min_df=2` ditolak scikit-learn untuk dataset kecil. Kini diskalakan terhadap jumlah dokumen |

Empat dari lima bug di atas **lolos semua test** dan hanya ketahuan karena
membandingkan hasil dengan situs aslinya. Ini alasan jumlah test bukan ukuran
kualitas tunggal.

### Deduplikasi

SHA-256 dari `title|company_name|location` yang digabung dengan `\x1f`.
Pemisah itu penting: tanpa itu `"AB"+"C"` dan `"A"+"BC"` menghasilkan hash sama.

**Bukan `hash()` bawaan Python**: nilainya diacak per proses (PYTHONHASHSEED),
sehingga seluruh database akan terlihat baru setiap kali scraper dijalankan.

### `--replace` dan ambang pengaman

Operasi destruktif berjalan **terakhir dan hanya setelah pengambilan berhasil**:

- Sumber yang gagal **tidak** dihapus.
- Bila hasil hari ini < 60% isi database, penghapusan **dibatalkan**
  (`MIN_REPLACE_RATIO = 0.6`).

Tanpa ambang itu, satu kegagalan jaringan akan mengosongkan katalog.

---

## 3. Kecerdasan buatan: satu fitur, bukan tujuh

| Fitur | LLM? | Metode |
|---|---|---|
| Scraping, normalisasi, saringan IT | Tidak | HTTP + regex |
| Clustering | Tidak | TF-IDF + PCA + KMeans |
| Baca skill dari CV | Tidak | Ekstraksi teks + kamus + regex |
| Rekomendasi | Tidak | Rumus bobot |
| Statistik gaji | Tidak | Persentil |
| **Asisten** | **Ya** | DeepSeek `deepseek-flash` |

Ini disengaja: PRD melarang AI di normalisasi (R-03-14) dan rekomendasi
(R-07-11), karena hasilnya harus deterministik dan dapat diperiksa. "Pakai AI"
bukan tujuan; jawaban benar yang dapat dipertanggungjawabkan adalah tujuannya.

### Clustering

`TF-IDF → PCA(2) → KMeans(6)`, `random_state=42` agar hasilnya dapat diulang.

Skill diulang **dua kali** dalam vektor: deskripsi lowongan banyak berisi prosa
pemasaran, sedangkan daftar skill langsung menyebut teknologinya.

Kata kunci cluster = **selisih rata-rata vektor cluster terhadap cluster lain**,
bukan kata tersering. Tanpa pengurangan itu, seluruh cluster menampilkan kata
yang sama ("developer" ada di mana-mana).

### CV: kamus, bukan AI

`core/data/skills.json` berisi 105 skill dan 80 alias. Pencocokan memakai regex
dengan **batas kata** `(?<![\w+#.])python(?![\w+#])` — tanpa itu `go` cocok di
dalam "Django" dan `c` di dalam "React".

Dua penyaring ditambahkan setelah melihat keluaran nyata:
- `_NOT_SKILL` untuk kata fungsi.
- **Baris pertama CV dilewati** — di situ nama orang; "budi" sempat muncul
  sebagai kandidat skill.

### Asisten: grounding, bukan model bebas

Konteks disusun dari database (8 lowongan relevan, kategori, statistik gaji,
skill terkonfirmasi) — sekitar 2.562 karakter. Tautan **selalu** dari baris
database, tidak pernah dari teks model: URL karangan lebih berbahaya daripada
tidak ada URL.

Tiga kegagalan nyata yang diperbaiki setelah diuji:

1. **Klarifikasi tidak pernah menyala.** Syaratnya "kategori kosong", padahal
   kategori selalu ada setelah clustering — jadi pertanyaan apa pun lolos dan
   "apa itu quantum computing" dijawab "Ada lowongan Data Analyst".
2. **Pertanyaan wajar ikut tertolak.** "backend engineer" ditolak karena
   judulnya "Software Engineer, Backend". Kini niat mencari kerja (skill di
   kamus, kata seputar lowongan, label kategori) membuka gerbangnya, dan
   lowongan terbaru dipakai dengan label "tidak ada yang persis cocok".
3. **Kuota dipotong untuk klarifikasi.** Pengguna tidak menerima jawaban,
   jadi pertanyaannya tidak boleh menghabiskan jatah.

### Model DeepSeek: dua kesalahan konfigurasi

`deepseek-chat` **dihentikan 24 Juli 2026**. Setiap panggilan dibalas 400, dan
karena kode memperlakukan 4xx sebagai kegagalan permanen, pengguna melihat
"asisten sedang sibuk" — pesan yang membuatnya menunggu tanpa akhir.

Diperbaiki: model `deepseek-flash`, dan 401/403 kini berbunyi "kunci API
ditolak, hubungi pengelola" alasan sebenarnya dicatat ke log.

**Thinking mode menyala secara bawaan** pada `deepseek-flash`. Bila dibiarkan,
rantai penalaran memakan `max_tokens=512` sehingga `content` dapat kosong, dan
`temperature=0.2` — yang justru menahan model dari mengarang — **diabaikan
sepenuhnya**. Kini dikirim `{"thinking": {"type": "disabled"}}`.

---

## 4. Keputusan UI yang menyimpang dari dugaan

| Keputusan | Alasan |
|---|---|
| `minmax(0, 1fr)` bukan `1fr` | `1fr` membuat katalog meluber ke 589px pada viewport 360px |
| Skor rekomendasi dikalikan `min(1, n/4)` | Lowongan yang hanya menyebut `aws` mendapat skor 100% dan mengalahkan lowongan yang cocok pada empat skill |
| Statistik gaji dari titik tengah rentang | Memakai `salary_min` saja menurunkan median secara sistematis |
| Periode tidak diketahui **tidak** dilabeli "bulanan" | Itu klaim yang tidak dimiliki data |
| `/healthz` tidak menyentuh database | Health check yang menyentuh DB mengubah gangguan Supabase sesaat menjadi restart loop Render |

---

## 5. Batasan yang diterima

- **Cakupan skill 192 dari 363 lowongan.** Kalibrr dan Remotive tidak punya
  field skill, jadi harus disimpulkan — dan penyimpulan sengaja konservatif.
  8 dari 32 benar lebih baik daripada 13 dari 32 dengan skill palsu.
- **Label cluster kaku** ("Teknik & Informasi & Bisnis"). PRD menyarankan label
  manual; label otomatis dipilih agar selalu terisi setiap clustering dijalankan.
- **Render Free tidur setelah 15 menit** tanpa trafik, cold start ±60 detik.
  Karena itu proses terjadwal berada di GitHub Actions, bukan di container.
- **GitHub Actions `schedule` terlambat 7–9 jam** pada repo bertrafik rendah.
  Terukur pada empat run berturut-turut. Ini tidak merusak scraping (data
  lowongan tidak terikat jam), tetapi **tidak layak untuk notifikasi terjadwal**
  — perlu pemicu eksternal bila fitur itu dikerjakan.
- **PDF hasil pindai tidak dapat dibaca**; tidak ada OCR.

---

## 6. Pertanyaan terbuka yang sudah diselesaikan

| Pertanyaan | Keputusan |
|---|---|
| Apakah semua jenis lowongan atau hanya IT? | Hanya IT, karena 96% data Dealls non-IT |
| Filter tunggal atau banyak nilai? | Banyak nilai (OR dalam dimensi, AND antar dimensi) |
| Data lama dihapus atau ditambahkan? | Diganti (`--replace`), dengan ambang 60% |
| Simpan teks CV untuk analisis lanjutan? | Tidak. Hanya nama skill yang dikonfirmasi |
| Prediksi gaji? | Tidak. Hanya statistik faktual |
| Scheduler di dalam aplikasi? | Tidak. GitHub Actions |
| AI untuk normalisasi/rekomendasi? | Tidak. Harus deterministik |

Dua hal yang **tidak** disetujui dan sengaja tidak dikerjakan: retensi data
berkala, dan pembersihan otomatis. PRD induk menyebutnya sebagai pertanyaan
terbuka; menambahkannya tanpa persetujuan berarti menghapus data pengguna
atas dasar tebakan.

---

## 7. Hasil uji akhir

```
python -m pytest -q
```

| Kelompok | Cakupan |
|---|---|
| Parser & normalisasi | Fixture HTML asli, tanpa jaringan |
| Deduplikasi & `--replace` | Termasuk batas 59% vs 61% |
| Statistik gaji | Ambang 5 sampel, pemisahan mata uang |
| Clustering | Termasuk dataset kecil |
| Auth, bookmark, CV, asisten, admin, API | Test client, klien tiruan |
| Arsitektur | Arah dependensi antar lapisan |
| Rilis (PRD-10) | Tracker lamaran, privasi CV, ambang gaji, cookie, secret |

Seluruh test berjalan **tanpa Supabase dan tanpa jaringan**: `tests/conftest.py`
mengganti client database, dan setiap modul yang memanggil layanan luar
menerima klien tiruan lewat injeksi.

### Yang belum diverifikasi dengan layanan sungguhan

Jujur, bukan daftar kosong:

- **Jawaban DeepSeek.** Semua test memakai klien tiruan. Kunci di `.env`
  terakhir dibalas `401 Authentication Fails`, jadi belum ada satu pun jawaban
  nyata yang pernah terlihat.
- **Tombol hapus admin di browser.** Diuji lewat test client; belum diklik
  pada peramban sungguhan.
- **Jadwal harian GitHub Actions sebagai mekanisme tepat waktu.** Terbukti
  berjalan, terbukti terlambat 7–9 jam.
