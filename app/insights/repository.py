"""Akses data untuk insight (PRD-05).

Modul insight membaca tabel ``jobs`` dan ``clusters`` lewat repository miliknya
sendiri, bukan lewat ``app/jobs/repository.py`` (docs/ARCHITECTURE.md §5).

PRD-04 hanya membutuhkan bagian perusahaan (R-04-07): ringkasan yang
diturunkan dari tabel ``jobs`` tanpa tabel perusahaan tersendiri.
"""

from __future__ import annotations

from core import db as core_db

TABLE = "jobs"


def _client():
    return core_db.get_db()


def find_jobs_by_company(slug: str) -> list[dict]:
    """Semua lowongan satu perusahaan, terbaru lebih dulu (R-04-07)."""
    hasil = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("company_slug", slug)
        .order("posted_at", desc=True)
        .execute()
    )
    return hasil.data or []


def find_sources() -> list[dict]:
    """``source_id`` -> nama sumber, untuk kolom ``source`` pada kontrak job.

    Dimiliki repository insight sendiri, bukan dipinjam dari
    ``app.jobs.repository``: aturan arsitektur §4 butir 2 membatasi setiap
    service pada repository modulnya sendiri.
    """
    return _client().table("sources").select("id,name").execute().data or []


def find_jobs_with_salary(currency: str | None = None, period: str | None = None) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")


def find_clusters() -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")


def find_skill_counts(limit: int = 15) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")
