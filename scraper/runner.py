"""Satu-satunya orkestrator ingestion (PRD-02 §9).

Adapter tidak saling memanggil. ``runner.run`` membuat ``scrape_runs``, menjalankan
adapter yang diminta, lalu mencatat hasilnya. Kegagalan satu sumber tidak
menghentikan sumber lain (R-02-08). Diisi pada PRD-02.
"""

from __future__ import annotations


def run(source: str = "all", max_pages: int = 5, dry_run: bool = False) -> int:
    """Jalankan ingestion; kembalikan kode keluar (0 sukses sebagian, 1 semua gagal)."""
    raise NotImplementedError("Diisi pada PRD-02 (orkestrasi ingestion).")
