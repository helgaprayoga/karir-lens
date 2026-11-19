# PRD-F05 — Insight dan Admin (Frontend)

| Field | Keterangan |
|---|---|
| ID task | PRD-F05 |
| Nama task | Insight dan Admin |
| Track | A — Frontend |
| Prioritas | P0 |
| Dependensi | PRD-F01, PRD-F02 |
| Task yang bergantung | PRD-F06 |
| Status | Belum dimulai |
| PRD induk | [PRD KarirLens](../PRD.md) |
| Backend pasangan | [PRD-05](./PRD-05-perusahaan-insight.md), [PRD-09](./PRD-09-admin-api.md) |
| Design system | [Design System KarirLens](../design-system.md) |

---

## 1. Konteks

Insight dan panel admin adalah dua permukaan yang paling banyak menampilkan angka. Design system §2 butir 3 menetapkan prinsip "jujur terhadap data": angka dan badge hanya tampil bila datanya ada, dan statistik gaji tidak muncul bila sampel kurang dari lima. Prinsip itu harus diwujudkan di tampilan, bukan hanya di service.

Task ini membangun `/insights` dengan Chart.js, dan seluruh halaman `/admin/*`, termasuk state "data terbatas" yang harus tampil sebagai pesan jelas, bukan grafik kosong.

## 2. Tujuan

1. Membangun `/insights`: kategori, skill populer, statistik gaji, dengan grafik Chart.js.
2. Menampilkan state "data terbatas" saat sampel tidak mencukupi.
3. Membangun `/admin`: ringkasan, daftar lowongan, pengguna, riwayat run, tinjauan cluster.
4. Menyediakan `DataTable` dan `StatusPill` untuk seluruh halaman admin.
5. Menetapkan kontrak template untuk PRD-05 dan PRD-09.

## 3. Scope

### 3.1 Termasuk

- `/insights`: kartu statistik, grafik distribusi kategori, grafik skill, statistik gaji per mata uang.
- State "data terbatas" dan pesan bila sampel < 5.
- Chart.js lokal dari `static/vendor/` dengan registry `state.charts`.
- `/admin`: kartu ringkasan, `/admin/jobs`, `/admin/users`, `/admin/runs`, `/admin/clusters`.
- `DataTable` dengan pagination dan pencarian.
- `StatusPill` untuk status run (success, partial, failed, running, skipped).
- Konfirmasi sebelum menghapus lowongan.

### 3.2 Tidak termasuk

- Perhitungan clustering, agregasi, dan statistik (PRD-05).
- Pengecekan peran admin, query admin, hapus data (PRD-09).
- Endpoint REST API (PRD-09).
- Akses atau tampilan data CV di admin (dilarang R-09-09).

## 4. Requirement

| ID | Requirement | Prioritas |
|---|---|---|
| R-F05-01 | `/insights` menampilkan jumlah lowongan per kategori, skill populer, dan statistik gaji. | P0 |
| R-F05-02 | Statistik gaji menampilkan median, P25, P75, dan jumlah sampel. | P0 |
| R-F05-03 | Bila sampel < 5, tampil pesan data terbatas, bukan grafik kosong atau angka nol. | P0 |
| R-F05-04 | Mata uang berbeda tidak ditampilkan dalam satu grafik atau satu angka. | P0 |
| R-F05-05 | Grafik memakai Chart.js dan tetap terbaca pada 360 px. | P0 |
| R-F05-06 | Setiap grafik punya ringkasan teks atau tabel alternatif untuk pembaca layar. | P0 |
| R-F05-07 | Tidak ada field atau angka prediksi di mana pun. | P0 |
| R-F05-08 | `/admin` menampilkan kartu ringkasan: jumlah lowongan, pengguna, run terbaru. | P0 |
| R-F05-09 | `/admin/jobs` menyediakan pencarian, pagination, dan aksi hapus dengan konfirmasi. | P0 |
| R-F05-10 | `/admin/users` menyediakan daftar pengguna dengan pagination; tidak menampilkan password. | P0 |
| R-F05-11 | `/admin/runs` menampilkan waktu, status, jumlah ditemukan/disimpan/diperbarui, dan pesan error. | P0 |
| R-F05-12 | `/admin/clusters` menampilkan label, kata kunci, dan jumlah lowongan per cluster. | P0 |
| R-F05-13 | Tidak ada route, tautan, atau elemen yang menampilkan berkas atau teks CV di admin. | P0 |
| R-F05-14 | DataTable dapat dipakai dengan keyboard dan menandai baris terpilih. | P0 |
| R-F05-15 | Konfirmasi hapus memakai dialog yang dapat dibatalkan dan tidak langsung menghapus. | P0 |

### 4.1 Kontrak Template

**`insights/index.html`** menerima:

```json
{
  "categories": [{"cluster_id": 1, "label": "Backend", "job_count": 120, "keywords": ["python"]}],
  "skills": [{"skill": "python", "job_count": 210}],
  "salary": [{"currency": "IDR", "period": "month", "sample": 42, "median": 9000000, "p25": 7000000, "p75": 12000000}],
  "sample_sufficient": true
}
```

`sample_sufficient = false` wajib memicu `AlertBanner` varian data terbatas, bukan grafik kosong.

**`admin/index.html`** menerima `summary` (`{job_count, user_count, latest_runs}`).
**`admin/jobs.html`** dan **`admin/users.html`** menerima `items` dan `meta`.
**`admin/runs.html`** menerima `runs` (`list[dict]` dengan `status`, `started_at`, `finished_at`, `jobs_found`, `jobs_inserted`, `jobs_updated`, `error_message`).
**`admin/clusters.html`** menerima `clusters` (`list[dict]` dengan `label`, `keywords`, `job_count`).

## 5. Acceptance Criteria

- [ ] `/insights` menampilkan kategori, skill, dan gaji dari fixture.
- [ ] Statistik gaji menampilkan median, P25, P75, dan sampel.
- [ ] Sampel < 5 memunculkan pesan data terbatas, bukan grafik kosong.
- [ ] Mata uang tidak pernah dicampur dalam satu grafik.
- [ ] Grafik terbaca pada 360 px.
- [ ] Setiap grafik punya alternatif tekstual.
- [ ] Tidak ada angka prediksi.
- [ ] `/admin` menampilkan kartu ringkasan.
- [ ] `/admin/jobs` mendukung pencarian, pagination, dan hapus dengan konfirmasi.
- [ ] `/admin/users` tidak menampilkan password atau CV.
- [ ] `/admin/runs` menampilkan status dan pesan error.
- [ ] `/admin/clusters` menampilkan label, kata kunci, dan jumlah.
- [ ] Tidak ada tautan atau elemen CV di panel admin.
- [ ] DataTable dan dialog konfirmasi dapat dipakai dengan keyboard.

## 6. Dependensi

- PRD-F01 (komponen, `StatTile`, `MetricCell`, `ChartCard`, `DataTable` dasar).
- PRD-F02 (`JobCard` untuk daftar lowongan admin).
- Chart.js lokal di `static/vendor/`.
- Fixture `tests/fixtures/ui/insights.json`, `admin.json`.

## 7. Test Plan

### 7.1 Pengujian Otomatis (pytest)

| Test | Cakupan |
|---|---|
| `test_insights_renders_sections` | Tiga bagian insight terender dari fixture. |
| `test_salary_shows_quartiles` | Median, P25, P75, sampel tampil. |
| `test_insufficient_sample_message` | `sample_sufficient=false` memicu banner data terbatas. |
| `test_no_chart_when_insufficient` | Tidak ada elemen kanvas grafik gaji saat sampel kurang. |
| `test_currency_not_mixed` | Setiap grafik gaji hanya memuat satu mata uang. |
| `test_chart_has_text_alternative` | Setiap grafik punya ringkasan teks. |
| `test_no_prediction_fields` | Tidak ada label atau nilai prediksi di markup. |
| `test_admin_summary_tiles` | Kartu ringkasan sesuai fixture. |
| `test_admin_users_no_password` | Markup tidak memuat `password` atau `password_hash`. |
| `test_admin_no_cv_links` | Tidak ada tautan atau teks CV di `/admin*`. |
| `test_admin_runs_status_pills` | Setiap status memakai `StatusPill` yang sesuai. |
| `test_delete_requires_confirmation` | Aksi hapus memakai dialog konfirmasi. |
| `test_datatable_keyboard` | Tabel dapat difokuskan dan baris menandai state. |

### 7.2 Pengujian Manual

1. Buka `/insights` dan cocokkan angka dengan fixture.
2. Uji fixture sampel < 5 dan pastikan pesan data terbatas tampil.
3. Periksa grafik pada 360 px dan 1280 px.
4. Buka setiap halaman admin dan periksa kartu, tabel, dan status.
5. Coba hapus lowongan dan batalkan di dialog konfirmasi.
6. Pastikan tidak ada jejak CV di panel admin mana pun.

## 8. Out of Scope

- Perhitungan clustering, agregasi, dan statistik (PRD-05).
- Pengecekan peran dan operasi data admin (PRD-09).
- Endpoint API publik dan personal (PRD-09).
- Analitik lanjutan dan ekspor data.

## 9. Catatan Teknis

- Chart.js dimuat dari `static/vendor/chart.umd.min.js`, bukan CDN, agar demo tidak bergantung jaringan.
- Pola registry `state.charts` + `destroyChart(key)` wajib dipakai agar grafik aman saat data berubah.
- Warna grafik diambil dari token, bukan nilai hex.
- Alternatif tekstual grafik memakai `<details>` berisi tabel angka, agar tetap terbaca pembaca layar.
- Dialog konfirmasi memakai `<dialog>` native agar fokus terkelola tanpa pustaka.
- DataTable menampilkan batas baris per halaman; jangan memuat seluruh tabel.

## 10. Referensi Proyek

| Berkas rujukan | Bagian yang diadopsi |
|---|---|
| `docs/design-preview.html` baris 905–938 | Panel statistik pada rail: grid cell, angka besar, caption, bar mini. |
| `docs/design-system.md` §4.8 `StatTile`/`MetricCell`/`ChartCard`, §4.9 `Pagination`, §4.11 `StatusPill`, §4.18 `AlertBanner` | Anatomi komponen yang dipakai kedua halaman. |
| Bot Utang-Piutang — `static/js/dashboard.js` (`state.charts`, `destroyChart`) | Registry grafik dan penghancuran grafik lama sebelum membuat baru. |
| Bot Utang-Piutang — `formatRupiah()`, `formatRupiahSingkat()` | Format rupiah `id-ID` dan notasi kompak untuk sumbu grafik. |
| BengkelBot — `app.py` `admin()`, `templates/admin.html` | Struktur dashboard admin: kartu ringkasan, tabel distribusi, daftar baris terbaru. |
| Dashboard Analisis PLN — `tabs/tab_clustering.py` `render_tab_clustering()` | Pola pesan data terbatas sebagai peringatan, bukan grafik kosong. |

**Yang tidak diambil**

- Streamlit, matplotlib, dan wordcloud sebagai tampilan.
- Statistik intent chatbot dan riwayat chat di admin.
- Metrik kelengkapan profil dan skor performa (design system §6).

## 11. Definition of Done

- Semua acceptance criteria terpenuhi.
- Test otomatis pada §7.1 lulus.
- `/insights` dan seluruh `/admin/*` dapat ditinjau di browser dengan fixture.
- Kontrak template pada §4.1 tertulis dan dipakai PRD-05 serta PRD-09.
