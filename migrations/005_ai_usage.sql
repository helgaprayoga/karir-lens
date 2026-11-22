-- Batas harian asisten AI per pengguna (PRD-08 R-08-09).
-- Idempoten.
--
-- Disimpan di tabel, bukan memori proses: beberapa worker atau restart
-- aplikasi akan menghapus penghitung di memori, dan batas harian menjadi tidak
-- berarti. Satu baris per pertanyaan mencukupi — batasnya puluhan per hari,
-- jadi tabel ini tidak akan bertumbuh besar.
--
-- Yang TIDAK disimpan: pertanyaan maupun jawaban. R-08-11 melarangnya, dan
-- hanya jumlah pertanyaan yang dibutuhkan untuk menegakkan batas.

create table if not exists ai_usage (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id),
  tanggal date not null default current_date,
  created_at timestamptz not null default now()
);

create index if not exists ai_usage_user_tanggal_idx on ai_usage (user_id, tanggal);
