"""Satu sumber kebenaran untuk pagination (R-04-04, R-09-12).

Dipakai bersama oleh halaman web (``app/jobs``, ``app/admin``) dan endpoint JSON
(``app/api``), sehingga metadata halaman tidak pernah berbeda antar presenter.
"""

from __future__ import annotations

from typing import Mapping

DEFAULT_PER_PAGE = 12
MAX_PER_PAGE = 50


def _as_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def parse_page(
    args: Mapping[str, object] | None = None,
    *,
    default_per_page: int = DEFAULT_PER_PAGE,
) -> tuple[int, int, int]:
    """Kembalikan ``(page, per_page, offset)`` yang sudah divalidasi.

    Nilai non-numerik atau di luar rentang dijatuhkan ke default, bukan
    menghasilkan error, mengikuti pola validasi query string defensif pada PRD-04.
    """
    args = args or {}
    page = max(1, _as_int(args.get("page"), 1))
    per_page = _as_int(args.get("per_page"), default_per_page)
    per_page = min(max(1, per_page), MAX_PER_PAGE)
    return page, per_page, (page - 1) * per_page


def build_meta(page: int, per_page: int, total: int) -> dict[str, object]:
    """Metadata pagination dengan bentuk yang sama untuk HTML dan JSON."""
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_next": page * per_page < total,
    }
