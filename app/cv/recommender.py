"""Perhitungan rekomendasi deterministik, tanpa AI per permintaan (R-07-11).

Bobot kemiripan skill dan kecocokan kategori dibaca dari konfigurasi agar dapat
diuji tanpa jaringan.
"""

from __future__ import annotations

DEFAULT_SKILL_WEIGHT = 0.75
DEFAULT_CATEGORY_WEIGHT = 0.25


def score(job: dict, confirmed_skills: set[str], cluster_id: int | None) -> tuple[float, list[str]]:
    """Skor dan alasan singkat, mis. ``["skill: python", "kategori: Backend"]``."""
    raise NotImplementedError("Diisi pada PRD-07.")
