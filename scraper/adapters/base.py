"""Antarmuka adapter: satu-satunya abstraksi yang layak ada di proyek ini.

Ada tiga implementasi nyata dengan kontrak sama (R-02-01); menambah sumber
keempat cukup menambah satu modul. Lihat docs/ARCHITECTURE.md §7.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class RawJob:
    """Hasil parse satu lowongan sebelum normalisasi (R-02-02)."""

    title: str
    source_url: str
    company_name: str | None = None
    location: str | None = None
    employment_type: str | None = None
    description: str | None = None
    skills: list[str] = field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    source_job_id: str | None = None
    posted_at: str | None = None


class BaseAdapter:
    """Kontrak adapter sumber lowongan."""

    name: str
    base_url: str

    def is_allowed(self) -> bool:
        raise NotImplementedError

    def fetch(self, page: int = 1) -> list[dict]:
        raise NotImplementedError

    def parse(self, item: dict) -> RawJob | None:
        raise NotImplementedError

    def iter_jobs(self, max_pages: int = 5) -> Iterator[RawJob]:
        raise NotImplementedError
