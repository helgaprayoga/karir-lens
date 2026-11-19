"""Pemuat fixture UI.

Satu-satunya sumber data untuk Track A (docs/tasks/README.md §"Cara Frontend
Dikerjakan Tanpa Backend"). Bentuk berkas JSON di sini adalah **kontrak**: Track
B wajib menghasilkan ``dict`` dengan bentuk yang sama dari ``service``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "ui"

# Opsi chip filter. Disederhanakan pada Track A; PRD-04 mengambilnya dari
# database lewat service.
CITIES = ("Jakarta Selatan", "Jakarta Pusat", "Bandung", "Yogyakarta", "Remote")
EMPLOYMENT_TYPES = (
    ("full-time", "Penuh waktu"),
    ("part-time", "Paruh waktu"),
    ("contract", "Kontrak"),
    ("internship", "Magang"),
    ("freelance", "Lepas"),
)
SOURCES = (("dealls", "Dealls"), ("kalibrr", "Kalibrr"), ("remotive", "Remotive"))


@lru_cache(maxsize=32)
def _load(name: str):
    path = FIXTURE_DIR / f"{name}.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def jobs() -> list[dict]:
    """Daftar lowongan contoh, bentuk `job` PRD-F01 §4.2."""
    return _load("jobs") or []


def jobs_filtered(filters: dict | None = None) -> list[dict]:
    """Terapkan filter secara naif supaya state URL terasa nyata di Track A.

    Ini bukan aturan bisnis produksi: PRD-04 melakukannya di database. Tujuannya
    agar chip dan pencarian pada pratinjau benar-benar mengubah hasil.
    """
    items = jobs()
    if not filters:
        return items

    q = (filters.get("q") or "").strip().lower()
    city = filters.get("city")
    employment_type = filters.get("employment_type")
    source = filters.get("source")

    hasil = []
    for job in items:
        if q and q not in " ".join(
            filter(
                None,
                [
                    (job.get("title") or "").lower(),
                    (job.get("company_name") or "").lower(),
                    " ".join(job.get("skills") or []).lower(),
                ],
            )
        ):
            continue
        if city and job.get("location") != city:
            continue
        if employment_type and job.get("employment_type") != employment_type:
            continue
        if source and job.get("source") != source:
            continue
        hasil.append(job)

    urut = filters.get("sort")
    if urut == "posted_asc":
        hasil.sort(key=lambda j: j.get("posted_at") or "")
    elif urut != "relevance":
        hasil.sort(key=lambda j: j.get("posted_at") or "", reverse=True)

    return hasil


def jobs_page(filters: dict | None = None, page: int = 1, per_page: int = 4) -> dict:
    """``{"items", "meta"}`` untuk halaman katalog.

    ``total`` adalah jumlah item yang benar-benar cocok dengan filter, bukan
    angka karangan. ``per_page`` kecil supaya pagination terlihat pada data
    contoh yang pendek.
    """
    items = jobs_filtered(filters)
    total = len(items)
    page = max(1, int(page or 1))
    mulai = (page - 1) * per_page
    return {
        "items": items[mulai : mulai + per_page],
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_next": mulai + per_page < total,
        },
    }


def jobs_page_empty() -> dict:
    """Keadaan kosong: dipakai untuk memeriksa EmptyState."""
    data = _load("jobs_empty") or []
    return {
        "items": data,
        "meta": {"page": 1, "per_page": 4, "total": 0, "has_next": False},
    }


def job_by_id(job_id: int) -> dict | None:
    for job in jobs():
        if job.get("id") == job_id:
            return job
    return None


def similar_jobs(job: dict, limit: int = 6) -> list[dict]:
    """Lowongan serupa berdasarkan skill yang sama (R-F02-12)."""
    skills = set(job.get("skills") or [])
    others = [j for j in jobs() if j.get("id") != job.get("id")]

    def skor(item: dict) -> int:
        return len(skills & set(item.get("skills") or []))

    beririsan = [j for j in others if skor(j) > 0]
    beririsan.sort(key=skor, reverse=True)
    return beririsan[:limit] or others[:limit]


def jobs_recommended() -> list[dict]:
    return _load("jobs_recommended") or []


def home() -> dict:
    return _load("home") or {}


def company_by_slug(slug: str) -> dict | None:
    for company in companies():
        if company.get("slug") == slug:
            return company
    return None


def filter_options() -> dict:
    return {
        "cities": list(CITIES),
        "employment_types": [{"value": v, "label": l} for v, l in EMPLOYMENT_TYPES],
        "sources": [{"value": v, "label": l} for v, l in SOURCES],
    }


def insights() -> dict:
    return _load("insights") or {}


def profile() -> dict:
    return _load("profile") or {}


def admin() -> dict:
    return _load("admin") or {}


def cv() -> dict:
    return _load("cv") or {}


def runs() -> list[dict]:
    return _load("runs") or []


def companies() -> list[dict]:
    return _load("companies") or []
