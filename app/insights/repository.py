"""Akses data untuk insight (PRD-05).

Modul insight membaca tabel ``jobs`` dan ``clusters`` lewat repository miliknya
sendiri, bukan lewat ``app/jobs/repository.py`` (docs/ARCHITECTURE.md §5).
"""

from __future__ import annotations


def find_jobs_with_salary(currency: str | None = None, period: str | None = None) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")


def find_clusters() -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")


def find_jobs_by_company(slug: str) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")


def find_skill_counts(limit: int = 15) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-05.")
