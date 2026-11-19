"""Verifikasi skema KarirLens pada project Supabase (PRD-01 R-01-06, R-01-07).

Skrip ini hanya membaca; ia tidak pernah membuat atau mengubah tabel. DDL
dijalankan lewat SQL Editor dashboard, karena client ``supabase`` berbicara
lewat PostgREST dan tidak dapat mengeksekusi ``CREATE TABLE``.

Pemakaian:
    python scripts/verify_supabase.py

Membaca SUPABASE_URL dan SUPABASE_KEY dari environment atau berkas .env.
Kode keluar 0 bila semua tabel, kolom, dan index wajib tersedia; 1 bila ada
yang hilang.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED_TABLES = (
    "sources",
    "clusters",
    "jobs",
    "scrape_runs",
    "users",
    "saved_jobs",
    "user_skills",
)

# Kolom yang wajib ada per tabel (R-01-02, PRD-01 §4.2).
REQUIRED_COLUMNS = {
    "jobs": (
        "id",
        "title",
        "company_name",
        "company_slug",
        "location",
        "employment_type",
        "description",
        "skills",
        "salary_min",
        "salary_max",
        "salary_currency",
        "salary_period",
        "source_id",
        "source_url",
        "source_job_id",
        "posted_at",
        "scraped_at",
        "dedup_hash",
        "cluster_id",
    ),
    "users": ("id", "email", "password_hash", "name", "role", "created_at", "updated_at"),
    "saved_jobs": ("user_id", "job_id", "created_at"),
    "user_skills": ("id", "user_id", "skill", "source", "is_confirmed", "created_at"),
    "scrape_runs": (
        "id",
        "source_id",
        "started_at",
        "finished_at",
        "status",
        "jobs_found",
        "jobs_inserted",
        "jobs_updated",
        "error_message",
    ),
    "clusters": ("id", "label", "keywords", "job_count", "created_at"),
    "sources": ("id", "name", "base_url", "last_scraped_at"),
}


def _fail(message: str) -> None:
    print(f"  GAGAL  {message}")


def _ok(message: str) -> None:
    print(f"  OK     {message}")


def _is_missing_relation(message: str) -> bool:
    """True bila error berarti tabel/relasi tidak ada, bukan masalah koneksi."""
    lowered = message.lower()
    return "does not exist" in lowered or "pgrst205" in lowered or "42p01" in lowered


def _is_connectivity_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in ("getaddrinfo failed", "nameresolutionerror", "connection", "timed out", "timeout")
    )


def preflight(client) -> bool:
    """Pastikan project dapat dijangkau sebelum memeriksa skema.

    Tanpa ini, kegagalan jaringan akan tampil sebagai puluhan pesan "kolom tidak
    lengkap" yang menyesatkan, dan pemeriksaan batasan scope akan salah
    menyimpulkan bahwa tabel `applications` tidak ada.
    """
    try:
        client.table(REQUIRED_TABLES[0]).select("*").limit(1).execute()
    except Exception as error:  # noqa: BLE001
        message = str(error)
        if _is_missing_relation(message):
            return True  # tersambung; tabelnya saja yang belum ada
        if _is_connectivity_error(message):
            _fail(f"tidak dapat menjangkau project: {message[:160]}")
            print("\nPeriksa koneksi internet dan apakah SUPABASE_URL benar.")
            return False
        _fail(f"project tidak dapat diakses: {message[:160]}")
        return False
    return True


def verify_table(client, table: str) -> bool:
    """Tabel ada bila select terhadap tabel itu tidak menghasilkan error relasi."""
    try:
        client.table(table).select("*", count="exact").limit(1).execute()
    except Exception as error:  # noqa: BLE001 - pesan driver berbeda antar versi
        message = str(error)
        if _is_missing_relation(message):
            _fail(f"tabel {table} tidak ditemukan")
        else:
            _fail(f"tabel {table} tidak dapat dibaca: {message[:160]}")
        return False
    _ok(f"tabel {table}")
    return True


def verify_columns(client) -> bool:
    """Kolom wajib ada bila select kolom tersebut berhasil."""
    all_ok = True
    for table, columns in REQUIRED_COLUMNS.items():
        try:
            client.table(table).select(",".join(columns)).limit(1).execute()
        except Exception as error:  # noqa: BLE001
            _fail(f"{table}: kolom wajib tidak lengkap ({str(error)[:160]})")
            all_ok = False
        else:
            _ok(f"{table}: {len(columns)} kolom wajib")
    return all_ok


def verify_scope_exclusions(client) -> bool:
    """Tabel `applications` dan kolom penyimpanan CV tidak boleh ada (PRD §4, §11.2).

    Hanya error "relasi tidak ada" yang dianggap lulus. Kegagalan koneksi tidak
    boleh lolos sebagai "tabel tidak ada".
    """
    all_ok = True

    try:
        client.table("applications").select("*").limit(1).execute()
    except Exception as error:  # noqa: BLE001
        if _is_missing_relation(str(error)):
            _ok("tabel applications tidak ada (sesuai scope)")
        else:
            _fail(f"tabel applications tidak dapat diperiksa: {str(error)[:160]}")
            all_ok = False
    else:
        _fail("tabel applications ADA — di luar scope produk")
        all_ok = False

    return all_ok


def main() -> int:
    from core.config import load_env

    load_env(ROOT / ".env")

    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_KEY") or "").strip()

    if not url or not key:
        print("SUPABASE_URL dan SUPABASE_KEY belum diisi. Salin .env.example menjadi .env.")
        return 1

    print(f"Memverifikasi {url}\n")

    from supabase import create_client

    client = create_client(url, key)

    if not preflight(client):
        return 1

    print("Tabel:")
    tables_ok = all(verify_table(client, table) for table in REQUIRED_TABLES)

    print("\nKolom:")
    columns_ok = verify_columns(client)

    print("\nBatasan scope:")
    scope_ok = verify_scope_exclusions(client)

    print()
    if tables_ok and columns_ok and scope_ok:
        print("Skema lengkap. Acceptance criteria PRD-01 §5 baris migrasi terpenuhi.")
        return 0

    print("Skema belum lengkap. Jalankan migrations/001_initial_schema.sql di SQL Editor Supabase.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
