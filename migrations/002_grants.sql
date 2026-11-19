-- Grant akses PostgREST untuk KarirLens.
--
-- Mengapa diperlukan: tabel yang dibuat lewat koneksi Postgres langsung dimiliki
-- role `postgres`. Role `anon` dan `authenticated` yang dipakai PostgREST tidak
-- otomatis mendapat izin, sehingga query gagal dengan 42501 "permission denied".
-- Supabase Dashboard biasanya menambahkan grant ini; jalur migrasi manual tidak.
--
-- Catatan keamanan (lihat docs/SUPABASE-SETUP.md §10):
-- Otorisasi KarirLens ditangani di aplikasi Flask (Flask-Login + dekorator
-- login_required/admin_required). Kunci API hanya dipakai server-side, tidak
-- pernah dikirim ke browser. Karena itu RLS tidak diaktifkan pada tabel ini;
-- mengaktifkannya tanpa policy akan memblokir seluruh aplikasi.
-- Bila kelak kunci dipakai di klien, aktifkan RLS dan tulis policy lebih dulu.

grant usage on schema public to anon, authenticated;

grant select, insert, update, delete on all tables in schema public to anon, authenticated;
grant usage, select on all sequences in schema public to anon, authenticated;

-- Tabel dan sequence yang dibuat setelah migrasi ini juga mendapat izin yang sama.
alter default privileges in schema public
  grant select, insert, update, delete on tables to anon, authenticated;

alter default privileges in schema public
  grant usage, select on sequences to anon, authenticated;
