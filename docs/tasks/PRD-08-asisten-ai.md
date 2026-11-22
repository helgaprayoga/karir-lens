# PRD-08 — Asisten AI (Backend)

| Field | Keterangan |
|---|---|
| ID task | PRD-08 |
| Nama task | Asisten AI (Backend) |
| Track | B — Backend |
| Prioritas | P1 |
| Milestone | M7 AI, admin, API (2 hari) |
| Dependensi | PRD-03, PRD-05, PRD-06, PRD-F04 |
| Task yang bergantung | PRD-09, PRD-10 |
| Status | Selesai (terbukti di Supabase, AI menunggu API key) |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F04](./PRD-F04-cv-asisten.md) |

---

## 1. Konteks

Antarmuka `/assistant` sudah dibangun pada PRD-F04: area pesan dengan `aria-live`, indikator memproses, dan `AlertBanner` untuk galat. Task ini mengisi mesinnya: penyusunan konteks dari data aplikasi, pemanggilan DeepSeek, larangan klaim di luar konteks, dan rate limit per pengguna.

Template sudah mengasumsikan bentuk respons `{"data": {"reply": ..., "sources": [...]}}`. Task ini wajib memenuhinya, termasuk memastikan tautan yang muncul benar-benar berasal dari `jobs`.

Keluaran task ini wajib memenuhi **kontrak PRD-F04 §4.1**.

## 2. Tujuan

1. Menyusun konteks dari lowongan, cluster, statistik gaji, dan skill terkonfirmasi.
2. Menjawab dalam Bahasa Indonesia dengan tautan lowongan bila relevan.
3. Menolak atau meminta klarifikasi jika data tidak cukup.
4. Membatasi penggunaan per pengguna untuk mencegah penyalahgunaan.
5. Tidak memakai isi CV mentah dan tidak mengambil data dari internet.

## 3. Scope

### 3.1 Termasuk

- `app/assistant/service.py`: penyusunan konteks dan rate limit.
- `core/external/deepseek.py`: implementasi klien HTTP dengan timeout eksplisit.
- `POST /api/assistant` dengan bentuk respons kontrak PRD-F04 §4.1.
- System prompt yang melarang klaim di luar konteks.
- Penanganan error dan timeout API yang ramah.
- Pengujian dengan klien tiruan tanpa jaringan.
- Menonaktifkan route preview untuk `/assistant`.

### 3.2 Tidak termasuk

- Markup, CSS, dan JavaScript `/assistant` (selesai pada PRD-F04).
- Pencarian internet atau akses sumber eksternal.
- Memakai isi CV mentah.
- Menghitung rekomendasi lowongan (PRD-07).
- Riwayat percakapan permanen lintas sesi.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-08-01 | `/api/assistant` dan `/assistant` hanya tersedia untuk pengguna login; template `/assistant` sudah ada dari PRD-F04. | P0 |
| R-08-02 | Konteks disusun dari data aplikasi: lowongan relevan, cluster, statistik gaji, dan skill terkonfirmasi milik pengguna. | P0 |
| R-08-03 | Asisten tidak mengambil data langsung dari internet. | P0 |
| R-08-04 | Asisten tidak memakai isi CV mentah; hanya skill terkonfirmasi. | P0 |
| R-08-05 | Jawaban dalam Bahasa Indonesia dan tidak mengarang gaji, perusahaan, atau tautan. | P0 |
| R-08-06 | Tautan lowongan disertakan hanya dari data tersimpan. | P0 |
| R-08-07 | Jika data tidak cukup, asisten meminta klarifikasi atau menolak dengan sopan. | P0 |
| R-08-08 | Model DeepSeek dibaca dari `DEEPSEEK_MODEL`; API key dari `DEEPSEEK_API_KEY`. | P0 |
| R-08-09 | Rate limit per pengguna dan batas harian diterapkan; kelebihan limit menghasilkan pesan jelas. | P0 |
| R-08-10 | Timeout dan error API eksternal ditangani tanpa membocorkan detail internal. | P0 |
| R-08-11 | Pertanyaan dan jawaban tidak disimpan permanen pada task ini; log tidak memuat data sensitif. | P1 |
| R-08-12 | Asisten tidak dipakai untuk menghitung rekomendasi lowongan. | P0 |
| R-08-13 | Pengujian memakai mock respons DeepSeek dan tidak memanggil jaringan. | P0 |

### 4.1 Susunan Konteks

| Sumber | Pemakaian |
|---|---|
| `jobs` | Lowongan relevan dengan pertanyaan (judul, perusahaan, lokasi, gaji bila ada, `source_url`). |
| `clusters` | Label dan kata kunci kategori. |
| `insights` | Statistik gaji faktual bila tersedia dan sampel ≥ 5. |
| `user_skills` | Hanya skill dengan `is_confirmed = true`. |
| CV mentah | Tidak pernah dipakai. |
| Internet | Tidak pernah dipakai. |

### 4.2 Aturan Jawaban

- Jawab hanya dari konteks yang diberikan.
- Jika konteks tidak memuat jawaban, minta klarifikasi atau sampaikan keterbatasan.
- Jangan menyebut angka gaji yang tidak ada di data.
- Jangan menyebut perusahaan atau tautan yang tidak ada di data.
- Cantumkan tautan lowongan relevan bila ada.
- Bahasa Indonesia, ringkas, dan jelas.

## 5. Acceptance Criteria

- [x] Pengguna login dapat mengirim pertanyaan dan menerima jawaban Bahasa Indonesia.
- [x] Jawaban hanya merujuk pada data yang tersedia dan tidak membuat klaim di luar data.
- [x] Asisten meminta klarifikasi atau menolak saat data tidak cukup.
- [x] Tautan lowongan yang disertakan berasal dari data tersimpan.
- [x] Rate limit dan batas harian bekerja dengan pesan jelas.
- [x] Error/timeout DeepSeek ditangani tanpa detail internal.
- [x] Isi CV mentah tidak pernah dipakai atau muncul pada jawaban.
- [x] Pengujian berjalan dengan mock dan tanpa jaringan.

Bukti terukur ada di §12. Catatan jujur: jawaban dari DeepSeek **belum dapat
diuji terhadap API sungguhan** karena `DEEPSEEK_API_KEY` belum diisi di
lingkungan ini. Seluruh alur lain terbukti, dan pemanggilan model diuji dengan
klien tiruan.

## 6. Dependensi

- PRD-06 (autentikasi dan sesi).
- PRD-05 (cluster dan statistik gaji).
- PRD-03 (data lowongan ternormalisasi).
- Kredensial `DEEPSEEK_API_KEY` dan model `DEEPSEEK_MODEL`.
- Pustaka: klien HTTP (`requests`) atau SDK DeepSeek.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_assistant_requires_login` | Pengunjung ditolak. |
| `test_context_uses_confirmed_skills_only` | Konteks tidak memuat CV mentah; skill belum dikonfirmasi diabaikan. |
| `test_answer_grounded_in_context` | Mock respons dibatasi konteks; jawaban tidak memuat data di luar konteks. |
| `test_insufficient_data_asks_clarification` | Konteks kosong memicu klarifikasi/penolakan. |
| `test_links_from_stored_jobs` | Tautan yang muncul berasal dari `jobs`. |
| `test_rate_limit_per_user` | Permintaan melebihi batas ditolak dengan pesan jelas. |
| `test_daily_limit` | Batas harian diterapkan. |
| `test_api_timeout_handled` | Timeout menghasilkan pesan ramah. |
| `test_no_cv_content_in_response` | Jawaban tidak memuat isi CV. |
| `test_recommendation_not_using_assistant` | Rekomendasi tidak memanggil asisten. |

Pengujian memakai stub `DeepSeekClient` dan tidak memanggil jaringan.

### 7.2 Pengujian Manual

1. Login, tanya "skill apa yang paling banyak dicari untuk data analyst?" dan periksa jawaban dengan `/insights`.
2. Tanya tentang gaji dan pastikan tidak ada angka di luar data.
3. Tanya hal di luar data dan pastikan klarifikasi/penolakan.
4. Kirim banyak pertanyaan dan periksa rate limit.
5. Matikan koneksi DeepSeek dan pastikan pesan error ramah.
6. Periksa log tidak memuat pertanyaan sensitif atau isi CV.

## 8. Out of Scope

- Pencarian internet dan pengambilan data langsung dari sumber.
- Memakai isi CV mentah.
- Prediksi gaji.
- Riwayat percakapan lintas sesi dan personalisasi lanjutan.
- Perhitungan rekomendasi lowongan.

## 9. Catatan Teknis

- DeepSeek dipanggil dengan timeout eksplisit dan retry terbatas.
- System prompt harus eksplisit melarang klaim di luar konteks.
- Rate limit disimpan per pengguna (mis. tabel atau cache) dengan batas harian dari `AI_DAILY_LIMIT`.
- Konteks dibatasi ukurannya agar biaya dan latensi terkendali.
- Mock klien DeepSeek untuk pengujian; jangan memanggil API nyata di test.

## 10. Referensi Proyek

**Tidak ada proyek referensi yang memanggil LLM.** BengkelBot sengaja berbasis aturan tanpa LLM, dan tidak ada proyek lain di kedua folder yang memanggil DeepSeek/OpenAI. Bagian prompt, grounding konteks, dan rate limit tetap dikerjakan tanpa acuan.

Yang dirujuk adalah **kerangka antarmuka dan kontraknya** dari **BengkelBot** (`D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot`).

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `app.py` — `api_chat()` | Kontrak `POST /api/chat`: tolak body non-dict (`isinstance(data, dict)`), tolak pesan kosong, batasi `MAKS_KARAKTER`, lalu `bot.reply(pesan)` diikuti penyimpanan. Acuan langsung R-08-01 dan validasi input R-08-07. |
| `app.py` — `galat(pesan, kode)` | Satu helper respons error JSON seragam `{"error": pesan}` untuk seluruh endpoint API. Acuan R-08-10 (format error konsisten tanpa detail internal). |
| `app.py` — `create_app(config=None)` | Konfigurasi `MAX_CONTENT_LENGTH` dan error handler 413/500 yang membedakan `/api/` dari halaman. Acuan penanganan payload terlalu besar dan gagal server. |
| `chatbot/engine.py` — `ChatbotEngine.reply()` | Bentuk hasil `{"reply": teks, "intent": tag, "score": skor}` — satu objek yang membawa jawaban plus metadata keputusan. Acuan struktur respons agar UI bisa menampilkan alasan/tingkat keyakinan. |
| `chatbot/engine.py` — `classify()` + ambang | Menolak menjawab saat skor di bawah ambang, lalu memakai fallback. Padanan langsung R-08-07 (meminta klarifikasi atau menolak bila data tidak cukup): hindari menjawab dengan yakin saat konteks lemah. |
| `chatbot/engine.py` — `_isi_placeholder()` | Pengisian nilai dinamis (`{waktu}`, `{tanggal}`) saat jawaban dibuat, bukan saat tema dimuat. Acuan agar tautan dan angka selalu berasal dari data terkini. |
| `static/js/chat.js`, `templates/chat.html` | Interaksi chat di browser: kirim pesan, tampilkan pasangan pesan, tangani galat jaringan. Acuan R-08-01 untuk UI percakapan. |
| `tests/test_engine.py`, `tests/test_web.py` | Pengujian mesin dan endpoint tanpa jaringan; `app.test_client()` untuk `/api/*`. Acuan R-08-13 (mock respons, tanpa panggilan jaringan). |

**Cara mengadaptasi ke KarirLens**

1. Pakai kontrak `POST /api/chat` dan helper `galat()` sebagai bentuk dasar `/api/assistant`.
2. Ganti `ChatbotEngine.reply()` dengan klien DeepSeek, tetapi **pertahankan bentuk hasil** `{"reply", "intent"/"sumber", "score"}` agar UI dan pengujian tetap sederhana.
3. Terapkan pola ambang: jika konteks yang berhasil dikumpulkan lemah atau kosong, arahkan ke klarifikasi, bukan memaksa jawaban.
4. Pakai pola mock di `tests/test_web.py` untuk memalsukan klien DeepSeek.

**Yang tidak diambil**

- Mesin berbasis aturan, file tema `themes/*.json`, dan `difflib.SequenceMatcher`. KarirLens memakai LLM dengan konteks dari database.
- **Penyimpanan riwayat chat permanen.** BengkelBot menyimpan setiap pesan ke SQLite dan menampilkannya di admin. PRD-08 R-08-11 menyatakan pertanyaan dan jawaban **tidak** disimpan permanen pada task ini; pola penyimpanan itu sengaja tidak diadopsi.
- Dashboard admin pertanyaan tak dikenali. Namun pola statistiknya menjadi acuan PRD-09.
- Tidak ada acuan untuk rate limit per pengguna dan batas harian; bagian itu tetap mengikuti PRD induk.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus tanpa jaringan.
- Jawaban terbukti hanya berbasis data aplikasi.
- Tidak ada pemakaian atau penyimpanan isi CV mentah.

---

## 12. Catatan Implementasi

### 12.1 Berkas

| Berkas | Isi |
|---|---|
| `core/external/deepseek.py` | Klien HTTP dengan timeout, retry terbatas, galat aman |
| `app/assistant/service.py` | Konteks, system prompt, klarifikasi, rate limit |
| `app/assistant/repository.py` | Query lowongan/kategori/gaji/skill dan pencatatan pemakaian |
| `app/assistant/routes.py` | `/assistant` dan `/assistant/ask` |
| `app/api/routes.py` | `POST /api/assistant` (kontrak PRD-F04 §4.1) |
| `migrations/005_ai_usage.sql` | Tabel `ai_usage` untuk batas harian |
| `tests/unit/test_assistant.py` | 34 test, semuanya dengan klien tiruan |

### 12.2 Keputusan

**Sumber tautan diambil dari konteks, bukan dari jawaban model.** Model dapat
mengarang URL, dan tautan karangan lebih berbahaya daripada tidak ada tautan.
`sources` dibangun dari baris `jobs` yang benar-benar dikirim ke prompt
(R-08-06).

**Klarifikasi diputuskan sebelum memanggil model.** Bila konteks tidak memuat
jawaban, model hanya akan mengarang dari pengetahuan umumnya. Berhenti lebih
awal lebih jujur dan lebih murah.

**Kuota tidak dipotong saat klarifikasi atau kegagalan.** Pengguna tidak
menerima jawaban; mengurangi jatahnya akan menghukumnya atas keputusan kita
sendiri.

**Batas harian disimpan di tabel, bukan memori proses.** Beberapa worker atau
restart aplikasi akan menghapus penghitung di memori, dan batasnya menjadi tidak
berarti. Yang disimpan hanya `user_id` dan `tanggal` — bukan pertanyaan maupun
jawaban (R-08-11).

**`AssistantError` turunan `ExternalServiceError`.** Dengan begitu handler
global PRD-01 memetakannya ke 502 dengan bentuk galat yang sama seperti endpoint
lain, tanpa setiap route perlu menangkapnya sendiri.

### 12.3 Bug yang Ditemukan Verifikasi

**Klarifikasi tidak pernah terpicu.** Syaratnya "tidak ada lowongan **dan**
tidak ada kategori", tetapi kategori selalu ada setelah clustering (6 buah).
Akibatnya pertanyaan apa pun lolos ke model. Terukur: "apa itu quantum
computing" dikirim ke model dan dijawab "Ada lowongan Data Analyst" — jawaban
yang tidak menjawab pertanyaannya.

Perbaikannya `_perlu_klarifikasi()`: klarifikasi terjadi bila tidak ada lowongan
cocok **dan** pertanyaan tidak menyentuh kategori mana pun. Pertanyaan meta
("kategori apa saja", "gaji backend") tetap dijawab karena datanya ada.

**Pertanyaan meta kehilangan semua katanya.** Setelah stopword dibuang,
"kategori apa saja yang ada" tidak menyisakan kata apa pun, sehingga dianggap
tidak relevan. Ditambahkan daftar `_META` (`kategori`, `gaji`, `skill`,
`statistik`) yang menandai pertanyaan tentang isi sistem, bukan tentang lowongan
tertentu.

**`CSRFProtect` membaca config saat init.** Mengubah `app.config` sesudah
`create_app` tidak mematikan CSRF; kelas config harus membawa
`WTF_CSRF_ENABLED=False` sejak awal. Ini pelajaran untuk test berikutnya.

**`user_loader` menyentuh Supabase di test.** Tanpa tambalan, sesi dianggap
tidak login karena query gagal, dan setiap request berakhir 302 alih-alih diuji.

### 12.4 Verifikasi Terukur

Terhadap Supabase sungguhan (363 lowongan, 6 kategori):

| Pemeriksaan | Hasil |
|---|---|
| `DEEPSEEK_API_KEY` | **belum diisi** — jawaban memuat pemberitahuan, bukan error |
| Konteks yang dikirim ke model | 2.562 karakter, memuat LOWONGAN RELEVAN, STATISTIK GAJI, KATEGORI |
| Skill terkonfirmasi | tidak ada untuk pengguna uji (benar) |
| Sumber tautan | 3, semuanya `kalibrr.com` dari baris `jobs` |
| Pertanyaan di luar data | dijawab klarifikasi, **model tidak dipanggil** |
| Pemakaian tercatat | 1 baris, hanya `user_id` dan `tanggal` |
| Tamu `POST /api/assistant` | 302 ke login |

Diperiksa di browser: `/assistant` menampilkan 4 saran pertanyaan, form menunjuk
`/api/assistant` produksi, dan pertanyaan suntingan menghasilkan balasan
klarifikasi yang menyebut kategori yang tersedia. Tidak ada luberan pada 360px.

Data uji dihapus setelah verifikasi (1 pengguna, 1 baris pemakaian).

Total test setelah task ini: **597 lulus**.
