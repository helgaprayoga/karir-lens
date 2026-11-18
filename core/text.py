"""Normalisasi teks yang dipakai bersama pipeline data dan ekstraksi CV.

PRD-03 memakai modul ini untuk menormalkan field lowongan; PRD-07 wajib memakai
aturan yang sama untuk skill CV (R-07-04), sehingga implementasinya hanya satu.
Diisi pada PRD-03.
"""

from __future__ import annotations

import re
import unicodedata

_NON_WORD = re.compile(r"[^a-z0-9\s+#.]")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    """Huruf kecil, buang aksen dan tanda baca, rapikan spasi.

    ``+``, ``#``, dan ``.`` dipertahankan agar ``c++``, ``c#``, dan ``node.js``
    tidak rusak menjadi token yang salah.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower()
    cleaned = _NON_WORD.sub(" ", lowered)
    return _WHITESPACE.sub(" ", cleaned).strip()


def slugify(value: str | None) -> str:
    """Slug stabil untuk ``company_slug`` dan URL halaman perusahaan."""
    return normalize_text(value).replace(" ", "-").strip("-")


def tokenize(value: str | None) -> list[str]:
    """Token teks yang sudah dinormalkan."""
    normalized = normalize_text(value)
    return normalized.split() if normalized else []
