"""Aturan bisnis autentikasi (PRD-01).

Tempat tinggal: validasi email, panjang password, keunikan email, serta hashing
memakai ``werkzeug.security``. Tidak boleh mengimpor ``flask``.
"""

from __future__ import annotations

MIN_PASSWORD_LENGTH = 8


def register(email: str, password: str, name: str | None = None) -> dict:
    """Buat pengguna baru dengan password ter-hash dan email unik (R-01-09)."""
    raise NotImplementedError("Diisi pada PRD-01 (registrasi).")


def authenticate(email: str, password: str) -> dict | None:
    """Kembalikan data pengguna bila kredensial valid, ``None`` bila tidak."""
    raise NotImplementedError("Diisi pada PRD-01 (login).")
