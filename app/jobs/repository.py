"""Akses data tabel ``jobs`` untuk katalog publik (PRD-04).

Semua query PostgREST hidup di sini; nilai filter diikat, tidak pernah disusun
dari string mentah (R-04-05).
"""

from __future__ import annotations

TABLE = "jobs"


def find_page(criteria: dict, offset: int, limit: int) -> list[dict]:
    """Sebagian baris sesuai kriteria dan rentang halaman."""
    raise NotImplementedError("Diisi pada PRD-04.")


def count(criteria: dict) -> int:
    """Jumlah baris yang cocok, untuk metadata pagination."""
    raise NotImplementedError("Diisi pada PRD-04.")


def find_by_id(job_id: int) -> dict | None:
    raise NotImplementedError("Diisi pada PRD-04.")


def find_similar(job: dict, limit: int = 6) -> list[dict]:
    """Lowongan serupa berdasarkan skill yang sama (R-04-09)."""
    raise NotImplementedError("Diisi pada PRD-04.")
