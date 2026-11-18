"""Aturan bisnis katalog lowongan (PRD-04).

Tempat tinggal: validasi filter defensif (nilai di luar himpunan direset ke
default), penyusunan kriteria, dan pembangunan metadata halaman. Fungsi di sini
dipakai ulang oleh ``app/api`` tanpa perubahan (R-09-15).
"""

from __future__ import annotations

VALID_EMPLOYMENT_TYPES = ("full-time", "part-time", "contract", "internship", "freelance")
VALID_SOURCES = ("dealls", "kalibrr", "remotive")
VALID_SORTS = ("posted_desc", "posted_asc", "relevance")
DEFAULT_SORT = "posted_desc"


def search_jobs(
    *,
    q: str | None = None,
    city: str | None = None,
    employment_type: str | None = None,
    source: str | None = None,
    sort: str | None = None,
    page: str | int | None = None,
    per_page: str | int | None = None,
) -> dict:
    """Cari lowongan dan kembalikan ``{"items", "meta", "filters"}`` (R-04-01..04-04)."""
    raise NotImplementedError("Diisi pada PRD-04.")


def get_job(job_id: int) -> dict:
    """Detail satu lowongan beserta lowongan serupa (R-04-07..R-04-09)."""
    raise NotImplementedError("Diisi pada PRD-04.")
