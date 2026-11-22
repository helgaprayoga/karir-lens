# Sumber Skill per Sumber Lowongan — Temuan

Diperiksa langsung terhadap HTML asli (fixture dari user + `requests` ke Dealls).
Dokumen ini menjawab: dari mana `skills` diambil untuk masing-masing sumber.

## Ringkasan

| Sumber | Skill terstruktur? | Dari mana | Kualitas |
|---|---|---|---|
| **Dealls** | **Ya** | `__NEXT_DATA__` → `candidatePreference.skills[].name` | Nama skill bersih, ada `id`, `count`, `status` |
| **Kalibrr** | **Tidak** | Field `jobSdsSkills` ada tetapi `null` di 15/15 lowongan | Harus diturunkan dari teks |
| **Remotive** | **Tidak** | `JobPosting` JSON-LD tidak punya field skill | Harus diturunkan dari teks |

## Dealls — sama seperti proyek referensi

`__NEXT_DATA__` masih ditanam di halaman detail. Bentuknya identik dengan
`parse_detail_skills()` di `Pertemuan 9/scraper.py`:

```json
"candidatePreference": {
  "skillIds": ["63c001e3ff234e00129def24", ...],
  "skills": [
    {"id": "63c001e3ff234e00129def24", "name": "Calendar Management",
     "addedByUser": true, "status": "notProcessed", "count": 179}
  ]
}
```

Perbedaan yang perlu dicatat:

1. **Tag `<script>` kini punya atribut `nonce`.** Regex yang hanya mencocokkan
   `<script id="__NEXT_DATA__"` gagal; perlu
   `<script[^>]*id="__NEXT_DATA__"[^>]*>`. Ini sempat membuat saya salah
   menyimpulkan bahwa `__NEXT_DATA__` sudah tidak ada.
2. **`status: "notProcessed"`** menunjukkan skill ini hasil klasifikasi otomatis
   platform, bukan diketik rekruter. Tetap dipakai, tetapi layak dicatat.
3. **`count`** adalah berapa lowongan lain memakai skill itu — berguna untuk
   bobot rekomendasi PRD-07, bukan untuk ditampilkan sebagai angka.

## Kalibrr — tidak ada skill terstruktur

Diperiksa pada detail lowongan Backend Software Engineer (SMS Finance):

| Field | Nilai |
|---|---|
| `jobSdsSkills` | `null` |
| `duties` | `null` |
| `qualifications` | HTML `<ul><li>…</li></ul>` |

Diperiksa juga 15 lowongan pada halaman `/job-board`: **0/15** punya
`jobSdsSkills` terisi. Artinya field itu ada di skema mereka tetapi belum dipakai
untuk lowongan Indonesia.

Yang tersedia hanya **teks bebas**:

```html
<h2>Kualifikasi Minimum</h2>
<ul>
  <li>Proficient in at least one programming language such as Golang, C++, C, or Python.</li>
  <li>Strong understanding of SQL and NoSQL databases…</li>
  <li>Good communication skills…</li>
</ul>
```

## Remotive — tidak ada skill terstruktur

`<script type="application/ld+json">` dengan `@type: JobPosting` memuat:

```
@context, @type, applicantLocationRequirements, datePosted, description,
employmentType, hiringOrganization, identifier, image, jobLocationType,
occupationalCategory, title, url, validThrough
```

Tidak ada `skills`, `qualifications`, atau `experienceRequirements`. Skill hanya
muncul di dalam `description` sebagai kalimat biasa ("Experience with AWS, GCP,
or AWS is required"). Halaman daftar pun hanya punya tautan filter
`?skills=…`, bukan atribut per lowongan.

## Artinya untuk KarirLens

Konsep `__NEXT_DATA__` hanya bisa dipakai untuk **Dealls**. Untuk dua sumber
lain, skill harus **diturunkan dari teks** — dan itu justru pekerjaan PRD-03,
bukan PRD-02.

### Hasil pengukuran pada HTML asli

Diukur dengan kamus ~90 skill teknologi (bukan soft skill) dan batas kata, pada
dua berkas detail yang dikirim user. Tidak ada AI, tidak ada jaringan.

| Sumber | Bahan | Karakter | Skill dikenali |
|---|---|---|---|
| Remotive | judul saja | 52 | `react` |
| Remotive | deskripsi **penuh** | 4.314 | **26** — hampir semua salah |
| Remotive | deskripsi **dipangkas** | 2.164 | `aws`, `azure`, `gcp`, `python`, `react` |
| Kalibrr | judul saja | 25 | — |
| Kalibrr | kualifikasi + deskripsi | 1.025 | `c++`, `golang`, `python`, `sql` |

**Kenapa deskripsi penuh salah.** Deskripsi Remotive memuat bagian
**"NOT YOUR TECH STACK?"** — daftar kategori platform ("React & Golang, Golang,
React & Java, React & Ruby, PHP & Vue, …"). Itu bukan syarat lowongan ini,
tetapi pencocokan tanpa pangkas membaca semuanya. 26 skill → 5 setelah bagian
itu dipotong.

**Kenapa Kalibrr justru bersih.** Teksnya pendek dan memang berisi syarat:
"Proficient in at least one programming language such as Golang, C++, C, or
Python. Strong understanding of SQL and NoSQL databases". Empat skill yang
dikenali semuanya benar.

**Judul adalah sinyal paling presisi.** "Senior React Full-stack Developer"
→ `react`. Nol salah. Tetapi hanya memberi satu skill.

### Lima cara yang layak dipertimbangkan

| Cara | Presisi | Biaya | Catatan |
|---|---|---|---|
| **A. Kamus + pangkas bagian non-syarat** | Baik (terukur di atas) | Nol | Butuh kamus terisi; aturan pangkas per sumber |
| **B. Judul sebagai sinyal utama, deskripsi sebagai pelengkap** | Paling tinggi | Nol | Judul beberapa lowongan tidak menyebut teknologi |
| **C. Kategori pekerjaan** (`occupationalCategory`, `function`) | Rendah | Nol | "Software Development" terlalu kasar untuk rekomendasi |
| **D. LLM (DeepSeek) saat ingestion** | Tinggi | Uang + tidak deterministik | **Dilarang R-03-14**: normalisasi tidak boleh memanggil layanan eksternal |
| **E. Biarkan kosong** | — | Nol | Rekomendasi berbasis skill hanya memakai lowongan Dealls |

**D tidak bisa dipakai**, dan itu bukan pilihan gaya: R-03-14 melarang
normalisasi memanggil AI. Yang masih boleh adalah memakai LLM **sekali di luar
jalur** untuk menyusun kamus — hasilnya disimpan sebagai berkas, bukan
dipanggil per lowongan.

### Rekomendasi

**A + B, dengan urutan teks yang tegas:**

1. Judul lowongan (paling presisi, bobot penuh).
2. Kualifikasi, bila ada (`qualifications` Kalibrr).
3. Deskripsi, **dipotong** pada penanda bagian non-syarat (`not your tech stack`,
   `how it works`, `about us`, `benefits`).
4. `occupationalCategory` **tidak** dipakai sebagai skill — hanya sebagai
   kategori lowongan.

Hasil terukur pada dua contoh: Kalibrr 4 skill tepat; Remotive 6 skill
(`react`, `python`, `aws`, `azure`, `gcp` + judul) semuanya benar.

Dan **tetap wajib** penanda asal: `declared` (Dealls) vs `inferred`
(Kalibrr/Remotive). Tanpa itu pengguna mengira skill hasil kamus adalah
pernyataan rekruter.

### Yang perlu diputuskan sebelum PRD-03

1. **Isi kamus.** `core/data/skills.json` masih `"skills": []`. Sumber
   terbaik: nama skill bersih dari `candidatePreference.skills` Dealls —
   data nyata, bukan daftar karangan.
2. **Penanda asal skill.** Kolom baru `skills_source` bernilai `declared` atau
   `inferred`.
3. **Daftar penanda pangkas per sumber.** Remotive punya "NOT YOUR TECH STACK?";
   sumber lain akan punya penandanya sendiri.

## Hasil akhir implementasi

Kamus sudah terisi dan pencocokan sudah dipakai. Angka berikut diukur pada
database sungguhan setelah ingestion dengan `--detail`:

| Field | Total | Dealls | Kalibrr | Remotive |
|---|---|---|---|---|
| `company_name` | 49/49 | 18/18 | 15/15 | 16/16 |
| `location` | 49/49 | 18/18 | 15/15 | 16/16 |
| `employment_type` | 49/49 | 18/18 | 15/15 | 16/16 |
| `posted_at` | 49/49 | 18/18 | 15/15 | 16/16 |
| `description` | 49/49 | 18/18 | 15/15 | 16/16 |
| `skills` | 17/49 | **17/18** | 0/15 | 0/16 |
| `salary_min` | 20/49 | 9/18 | 1/15 | 10/16 |

Skill 0 di Kalibrr dan Remotive **bukan kegagalan**: keduanya tidak punya field
skill, dan PRD-03 bertugas menurunkannya lewat `core/skills.py` — yang sudah
diimplementasikan dan diuji. Kolom `skills` akan terisi saat PRD-03 berjalan.

`salary_min` rendah karena sumbernya memang tidak mencantumkan gaji
("Salary Undisclosed" / "Tidak Ditampilkan"), bukan karena parser gagal.

---

## Keputusan akhir: inferensi dinyalakan saat ingestion

Catatan di atas ditulis **sebelum** inferensi benar-benar dipanggil. Saat itu
`core/skills.py` sudah ada dan diuji, tetapi tidak ada satu pun pemanggilnya di
pipeline — akibatnya Kalibrr dan Remotive tetap 0 skill di database, dan
kartunya tampil tanpa satu pun tag sementara kartu Dealls penuh. Itu yang
terlihat janggal di antarmuka.

Inferensi sekarang dijalankan di `scraper/pipeline/normalize.py` lewat
`infer_skills()`, dengan tiga tingkat presisi:

| Tingkat | Bahan | Contoh |
|---|---|---|
| 1 | Judul | "Senior React Full-stack Developer" → `react` |
| 2 | Bagian syarat (di bawah heading) | "Who we're looking for" di Remotive |
| 3 | Kalimat ber-penanda syarat | "Proficient in … Golang, C++, C, or Python" di Kalibrr |

### Yang salah bila deskripsi dibaca apa adanya

Diukur pada database sungguhan. Masing-masing punya penyebab berbeda:

| Lowongan | Skill salah | Penyebab |
|---|---|---|
| Senior Data Engineer (Lemon.io) | `react` | *Boilerplate* perekrut di atas syarat: "New roles for Senior React Full-stack Engineers come in all the time" |
| Content Reviewer (TELUS) | `android`, `ios` | Syarat perangkat: "a reliable computer and a smartphone (Android 5.0, iOS 14 or higher)" |
| Freelance Writer (IAPWE) | `rest api` | Alias kamus `rest` → `rest api` cocok pada "the rest of our content team" |

Tiga perbaikan:

1. **Pemotongan berbasis heading** — hanya teks di bawah "Requirements" /
   "What you'll bring" / "Qualifications" yang dicocokkan, dan berhenti pada
   heading non-syarat ("Benefits", "About us").
2. **Penyaring kalimat perangkat** — kalimat yang menyebut *smartphone*,
   *computer*, *laptop*, *internet connection* dibuang sebelum pencocokan.
3. **Alias `rest` dan `dl` dihapus dari kamus.** Keduanya kata biasa dalam prosa
   Inggris. `rest apis` dan `api integration` ditambahkan agar bentuk yang sah
   tetap dikenali.

### Hasil terukur

Setelah perbaikan, pada 54 baris di database:

| Sumber | Total | `declared` | `inferred` | Kosong |
|---|---|---|---|---|
| dealls | 22 | 19 | 0 | 3 |
| kalibrr | 16 | 0 | 2 | 14 |
| remotive | 16 | 0 | 6 | 10 |
| **total** | **54** | **19** | **8** | **27** |

Bandingkan dengan sebelum inferensi dinyalakan: 17 declared, **0 inferred**.

Cakupan memang tidak penuh, dan itu disengaja. Dari 32 lowongan Kalibrr +
Remotive, membaca seluruh deskripsi memberi 13 yang terisi tetapi dengan skill
palsu (termasuk `react` pada Data Engineer); pendekatan berbasis syarat memberi
8 yang semuanya benar. Untuk data yang tampil di kartu, 8 benar lebih baik
daripada 13 yang sebagian bohong.

Sebagian besar sisanya memang tidak menyebut teknologi apa pun — "Staff General
Affair", "Senior Cook", "Community Officer", "Tax & Audit Staff". Kosong adalah
jawaban yang benar untuk lowongan seperti itu.

### Penanda asal wajib

Kolom `jobs.skills_source` (`declared` / `inferred`, migrasi 004) membedakan
pernyataan sumber dari hasil kamus. Tanpa itu, skill tebakan tampil sama
yakannya dengan yang ditulis rekruter.

Di antarmuka:

- Kartu: penanda kecil `≈` dengan `title`/`aria-label` penjelas.
- Detail: kalimat "Skill disimpulkan dari judul dan deskripsi lowongan, bukan
  daftar resmi dari Kalibrr."

Baris lama yang belum punya penanda diisi mundur: skill Dealls dianggap
`declared` (satu-satunya sumber berfield skill), sumber lain `inferred`.

### Kamus yang dipakai

`core/data/skills.json` berisi **105 skill** dan **80 alias**. Dua sumbernya:

- **Teknis**: dikurasi dari istilah yang benar-benar muncul di teks Kalibrr dan
  Remotive (diukur, bukan dikarang).
- **Soft skill**: dari `candidatePreference.skills` Dealls — vocabulary yang
  dipakai pengguna saat mengonfirmasi skill dari CV.

Pencocokan memakai batas kata dan aturan "entri terpanjang menang", sehingga
`React Native` tidak menghasilkan `react` + `react native`, dan `Golang` tidak
menghasilkan `go` + `golang`.

## Catatan tentang fixture yang dikirim

Empat berkas HTML sudah diterima:

| Berkas | Isi |
|---|---|
| `Lowongan Kerja Backend Software Engineer … .html` | Kalibrr detail — **ada** `__NEXT_DATA__` + `qualifications` |
| `Temukan lowongan kerja terbaru … .html` | Kalibrr board — `__NEXT_DATA__` dengan 15 lowongan |
| `[Hiring] Senior React Full-stack Developer @Lemon.io.html` | Remotive detail — JSON-LD `JobPosting` |
| `Remote Jobs in Programming, Support, Design and more.html` | Remotive board — kartu HTML |

Nama berkasnya panjang dan berasal dari judul halaman. Rencana semula memakai
nama tetap (`kalibrr_board.html`, dst). Saya bisa menyalinnya dengan nama itu
agar test stabil — berkas asli tetap dipertahankan.
