"""Lapisan HTTP bersama: session, user agent, timeout, backoff, robots.txt.

Menyatukan perilaku sopan yang wajib dipakai ketiga adapter (R-02-03..R-02-05)
agar tidak diduplikasi per sumber.

Pola ini diadaptasi dari ``DeallsScraper`` pada proyek referensi
(``Praktik Scripting/Pertemuan 9/scraper.py``): ``load_robots()``,
``ensure_allowed()``, ``_polite_sleep()``, dan ``_backoff()`` dipindah ke satu
kelas dasar sehingga tiga adapter tidak menyalinnya.

Yang berbeda dari referensi: batas laju di sini **dapat dikonfigurasi per
sumber** (R-02-04) dan dinyatakan sebagai jarak minimum antar permintaan,
bukan rentang acak.
"""

from __future__ import annotations

import logging
import random
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from core.config import Settings

from .errors import RobotsDisallowedError, ScrapeBlockedError, ScrapeError

logger = logging.getLogger(__name__)

# Status yang berarti "berhenti, jangan coba lagi hari ini".
STOP_STATUS_CODES = frozenset({403, 429})

DEFAULT_TIMEOUT = 15
# R-02-04: tidak lebih dari satu permintaan per detik secara bawaan.
DEFAULT_MIN_INTERVAL = 1.0
MAX_BACKOFF_SECONDS = 30.0


class ScraperHTTP:
    """Klien HTTP dengan retry, backoff eksponensial, dan pemeriksaan robots.txt.

    Satu instance dipakai satu adapter, sehingga jeda dan cache robots.txt tidak
    saling memengaruhi antar sumber.
    """

    def __init__(
        self,
        settings: Settings,
        base_url: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        min_interval: float = DEFAULT_MIN_INTERVAL,
    ) -> None:
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_interval = max(0.0, min_interval)
        self._robots: RobotFileParser | None = None
        self._last_request_at = 0.0
        self._session = None

    # --- session ---------------------------------------------------------

    @property
    def user_agent(self) -> str:
        """User agent dari konfigurasi (R-02-03)."""
        return self.settings.scraper_user_agent

    @property
    def max_retry(self) -> int:
        """Jumlah percobaan total; minimal 1 agar tidak ada loop kosong."""
        return max(1, self.settings.scraper_max_retry)

    def session(self):
        """``requests.Session`` dengan header tetap, dibuat sekali."""
        if self._session is None:
            import requests

            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                }
            )
            self._session = session
        return self._session

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    # --- robots.txt ------------------------------------------------------

    def load_robots(self) -> RobotFileParser:
        """Baca dan urai ``robots.txt``.

        Bila berkasnya tidak dapat dibaca setelah seluruh percobaan, seluruh
        jalur dianggap diizinkan — sama seperti referensi. Keputusan ini dipilih
        agar kegagalan jaringan sementara tidak mematikan sumber selamanya;
        pemblokiran eksplisit (403/429) tetap dihormati.
        """
        robots_url = urljoin(self.base_url + "/", "robots.txt")
        terakhir: Exception | None = None

        for attempt in range(1, self.max_retry + 1):
            self._polite_sleep()
            try:
                response = self.session().get(robots_url, timeout=self.timeout)
                self._last_request_at = time.monotonic()
            except Exception as exc:  # requests.RequestException dan turunannya
                terakhir = exc
                logger.warning(
                    "Gagal membaca robots.txt (percobaan %d/%d): %s", attempt, self.max_retry, exc
                )
                self._backoff(attempt)
                continue

            if response.status_code == 200:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                self._robots = parser
                return parser

            if response.status_code in STOP_STATUS_CODES:
                raise ScrapeBlockedError(
                    f"robots.txt menolak akses dengan status {response.status_code}.",
                    response.status_code,
                )

            terakhir = ScrapeError(f"robots.txt mengembalikan status {response.status_code}.")
            self._backoff(attempt)

        logger.warning(
            "robots.txt tidak dapat dibaca (%s); menganggap semua jalur diizinkan.", terakhir
        )
        parser = RobotFileParser()
        parser.parse([])
        self._robots = parser
        return parser

    def is_allowed(self, url: str) -> bool:
        """True bila ``robots.txt`` mengizinkan pengambilan ``url`` (R-02-05)."""
        if self._robots is None:
            self.load_robots()
        assert self._robots is not None
        return self._robots.can_fetch(self.user_agent, url)

    def ensure_allowed(self, url: str) -> None:
        """Lempar ``RobotsDisallowedError`` bila jalur dilarang."""
        if not self.is_allowed(url):
            raise RobotsDisallowedError(
                f"robots.txt {urlsplit(self.base_url).netloc} melarang pengambilan {url}."
            )

    # --- jeda dan retry --------------------------------------------------

    def _polite_sleep(self) -> None:
        """Jaga jarak minimum antar permintaan ke host yang sama (R-02-04)."""
        if self._last_request_at == 0.0 or self.min_interval <= 0:
            return
        sisa = self.min_interval - (time.monotonic() - self._last_request_at)
        if sisa > 0:
            time.sleep(sisa)

    def _backoff(self, attempt: int) -> None:
        """Tunggu eksponensial dengan sedikit keacakan (R-02-03).

        Nilai dibatasi ``MAX_BACKOFF_SECONDS`` agar percobaan ketiga tidak
        menunggu delapan detik lebih di dalam test maupun di Actions.
        """
        delay = min(2.0**attempt + random.uniform(0, 0.5), MAX_BACKOFF_SECONDS)
        logger.debug("Menunggu %.1f detik sebelum mencoba lagi.", delay)
        time.sleep(delay)

    # --- GET -------------------------------------------------------------

    def get(self, url: str, params: dict | None = None) -> str:
        """Ambil isi halaman dengan retry dan backoff (R-02-03)."""
        self.ensure_allowed(url)

        terakhir: Exception | None = None
        for attempt in range(1, self.max_retry + 1):
            self._polite_sleep()
            try:
                response = self.session().get(url, params=params, timeout=self.timeout)
                self._last_request_at = time.monotonic()
            except Exception as exc:  # requests.RequestException
                terakhir = exc
                logger.warning(
                    "Permintaan gagal (percobaan %d/%d) %s: %s", attempt, self.max_retry, url, exc
                )
                self._backoff(attempt)
                continue

            if response.status_code in STOP_STATUS_CODES:
                raise ScrapeBlockedError(
                    f"Server mengembalikan status {response.status_code} untuk {url}.",
                    response.status_code,
                )
            if response.status_code == 404:
                raise ScrapeError(f"Halaman tidak ditemukan: {url}")
            if response.status_code >= 500:
                terakhir = ScrapeError(f"Server error {response.status_code} untuk {url}")
                self._backoff(attempt)
                continue
            if response.status_code != 200:
                raise ScrapeError(f"Status tak terduga {response.status_code} untuk {url}")

            response.encoding = response.encoding or "utf-8"
            return response.text

        raise ScrapeError(
            f"Gagal mengambil {url} setelah {self.max_retry} percobaan: {terakhir}"
        )

    def get_json(self, url: str, params: dict | None = None):
        """Ambil dan urai JSON. Dipakai sumber yang menyediakan API."""
        import json

        teks = self.get(url, params=params)
        try:
            return json.loads(teks)
        except ValueError as exc:
            raise ScrapeError(f"Respons {url} bukan JSON yang valid: {exc}") from exc
