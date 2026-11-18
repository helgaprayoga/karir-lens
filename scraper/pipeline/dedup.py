"""Deduplikasi lintas sumber (PRD-03).

Menghasilkan ``dedup_hash`` dari judul dan perusahaan yang sudah dinormalkan,
serta menandai lowongan yang sama dari sumber berbeda. Diisi pada PRD-03.
"""

from __future__ import annotations


def compute_hash(job: dict) -> str:
    """Hash stabil untuk mendeteksi duplikat lintas sumber."""
    raise NotImplementedError("Diisi pada PRD-03 (dedup_hash).")
