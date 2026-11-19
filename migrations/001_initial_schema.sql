-- Skema awal KarirLens (PRD-01 §4.2).
-- Idempoten: dapat dijalankan ulang tanpa error.
--
-- Urutan pembuatan penting: `clusters` dibuat sebelum `jobs` karena
-- `jobs.cluster_id` mereferensikannya.
--
-- Tabel `applications` sengaja tidak ada, dan tidak ada kolom untuk file atau
-- teks CV (PRD §11.2, §4).

create table if not exists sources (
  id bigint generated always as identity primary key,
  name text not null unique,
  base_url text not null,
  last_scraped_at timestamptz
);

create table if not exists clusters (
  id bigint generated always as identity primary key,
  label text not null,
  keywords text[] default '{}',
  job_count integer default 0,
  created_at timestamptz not null default now()
);

create table if not exists jobs (
  id bigint generated always as identity primary key,
  title text not null,
  company_name text,
  company_slug text,
  location text,
  employment_type text,
  description text,
  skills text[] default '{}',
  salary_min numeric,
  salary_max numeric,
  salary_currency text,
  salary_period text,
  source_id bigint references sources(id),
  source_url text not null unique,
  source_job_id text,
  posted_at timestamptz,
  scraped_at timestamptz not null default now(),
  dedup_hash text,
  cluster_id bigint references clusters(id)
);

create table if not exists scrape_runs (
  id bigint generated always as identity primary key,
  source_id bigint references sources(id),
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,
  jobs_found integer default 0,
  jobs_inserted integer default 0,
  jobs_updated integer default 0,
  error_message text
);

create table if not exists users (
  id bigint generated always as identity primary key,
  email text not null unique,
  password_hash text not null,
  name text,
  role text not null default 'user' check (role in ('user', 'admin')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists saved_jobs (
  user_id bigint not null references users(id),
  job_id bigint not null references jobs(id),
  created_at timestamptz not null default now(),
  unique (user_id, job_id)
);

create table if not exists user_skills (
  id bigint generated always as identity primary key,
  user_id bigint not null references users(id),
  skill text not null,
  source text,
  is_confirmed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index wajib (R-01-07).
create index if not exists jobs_posted_at_idx on jobs (posted_at desc);
create index if not exists jobs_company_slug_idx on jobs (company_slug);
create index if not exists jobs_dedup_hash_idx on jobs (dedup_hash);
create index if not exists jobs_cluster_id_idx on jobs (cluster_id);

-- `source_url` sudah unik lewat constraint, index uniknya dibuat otomatis.
create index if not exists user_skills_user_id_idx on user_skills (user_id);
create index if not exists scrape_runs_started_at_idx on scrape_runs (started_at desc);
