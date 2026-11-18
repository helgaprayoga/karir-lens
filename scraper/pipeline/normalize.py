"""Normalisasi field lowongan (PRD-03).

Memakai ``core/text.py`` dan ``core/skills.py`` agar aturan yang sama berlaku
untuk skill lowongan dan skill CV (R-07-04). Diisi pada PRD-03.
"""

from __future__ import annotations


def normalize(raw_job) -> dict:
    """``RawJob`` -> dict siap disimpan dengan format seragam."""
    raise NotImplementedError("Diisi pada PRD-03 (normalisasi field).")
