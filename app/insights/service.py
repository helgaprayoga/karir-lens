"""Aturan bisnis insight (PRD-05).

Tempat tinggal: aturan sampel gaji minimal, pemisahan mata uang, dan larangan
menampilkan prediksi. Dipakai ulang oleh ``/api/insights/*`` (R-05-15, R-09-15).
"""

from __future__ import annotations


def get_categories() -> dict:
    """Distribusi lowongan per kategori/cluster (R-05-06)."""
    raise NotImplementedError("Diisi pada PRD-05.")


def get_top_skills(limit: int = 15) -> dict:
    """Skill paling banyak dicari (R-05-07)."""
    raise NotImplementedError("Diisi pada PRD-05.")


def get_salary_stats(currency: str | None = None, period: str | None = None) -> dict:
    """Statistik gaji faktual dengan aturan sampel minimal (R-05-08..R-05-10)."""
    raise NotImplementedError("Diisi pada PRD-05.")


def get_company(slug: str) -> dict:
    """Ringkasan perusahaan yang hanya diturunkan dari data ``jobs`` (R-05-16..R-05-18)."""
    raise NotImplementedError("Diisi pada PRD-05.")
