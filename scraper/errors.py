"""Error domain ingestion (PRD-02 §4).

Dipisah dari ``core/errors.py`` karena ``AppError`` dipetakan ke respons HTTP,
sedangkan kegagalan scraping tidak pernah dilihat pengguna web — ia berakhir di
kolom ``scrape_runs.error_message`` dan log.
"""

from __future__ import annotations


class ScrapeError(Exception):
    """Kegagalan umum saat mengambil atau mengurai satu sumber."""


class RobotsDisallowedError(ScrapeError):
    """``robots.txt`` melarang pengambilan jalur yang diminta (R-02-05)."""


class ScrapeBlockedError(ScrapeError):
    """Server menolak akses (403/429); sumber ini harus dihentikan (R-02-03)."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
