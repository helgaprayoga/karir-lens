"""Koneksi langsung ke Postgres Supabase untuk menjalankan migrasi.

Berbeda dari ``core/db.py``:

- ``core/db.py`` berbicara lewat **PostgREST** (client ``supabase``). Itu API
  untuk baris data; ia tidak bisa menjalankan ``CREATE TABLE``.
- Modul ini berbicara lewat **protokol Postgres** memakai ``psycopg``, sehingga
  DDL bisa dijalankan dari program — sama seperti ``php artisan migrate`` pada
  Laravel.

Dipakai hanya oleh ``python -m db migrate``. Aplikasi web tetap memakai
``core/db.py``.

Modul ini tidak mengimpor Flask (docs/ARCHITECTURE.md §4 aturan 4).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    """Parameter koneksi langsung ke Postgres Supabase."""

    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        missing = [
            name
            for name in ("SUPABASE_DB_HOST", "SUPABASE_DB_USER", "SUPABASE_DB_PASSWORD")
            if not (os.environ.get(name) or "").strip()
        ]
        if missing:
            from core.config import PROJECT_ROOT

            env_file = PROJECT_ROOT / ".env"
            hint = (
                f"Berkas .env ditemukan di {env_file}, tetapi variabel tersebut kosong di sana."
                if env_file.is_file()
                else f"Berkas .env TIDAK ditemukan di {env_file}."
            )
            raise RuntimeError(
                "Koneksi database langsung belum dikonfigurasi.\n"
                f"Variabel yang kosong: {', '.join(missing)}\n"
                f"{hint}\n"
                "Isi dari dashboard Supabase: Settings -> Database -> Connection string "
                "(tab Session pooler, port 5432).\n"
                "Lihat docs/SUPABASE-SETUP.md §3.2 dan §5."
            )

        port_raw = (os.environ.get("SUPABASE_DB_PORT") or "5432").strip()
        try:
            port = int(port_raw)
        except ValueError:
            raise RuntimeError(f"SUPABASE_DB_PORT harus angka, bukan {port_raw!r}.") from None

        return cls(
            host=(os.environ.get("SUPABASE_DB_HOST") or "").strip(),
            port=port,
            database=(os.environ.get("SUPABASE_DB_NAME") or "postgres").strip(),
            user=(os.environ.get("SUPABASE_DB_USER") or "").strip(),
            password=os.environ.get("SUPABASE_DB_PASSWORD") or "",
            sslmode=(os.environ.get("SUPABASE_DB_SSLMODE") or "require").strip(),
        )

    def describe(self) -> str:
        """Ringkasan aman untuk ditampilkan; password tidak pernah ikut."""
        return f"{self.user}@{self.host}:{self.port}/{self.database} (sslmode={self.sslmode})"

    def dsn(self) -> str:
        """DSN libpq. Nilai di-escape agar password bertanda khusus tetap aman."""
        from psycopg.conninfo import make_conninfo

        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
            sslmode=self.sslmode,
        )


def connect(config: DatabaseConfig | None = None):
    """Buka koneksi Postgres. Pemanggil bertanggung jawab menutupnya."""
    import psycopg

    config = config or DatabaseConfig.from_env()
    return psycopg.connect(config.dsn(), autocommit=False)
