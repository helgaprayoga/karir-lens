"""Logging tidak menulis data sensitif (R-01-13) dan skema bersifat idempoten
(R-01-06, R-01-07).

Pemeriksaan SQL dilakukan dengan membaca berkas migrasi, bukan menjalankan
database, agar test tetap berjalan tanpa Supabase.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from app.logging_config import SensitiveDataFilter, redact

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "001_initial_schema.sql"


# --- Penyaring log ---------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "login password=rahasia123",
        "password: rahasia123",
        "csrf_token=abc.def-ghi",
        "api_key=sk-live-12345",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
        "SECRET=hunter2",
    ],
)
def test_redact_removes_secret_values(message: str) -> None:
    result = redact(message)

    assert "rahasia123" not in result
    assert "sk-live-12345" not in result
    assert "eyJhbGciOiJIUzI1NiJ9" not in result
    assert "hunter2" not in result


def test_redact_keeps_ordinary_text() -> None:
    message = "Scrape dealls selesai: 42 lowongan, 3 error."

    assert redact(message) == message


def test_filter_redacts_rendered_message() -> None:
    """Nilai di ``args`` ikut tersaring karena pesan dirender lebih dulu."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="user %s password=%s",
        args=("budi@example.com", "rahasia123"),
        exc_info=None,
    )

    SensitiveDataFilter().filter(record)

    rendered = record.getMessage()
    assert "rahasia123" not in rendered
    assert "budi@example.com" in rendered


def test_configure_logging_does_not_duplicate_handlers() -> None:
    """``create_app`` dipanggil berkali-kali dalam test; handler tidak menumpuk."""
    from app.logging_config import configure_logging

    configure_logging(logging.INFO)
    first = len(logging.getLogger().handlers)
    configure_logging(logging.INFO)

    assert len(logging.getLogger().handlers) == first


# --- Skema -----------------------------------------------------------------

def test_migration_is_idempotent() -> None:
    """Setiap tabel dan index memakai ``IF NOT EXISTS`` (R-01-06)."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    creates = re.findall(r"create\s+(?:table|index)\s+(?!if not exists)", sql)
    assert creates == [], f"Ada pernyataan CREATE tanpa IF NOT EXISTS: {creates}"

    assert "create table if not exists" in sql
    assert "create index if not exists" in sql


@pytest.mark.parametrize(
    "table",
    ["sources", "jobs", "scrape_runs", "users", "saved_jobs", "user_skills", "clusters"],
)
def test_migration_creates_required_tables(table: str) -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert f"create table if not exists {table}" in sql


def test_migration_declares_unique_constraints() -> None:
    """``users.email`` unik dan ``saved_jobs`` unik per (user_id, job_id) (R-01-07)."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "email text not null unique" in sql
    assert "unique (user_id, job_id)" in sql
    assert "source_url text not null unique" in sql


@pytest.mark.parametrize(
    "index",
    ["jobs_posted_at_idx", "jobs_company_slug_idx", "jobs_dedup_hash_idx"],
)
def test_migration_declares_required_indexes(index: str) -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert f"create index if not exists {index}" in sql


def _sql_without_comments() -> str:
    """SQL tanpa komentar, agar penanda "tidak ada tabel X" di komentar tidak
    dianggap sebagai deklarasi tabel."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def test_migration_has_no_out_of_scope_objects() -> None:
    """Tidak ada tabel tracker lamaran dan tidak ada kolom penyimpanan CV."""
    sql = _sql_without_comments()

    assert "applications" not in sql
    assert "application_status" not in sql
    assert "cv_" not in sql
    assert "resume" not in sql


def test_clusters_created_before_jobs() -> None:
    """``jobs.cluster_id`` mereferensikan ``clusters``; urutan pembuatan penting."""
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert sql.index("create table if not exists clusters") < sql.index("create table if not exists jobs")
