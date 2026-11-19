"""Navigasi header yang hanya menampilkan tautan yang sudah terdaftar.

PRD-01 baru mengisi ``main`` dan ``auth``; blueprint lain menyusul pada PRD-04
sampai PRD-09. Memanggil ``url_for`` untuk endpoint yang belum ada akan
melempar ``BuildError``, jadi daftar tautan disaring terhadap
``app.view_functions``.
"""

from __future__ import annotations

from flask import current_app

PUBLIC_LINKS = (
    ("main.index", "Beranda"),
    ("jobs.index", "Lowongan"),
    ("insights.index", "Insight"),
)

USER_LINKS = (
    ("profile.index", "Profil"),
    ("profile.saved", "Tersimpan"),
    ("cv.index", "CV"),
    ("assistant.index", "Asisten"),
)

ADMIN_LINKS = (("admin.index", "Admin"),)


def _available(links) -> list[dict[str, str]]:
    endpoints = current_app.view_functions
    return [{"endpoint": endpoint, "label": label} for endpoint, label in links if endpoint in endpoints]


def nav_links() -> list[dict[str, str]]:
    """Tautan navigasi sesuai peran; admin melihat tautan tambahan (R-06-10)."""
    links = _available(PUBLIC_LINKS)

    from flask_login import current_user

    if current_user.is_authenticated:
        links.extend(_available(USER_LINKS))
        if getattr(current_user, "is_admin", False):
            links.extend(_available(ADMIN_LINKS))

    return links
