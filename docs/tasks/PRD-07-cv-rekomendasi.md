# PRD-07 — CV dan Rekomendasi (Backend)

| Field | Keterangan |
|---|---|
| ID task | PRD-07 |
| Nama task | CV dan Rekomendasi (Backend) |
| Track | B — Backend |
| Prioritas | P0 |
| Milestone | M6 CV dan rekomendasi (2 hari) |
| Dependensi | PRD-03, PRD-04, PRD-06, PRD-F04 |
| Task yang bergantung | PRD-09 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Frontend pasangan | [PRD-F04](./PRD-F04-cv-asisten.md) |

---

## 1. Konteks

Alur `/cv` — unggah, pratinjau skill, konfirmasi, rekomendasi — sudah dibangun pada PRD-F04, termasuk drop zone, state empat tahap, dan `MatchBadge` dengan alasan. Task ini mengisi mesin di belakangnya: ekstraksi teks PDF/DOCX, pencocokan kamus skill, AI fallback terbatas, dan skor rekomendasi deterministik.

Batas privasi sudah tertanam di tampilan: halaman menyatakan berkas dan teks CV tidak disimpan. Task ini wajib membuktikannya di sisi server, bukan hanya menjanjikannya di layar.

Keluaran task ini wajib memenuhi **kontrak template PRD-F04 §4.1**, termasuk bentuk respons `POST /api/cv/extract`.

## 2. Tujuan

1. Menerima CV PDF dan DOCX, mengekstrak teks secara lokal, dan mencocokkan skill dengan kamus.
2. Memakai AI hanya sebagai fallback untuk skill ambigu.
3. Meminta pengguna mengonfirmasi skill sebelum dipakai.
4. Tidak menyimpan file atau teks CV setelah ekstraksi selesai.
5. Menghitung rekomendasi tanpa AI per permintaan, dengan alasan singkat.

## 3. Scope

### 3.1 Termasuk

- `app/cv/extractor.py`: ekstraksi teks lokal dan penghapusan berkas sementara.
- `app/cv/recommender.py`: skor deterministik berbobot dari konfigurasi.
- `app/cv/service.py`: validasi tipe/ukuran, urutan kamus → AI fallback, penyusunan alasan.
- `app/cv/repository.py`: pembacaan skill terkonfirmasi dan kandidat lowongan.
- `core/skills.py` dan `core/data/skills.json`: kamus skill dan pencocokan.
- Route `/cv` dan `POST /api/cv/extract` yang mengisi kontrak PRD-F04 §4.1.
- Menonaktifkan route preview untuk `/cv`.

### 3.2 Tidak termasuk

- Markup, CSS, dan JavaScript `/cv` (selesai pada PRD-F04).
- Penyimpanan file CV atau teks CV dalam bentuk apa pun.
- Menampilkan CV di panel admin.
- Asisten AI percakapan (PRD-08).
- Prediksi gaji dan penilaian kualitas CV.

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-07-01 | `/cv` menerima file `application/pdf` dan DOCX. Tipe lain ditolak dengan pesan jelas. | P0 |
| R-07-02 | Ukuran file maksimum 5 MB; file lebih besar ditolak sebelum diproses. | P0 |
| R-07-03 | Ekstraksi teks dilakukan lokal; gagal ekstraksi menghasilkan pesan ramah. | P0 |
| R-07-04 | Skill dicocokkan dengan kamus skill bersama di `core/skills.py` dan `core/data/skills.json` (normalisasi sama seperti PRD-03). | P0 |
| R-07-05 | AI fallback hanya dipanggil untuk skill ambigu dan jumlahnya dibatasi. | P0 |
| R-07-06 | Pengguna meninjau dan mengonfirmasi skill sebelum disimpan. | P0 |
| R-07-07 | Hanya skill terkonfirmasi disimpan ke `user_skills` dengan `source` yang jelas. | P0 |
| R-07-08 | File sementara dihapus setelah proses; file dan teks CV tidak disimpan dan tidak masuk log. | P0 |
| R-07-09 | Rekomendasi memakai skill terkonfirmasi, kategori lowongan, dan skill lowongan. | P0 |
| R-07-10 | Rekomendasi menampilkan alasan singkat, mis. "Cocok pada 3 skill: python, sql, git". | P0 |
| R-07-11 | Rekomendasi tidak memanggil AI per permintaan. | P0 |
| R-07-12 | Rekomendasi hanya tersedia untuk pengguna login dan skill terkonfirmasi. | P0 |
| R-07-13 | Pengguna tanpa skill terkonfirmasi diarahkan untuk mengunggah CV atau menambah skill manual. | P1 |
| R-07-14 | Rekomendasi tidak menampilkan lowongan yang sudah di-bookmark sebagai rekomendasi utama (boleh ditandai). | P1 |
| R-07-15 | Pengguna dapat menghapus skill terkonfirmasi. | P1 |
| R-07-16 | Ekstraksi dan rekomendasi dapat diuji tanpa memanggil AI atau jaringan. | P0 |

### 4.1 Alur CV

```text
upload file
  -> validasi tipe & ukuran
  -> ekstraksi teks lokal
  -> cocokkan kamus skill
  -> AI fallback untuk ambigu (dibatasi)
  -> tampilkan pratinjau skill
  -> pengguna konfirmasi
  -> simpan hanya skill terkonfirmasi ke user_skills
  -> hapus file sementara
```

### 4.2 Aturan Rekomendasi

| Aturan | Nilai |
|---|---|
| Input | Skill terkonfirmasi pengguna, `cluster_id`, dan skill lowongan. |
| Skor | Kemiripan skill + kecocokan kategori; bobot dapat dikonfigurasi. |
| Alasan | Daftar skill yang cocok dan/atau kategori yang cocok. |
| AI | Tidak dipanggil per permintaan. |
| Batas | Top N (mis. 10) dengan pagination bila perlu. |

## 5. Acceptance Criteria

- [ ] Upload PDF dan DOCX berhasil diekstrak.
- [ ] File selain PDF/DOCX dan file > 5 MB ditolak dengan pesan jelas.
- [ ] Skill berhasil diekstrak dan hanya yang dikonfirmasi tersimpan.
- [ ] File dan teks CV tidak tersimpan setelah proses selesai.
- [ ] Isi CV tidak muncul di log dan tidak dapat diakses admin.
- [ ] Rekomendasi relevan dan menyertakan alasan singkat.
- [ ] Rekomendasi tidak memanggil AI per permintaan.
- [ ] Pengguna tanpa skill terkonfirmasi mendapat arahan jelas.
- [ ] Lowongan rekomendasi memiliki tautan sumber asli.

## 6. Dependensi

- PRD-03 (normalisasi skill dan `dedup_hash`).
- PRD-04 (query lowongan dan kartu lowongan).
- PRD-06 (sesi pengguna dan tabel `user_skills`).
- Pustaka: `pypdf`, `python-docx`, kamus skill lokal, DeepSeek API (fallback saja).
- Konfigurasi: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, batas fallback AI.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_reject_unsupported_file_type` | Tipe selain PDF/DOCX ditolak. |
| `test_reject_oversize_file` | File > 5 MB ditolak. |
| `test_extract_pdf_fixture` | Teks dan skill diekstrak dari PDF fixture. |
| `test_extract_docx_fixture` | Teks dan skill diekstrak dari DOCX fixture. |
| `test_dictionary_matching_only` | Skill cocok dengan kamus tanpa AI. |
| `test_ai_fallback_limited` | AI fallback dipanggil hanya untuk ambigu dan dibatasi. |
| `test_temp_file_removed` | Tidak ada file sementara tersisa. |
| `test_only_confirmed_skills_saved` | Skill belum dikonfirmasi tidak tersimpan. |
| `test_no_cv_logging` | Log tidak memuat isi CV. |
| `test_recommendation_reason` | Alasan rekomendasi menyebut skill/kategori yang cocok. |
| `test_recommendation_no_ai_call` | Perhitungan rekomendasi tidak memanggil AI. |
| `test_recommendation_requires_login` | Route rekomendasi menolak pengunjung. |

Pengujian memakai fixture CV sintetis dan tidak memakai CV nyata.

### 7.2 Pengujian Manual

1. Unggah CV PDF dan DOCX, tinjau skill hasil ekstraksi, konfirmasi sebagian.
2. Periksa `user_skills` hanya berisi skill terkonfirmasi.
3. Pastikan folder sementara kosong setelah proses.
4. Buka rekomendasi dan cocokkan alasan dengan skill yang dikonfirmasi.
5. Login sebagai admin dan pastikan CV tidak dapat diakses.
6. Uji penolakan file tipe salah dan file besar.

## 8. Out of Scope

- Penyimpanan dan riwayat CV.
- Menampilkan CV di admin.
- Asisten AI percakapan (PRD-08).
- Rekomendasi berbasis machine learning lanjutan atau embedding.
- Penilaian dan umpan balik CV.

## 9. Catatan Teknis

- Ekstraksi dilakukan di server; file disimpan pada direktori sementara yang dihapus di blok `finally`.
- Kamus skill adalah file data lokal yang dapat diperbarui.
- AI fallback memakai batas jumlah dan dicatat tanpa isi CV.
- Rekomendasi memakai fungsi deterministik yang dapat diuji; simpan bobot di konfigurasi.
- Jangan menulis teks CV ke log atau pesan error.

## 10. Referensi Proyek

**Tidak ada proyek referensi untuk ekstraksi CV.** Tidak satu pun dari `D:\Semester 5\Praktik Aplikasi Web` dan `D:\Semester 5\Praktik Scripting` memakai `pypdf`, `pdfplumber`, atau pembacaan berkas PDF. Sesuai instruksi, bagian upload, validasi tipe/ukuran berkas, ekstraksi teks, penghapusan berkas sementara, dan penyimpanan file tetap dikerjakan tanpa acuan.

Yang **bisa** dirujuk hanya pola pencocokan berbasis kamus dan pengukuran akurasinya dari **BengkelBot** (`D:\Semester 5\Praktik Aplikasi Web\Pertemuan 8\bengkelbot`).

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `chatbot/engine.py` — `NORMALISASI` | Kamus normalisasi kata tidak baku/singkatan ke bentuk baku (`"gmn": "bagaimana"`, `"karbu": "karburator"`), dengan nilai `""` berarti kata dibuang. Acuan langsung R-07-04 untuk kamus sinonim skill (mis. `js` → `javascript`, `py` → `python`, `postgres` → `postgresql`). |
| `chatbot/engine.py` — `preprocess()` | Urutan penyeragaman: lowercase → buang tanda baca lewat regex → normalisasi kamus → pecah token → buang stopword. Acuan agar skill hasil ekstraksi CV dinormalisasi dengan aturan yang **sama** seperti skill lowongan (R-07-04 menyebut normalisasi sama seperti PRD-03). |
| `chatbot/engine.py` — `load_theme()`, `validate_theme()` | Validasi struktur kamus di awal dengan pesan galat yang jelas (`ValueError`), bukan gagal saat dipakai. Acuan agar kamus skill divalidasi saat aplikasi start. |
| `evaluate.py` — `baca_data()`, `evaluasi()`, `main()` | Pengukuran akurasi memakai data uji berlabel di CSV, menghitung `(len(data) - len(salah)) / len(data)`, dan mencetak baris yang salah beserta tebakan terdekat. Acuan untuk mengukur akurasi pencocokan kamus skill sebelum bergantung pada AI fallback. |
| `chatbot/engine.py` — `explain(pesan, n=3)` | Mengembalikan kandidat teratas beserta skor, dipakai saat ambigu. Padanan untuk menentukan kapan sebuah skill dianggap ambigu dan layak dikirim ke AI fallback (R-07-05). |
| `tests/test_engine.py` | Fixture `scope="module"` yang memuat kamus sekali, lalu menguji praproses dengan kasus konkret. Acuan test plan §7.1. |

**Cara mengadaptasi ke KarirLens**

1. Buat `core/skills.py` dan `core/data/skills.json` berisi kamus sinonim skill dengan struktur seperti `NORMALISASI`, ditambah `preprocess()` yang dipakai bersama oleh ekstraksi CV dan normalisasi skill lowongan (PRD-03). Kamus diletakkan di `core/` karena R-07-04 menuntut normalisasi yang **sama** dengan PRD-03; satu implementasi bersama menjamin kesamaan itu, sementara salinan di `app/cv/` akan menyimpang seiring waktu. Lihat [Arsitektur Kode §12](../ARCHITECTURE.md).
2. Pakai pola `validate_theme()` untuk memvalidasi kamus skill saat aplikasi start.
3. Pakai pola `evaluate.py` untuk mengukur akurasi pencocokan kamus terhadap CV sintetis berlabel, sehingga AI fallback hanya dipakai untuk kasus yang benar-benar tidak tertangani kamus.
4. Pakai `explain()` sebagai acuan cara menandai skill ambigu beserta skornya.

**Yang tidak diambil**

- Mesin chatbot berbasis aturan dan file tema JSON. KarirLens memakai DeepSeek API di PRD-08; di PRD-07 kamus skill adalah sumber utama, bukan pengganti AI percakapan.
- `difflib.SequenceMatcher` untuk kemiripan kalimat. Tidak dipakai; pencocokan skill cukup berbasis token dan kamus.
- Tidak ada acuan untuk parsing PDF/DOCX, penghapusan berkas sementara, dan alur konfirmasi skill. Bagian itu tetap mengikuti PRD induk.

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- Terbukti tidak ada file atau teks CV tersimpan.
- Rekomendasi berjalan tanpa AI per permintaan.
