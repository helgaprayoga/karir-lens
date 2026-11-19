"""Runner migrasi SQL langsung ke Supabase (PRD-01 R-01-06).

Pemakaian:
    python -m db migrate          # jalankan migrasi yang belum diterapkan
    python -m db status           # tampilkan migrasi dan statusnya
    python -m db migrate --dry-run

Cara kerja:

1. Tabel ``schema_migrations`` dibuat bila belum ada.
2. Setiap berkas ``migrations/*.sql`` dibaca berurutan menurut nama.
3. Berkas yang belum tercatat dijalankan dalam satu transaksi, lalu dicatat.
4. Berkas yang sudah tercatat dilewati, sehingga aman dijalankan berulang.

Migrasi dijalankan lewat koneksi Postgres langsung (``core/db_direct.py``),
bukan lewat PostgREST, karena PostgREST tidak mengekspos DDL.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from core import config as core_config
from core import db_direct

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"

# Wajib dipanggil sebelum DatabaseConfig.from_env(), jika tidak .env diabaikan.
core_config.load_env(ROOT / ".env")

TRACKING_TABLE = "schema_migrations"

CREATE_TRACKING_TABLE = f"""
create table if not exists {TRACKING_TABLE} (
  version text primary key,
  checksum text not null,
  applied_at timestamptz not null default now()
);
"""


def migration_files() -> list[Path]:
    """Berkas migrasi, terurut menurut nama (mis. ``001_...``)."""
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def applied_migrations(connection) -> dict[str, str]:
    """Peta ``versi -> checksum`` untuk migrasi yang sudah diterapkan."""
    with connection.cursor() as cursor:
        cursor.execute(f"select version, checksum from {TRACKING_TABLE};")
        return {version: sum_ for version, sum_ in cursor.fetchall()}


def ensure_tracking_table(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(CREATE_TRACKING_TABLE)
    connection.commit()


def apply_migration(connection, path: Path) -> None:
    """Jalankan satu berkas migrasi beserta pencatatannya dalam satu transaksi."""
    sql = path.read_text(encoding="utf-8")
    version = path.stem
    digest = checksum(path)

    with connection.cursor() as cursor:
        # Seluruh isi berkas dikirim sebagai satu perintah; psycopg mengizinkan
        # banyak pernyataan dalam satu execute.
        cursor.execute(sql)
        cursor.execute(
            f"insert into {TRACKING_TABLE} (version, checksum) values (%s, %s);",
            (version, digest),
        )
    connection.commit()


def cmd_migrate(dry_run: bool = False) -> int:
    files = migration_files()
    if not files:
        print("Tidak ada berkas migrasi di migrations/.")
        return 1

    config = db_direct.DatabaseConfig.from_env()
    print(f"Target: {config.describe()}\n")

    connection = db_direct.connect(config)
    try:
        ensure_tracking_table(connection)
        already = applied_migrations(connection)

        pending = [path for path in files if path.stem not in already]
        if not pending:
            print("Semua migrasi sudah diterapkan. Tidak ada yang perlu dijalankan.")
            return 0

        for path in files:
            version = path.stem
            if version in already:
                if already[version] != checksum(path):
                    print(f"  UBAH   {version} — berkas berubah setelah diterapkan")
                else:
                    print(f"  LEWATI {version}")
                continue

            if dry_run:
                print(f"  ANTRE  {version}")
                continue

            print(f"  JALAN  {version} ...", end=" ", flush=True)
            try:
                apply_migration(connection, path)
            except Exception as error:  # noqa: BLE001 - pesan Postgres perlu ditampilkan
                connection.rollback()
                print("GAGAL")
                print(f"\n{type(error).__name__}: {error}")
                print("\nTransaksi migrasi dibatalkan; database tidak berubah sebagian.")
                return 1
            print("OK")

        if dry_run:
            print(f"\n{len(pending)} migrasi menunggu. Jalankan tanpa --dry-run untuk menerapkan.")
        else:
            print(f"\nSelesai. {len(pending)} migrasi diterapkan.")
        return 0
    finally:
        connection.close()


def cmd_status() -> int:
    files = migration_files()
    if not files:
        print("Tidak ada berkas migrasi di migrations/.")
        return 1

    config = db_direct.DatabaseConfig.from_env()
    print(f"Target: {config.describe()}\n")

    connection = db_direct.connect(config)
    try:
        ensure_tracking_table(connection)
        already = applied_migrations(connection)

        pending = 0
        for path in files:
            version = path.stem
            if version not in already:
                print(f"  BELUM  {version}")
                pending += 1
            elif already[version] != checksum(path):
                print(f"  UBAH   {version} (berkas berubah setelah diterapkan)")
            else:
                print(f"  OK     {version}")

        print(f"\n{len(files) - pending} diterapkan, {pending} menunggu.")
        return 0
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m db",
        description="Migrasi skema KarirLens langsung ke Postgres Supabase.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate_parser = subparsers.add_parser("migrate", help="Jalankan migrasi yang belum diterapkan.")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Tampilkan tanpa menjalankan.")

    subparsers.add_parser("status", help="Tampilkan status migrasi.")

    args = parser.parse_args(argv)

    try:
        if args.command == "migrate":
            return cmd_migrate(dry_run=args.dry_run)
        return cmd_status()
    except RuntimeError as error:
        print(f"{error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
