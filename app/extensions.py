"""Ekstensi Flask yang dipakai lintas blueprint (R-01-11, R-01-10).

Objek dibuat di sini lalu diikat ke aplikasi pada ``create_app`` agar test dapat
memakai konfigurasi terpisah.
"""

from __future__ import annotations

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan masuk terlebih dahulu."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    """Muat pengguna dari tabel ``users`` (implementasi pada PRD-06)."""
    raise NotImplementedError("Diisi pada PRD-06 (user_loader dari tabel users).")
