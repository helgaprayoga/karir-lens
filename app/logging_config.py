"""Penyaring log agar data sensitif tidak pernah tertulis (R-01-13, PRD §9.3).

Password, token CSRF, API key, dan isi CV tidak boleh masuk log. Filter bekerja
sebagai jaring pengaman terakhir: kode tetap tidak boleh sengaja mencatat nilai
tersebut.
"""

from __future__ import annotations

import logging
import re

REDACTED = "[disembunyikan]"

# ``password=...``, ``token: ...``, ``api_key=...`` dan sejenisnya.
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|token|csrf_token|secret|api[_-]?key|authorization)"
    r"(\s*[=:]\s*)([^\s,;&\"'}]+)"
)

_BEARER_PATTERN = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._\-]+")


class SensitiveDataFilter(logging.Filter):
    """Hapus nilai sensitif dari pesan log sebelum ditulis.

    Pesan dirender lebih dulu (``getMessage``) baru disaring. Menyaring templat
    mentah tidak cukup: pada ``"password=%s"`` dengan argumen password asli,
    yang tersaring justru placeholder-nya dan nilai asli lolos.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:  # noqa: BLE001 - format string rusak tidak boleh mematikan logging
            return True

        record.msg = redact(rendered)
        record.args = ()
        return True


def redact(value: str) -> str:
    """Kembalikan teks dengan nilai sensitif diganti penanda."""
    # ``Authorization: Bearer <token>`` disaring lebih dulu; pola umum di bawah
    # hanya akan menangkap kata "Bearer" dan meninggalkan tokennya.
    redacted = _BEARER_PATTERN.sub(lambda match: f"{match.group(1)}{REDACTED}", value)
    return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", redacted)


def configure_logging(level: int = logging.INFO) -> None:
    """Pasang handler dasar dengan penyaring data sensitif.

    Idempoten: dipanggil berkali-kali (mis. pada setiap ``create_app`` dalam
    test) tidak menumpuk handler.
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        if getattr(handler, "_karirlens", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(SensitiveDataFilter())
    handler._karirlens = True  # type: ignore[attr-defined]
    root.addHandler(handler)
