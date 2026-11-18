"""Kamus skill dan pencocokan berbasis aturan.

PRD-03 memakai ``preprocess``/``match_skills`` untuk menormalkan skill lowongan;
PRD-07 memakai fungsi yang sama untuk skill dari CV (R-07-04). AI hanya menjadi
fallback untuk skill ambigu, sehingga pencocokan utama tetap deterministik.
Diisi pada PRD-03 dan PRD-07.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DICTIONARY_PATH = Path(__file__).parent / "data" / "skills.json"
AMBIGUITY_THRESHOLD = 0.6


@lru_cache(maxsize=1)
def load_dictionary() -> dict[str, object]:
    """Muat dan validasi kamus skill sekali per proses."""
    with DICTIONARY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not data.get("skills"):
        raise ValueError("Kamus skill tidak valid: field 'skills' wajib ada.")
    return data


def canonical_skills() -> list[str]:
    """Daftar skill baku yang dikenal kamus."""
    return list(load_dictionary()["skills"])


def preprocess(text: str | None) -> list[str]:
    """Token teks yang sudah dinormalkan memakai aturan PRD-03."""
    raise NotImplementedError("Diisi pada PRD-03 (normalisasi skill).")


def match_skills(text: str | None) -> list[str]:
    """Skill baku yang ditemukan pada teks."""
    raise NotImplementedError("Diisi pada PRD-03/PRD-07 (pencocokan kamus).")


def is_ambiguous(candidate: str) -> bool:
    """True bila kandidat skill terlalu lemah dan layak dikirim ke AI fallback."""
    raise NotImplementedError("Diisi pada PRD-07 (penanda skill ambigu).")
