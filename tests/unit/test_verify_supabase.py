"""Verifikasi skema Supabase: klasifikasi error dan batasan scope.

Tidak menyentuh jaringan. Klien Supabase diganti stub agar logika
``preflight`` dan ``verify_scope_exclusions`` dapat diuji secara deterministik.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_supabase.py"


@pytest.fixture(scope="module")
def verify_module():
    spec = importlib.util.spec_from_file_location("verify_supabase", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _StubTable:
    def __init__(self, error: Exception | None, rows=None) -> None:
        self._error = error
        self._rows = rows or []

    def select(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self._error:
            raise self._error
        return type("Response", (), {"data": self._rows, "count": len(self._rows)})()


class _StubClient:
    def __init__(self, error: Exception | None = None, rows=None) -> None:
        self._error = error
        self._rows = rows

    def table(self, _name):
        return _StubTable(self._error, self._rows)


# --- Klasifikasi error -----------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        'relation "public.jobs" does not exist',
        'PGRST205: Could not find the table public.jobs',
        'ERROR: 42P01: relation "jobs" does not exist',
    ],
)
def test_missing_relation_detected(verify_module, message: str) -> None:
    assert verify_module._is_missing_relation(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "[Errno 11001] getaddrinfo failed",
        "HTTPSConnectionPool: Max retries exceeded",
        "connection refused",
        "read timed out",
    ],
)
def test_connectivity_error_detected(verify_module, message: str) -> None:
    assert verify_module._is_connectivity_error(message) is True


def test_missing_relation_is_not_connectivity_error(verify_module) -> None:
    message = 'relation "public.jobs" does not exist'
    assert verify_module._is_connectivity_error(message) is False


# --- Preflight -------------------------------------------------------------

def test_preflight_fails_on_unreachable_host(verify_module) -> None:
    """Kegagalan jaringan harus menghentikan pemeriksaan, bukan lolos."""
    client = _StubClient(error=OSError("[Errno 11001] getaddrinfo failed"))
    assert verify_module.preflight(client) is False


def test_preflight_passes_when_only_relation_missing(verify_module) -> None:
    """Tersambung tetapi tabel belum ada bukan kegagalan koneksi."""
    client = _StubClient(error=Exception('relation "public.sources" does not exist'))
    assert verify_module.preflight(client) is True


def test_preflight_passes_when_reachable(verify_module) -> None:
    assert verify_module.preflight(_StubClient(rows=[])) is True


# --- Batasan scope ---------------------------------------------------------

def test_scope_passes_when_applications_missing(verify_module) -> None:
    client = _StubClient(error=Exception('relation "public.applications" does not exist'))
    assert verify_module.verify_scope_exclusions(client) is True


def test_scope_fails_when_applications_exists(verify_module) -> None:
    """Tabel tracker lamaran tidak boleh ada (PRD §4)."""
    assert verify_module.verify_scope_exclusions(_StubClient(rows=[{"id": 1}])) is False


def test_scope_does_not_pass_on_connectivity_error(verify_module) -> None:
    """Koneksi gagal bukan bukti tabel tidak ada — ini bug yang harus dicegah."""
    client = _StubClient(error=OSError("[Errno 11001] getaddrinfo failed"))
    assert verify_module.verify_scope_exclusions(client) is False


# --- Konfigurasi -----------------------------------------------------------

def test_required_columns_cover_schema(verify_module) -> None:
    """Setiap tabel wajib punya daftar kolom, agar verifikasi tidak diam-diam melewatkan."""
    for table in verify_module.REQUIRED_TABLES:
        assert table in verify_module.REQUIRED_COLUMNS


def test_scope_excludes_cv_columns(verify_module) -> None:
    """Tidak ada kolom penyimpanan CV pada tabel mana pun (PRD §11.2)."""
    for table, columns in verify_module.REQUIRED_COLUMNS.items():
        for column in columns:
            assert not column.startswith("cv"), f"{table}.{column} menyimpan CV"
            assert column not in {"resume", "resume_path", "cv_text"}, f"{table}.{column} menyimpan CV"
