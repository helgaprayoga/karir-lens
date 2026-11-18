"""Shared kernel KarirLens.

Berisi kode yang dipakai lebih dari satu modul dan lebih dari satu entrypoint
(``app`` untuk web, ``scraper`` untuk pipeline data).

Modul di dalam paket ini tidak boleh mengimpor Flask maupun paket ``app`` /
``scraper``. Lihat docs/ARCHITECTURE.md §4 aturan 4.
"""
