-- Penanda duplikat lintas sumber (PRD-03 R-03-09).
-- Idempoten: dapat dijalankan ulang tanpa error.
--
-- `duplicate_of` menunjuk baris `jobs` lain yang dianggap lowongan sama dari
-- sumber berbeda. Baris duplikat TIDAK dihapus (R-03-10): tautan asli tetap
-- disimpan, dan tampilan yang memutuskan mana yang ditampilkan.
--
-- Tanpa ON DELETE CASCADE: bila baris induk hilang, penanda cukup menjadi
-- NULL dan barisnya tetap ada. Menghapus ikut akan menghilangkan data yang
-- masih punya nilai.

alter table jobs
  add column if not exists duplicate_of bigint references jobs(id);

alter table jobs
  add column if not exists dedup_source text;

-- Pencarian duplikat: "apakah hash ini sudah ada di sumber lain?"
create index if not exists jobs_duplicate_of_idx on jobs (duplicate_of);
