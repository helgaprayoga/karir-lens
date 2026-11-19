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


def jobs_page() -> dict:
    """``{"items", "meta"}`` untuk halaman katalog."""
    data = _load("jobs") or []
    return {"items": data, "meta": {"page": 1, "per_page": 12, "total": len(data), "has_next": False}}


def jobs_recommended() -> list[dict]:
    return _load("jobs_recommended") or []


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
