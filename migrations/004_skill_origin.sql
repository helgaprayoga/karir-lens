-- Asal skill: deklarasi sumber vs hasil inferensi (PRD-03 lanjutan).
-- Idempoten.
--
-- `declared`  sumber menyatakan skill itu sendiri (Dealls
--             `candidatePreference.skills`, atau `jobSdsSkills` Kalibrr bila terisi)
-- `inferred`  diturunkan dari judul/deskripsi oleh kamus `core/skills.py`
--
-- Tanpa kolom ini, skill hasil kamus tidak dapat dibedakan dari pernyataan
-- rekruter, dan antarmuka akan menampilkannya seolah-olah fakta dari sumber.

alter table jobs
  add column if not exists skills_source text;

alter table jobs
  drop constraint if exists jobs_skills_source_check;

alter table jobs
  add constraint jobs_skills_source_check
  check (skills_source is null or skills_source in ('declared', 'inferred'));
