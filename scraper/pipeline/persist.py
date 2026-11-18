"""Penyimpanan idempoten ke tabel ``jobs`` (PRD-03).

Satu-satunya berkas di ``scraper/`` yang boleh memakai ``core/db.py``.
Diisi pada PRD-03.
"""

from __future__ import annotations

TABLE = "jobs"


def insert_or_update(job: dict) -> str:
    """Simpan lowongan; kembalikan ``"inserted"`` atau ``"updated"``."""
    raise NotImplementedError("Diisi pada PRD-03 (insert-or-update idempoten).")
