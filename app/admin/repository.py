"""Akses data panel admin (PRD-09).

Membaca tabel ``jobs``, ``users``, ``scrape_runs``, dan ``clusters`` untuk
keperluan pemantauan.
"""

from __future__ import annotations


def count_jobs() -> int:
    raise NotImplementedError("Diisi pada PRD-09.")


def count_users() -> int:
    raise NotImplementedError("Diisi pada PRD-09.")


def find_recent_runs(limit: int = 10) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-09.")


def find_jobs_page(query: str | None, offset: int, limit: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-09.")


def find_users_page(offset: int, limit: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-09.")


def find_clusters() -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-09.")


def delete_job(job_id: int) -> None:
    raise NotImplementedError("Diisi pada PRD-09.")
