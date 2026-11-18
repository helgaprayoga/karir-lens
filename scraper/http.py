"""Lapisan HTTP bersama: session, user agent, timeout, backoff, robots.txt.

Menyatukan perilaku sopan yang wajib dipakai ketiga adapter (R-02-03..R-02-05)
agar tidak diduplikasi per sumber. Diisi pada PRD-02.
"""

from __future__ import annotations

from core.config import Settings

STOP_STATUS_CODES = frozenset({403, 429})


class ScraperHTTP:
    """Klien HTTP dengan retry, backoff eksponensial, dan pemeriksaan robots.txt."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_allowed(self, url: str) -> bool:
        """True bila robots.txt mengizinkan pengambilan ``url``."""
        raise NotImplementedError("Diisi pada PRD-02 (robots.txt).")

    def get(self, url: str, params: dict | None = None) -> str:
        """Ambil isi halaman dengan retry dan backoff."""
        raise NotImplementedError("Diisi pada PRD-02 (GET dengan retry).")
