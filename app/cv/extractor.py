"""Ekstraksi teks CV secara lokal memakai ``pypdf`` dan ``python-docx`` (PRD-07).

Tidak boleh menulis isi CV ke log (R-07-08).
"""

from __future__ import annotations


def extract_text(path: str, content_type: str) -> str:
    """Teks dari berkas PDF atau DOCX; gagal ekstraksi menghasilkan pesan ramah."""
    raise NotImplementedError("Diisi pada PRD-07.")
