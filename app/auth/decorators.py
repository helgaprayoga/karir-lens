"""Pembatas akses berbasis peran (PRD-09 R-09-01).

Ditempatkan di modul ``auth`` karena peran adalah milik pengguna, bukan milik
panel admin: ``app/api`` juga memakainya untuk endpoint yang butuh sesi.

Mengembalikan 403 untuk pengguna login yang bukan admin, dan 401 untuk tamu.
Keduanya lewat ``AppError``, sehingga handler global yang memilih tampilan HTML
atau JSON — route tidak perlu tahu bedanya (R-09-13).
"""

from __future__ import annotations

from functools import wraps

from flask_login import current_user

from core.errors import ForbiddenError


def admin_required(view):
    """Izinkan hanya pengguna dengan ``role == 'admin'`` (R-09-01).

    Dipakai bersama ``@login_required``: tamu sudah dialihkan ke halaman login
    oleh dekorator itu (perilaku yang benar untuk halaman HTML), sehingga di
    sini hanya peran yang perlu diperiksa. Pengguna login yang bukan admin
    mendapat 403 lewat ``AppError``.
    """

    @wraps(view)
    def terbungkus(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            raise ForbiddenError("Halaman ini hanya untuk admin.")
        return view(*args, **kwargs)

    return terbungkus
