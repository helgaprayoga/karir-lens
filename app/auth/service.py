"""Aturan bisnis autentikasi (PRD-01).

Tempat tinggal: validasi email, panjang password, keunikan email, dan hashing
memakai ``werkzeug.security`` (R-01-09). Modul ini tidak mengimpor Flask
(docs/ARCHITECTURE.md §4 aturan 2), sehingga dapat diuji tanpa aplikasi.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from core.errors import ValidationError

from . import repository

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class User:
    """Representasi pengguna untuk Flask-Login.

    Hanya membawa kolom publik; ``password_hash`` tidak pernah menempel pada
    objek yang disimpan di sesi.
    """

    def __init__(self, row: dict) -> None:
        self.id = row["id"]
        self.email = row.get("email") or ""
        self.name = row.get("name")
        self.role = row.get("role") or "user"

    @property
    def is_admin(self) -> bool:
        """Peran admin ditambahkan pada PRD-09; sebelum itu selalu ``False``."""
        return self.role == "admin"

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    @property
    def display_name(self) -> str:
        return self.name or self.email


def normalize_email(email: str | None) -> str:
    """Rapikan email: trim dan lowercase.

    ``core.text.normalize_text`` sengaja tidak dipakai karena ia membuang
    karakter non-alfanumerik, termasuk ``@``.
    """
    return (email or "").strip().lower()


def validate_registration(email: str | None, password: str | None) -> tuple[str, str]:
    """Validasi input registrasi dan kembalikan ``(email, password)`` bersih."""
    clean_email = normalize_email(email)
    if not clean_email:
        raise ValidationError("Email wajib diisi.")
    if "@" not in clean_email or clean_email.startswith("@") or clean_email.endswith("@"):
        raise ValidationError("Format email tidak valid.")

    if not password:
        raise ValidationError("Password wajib diisi.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password minimal {MIN_PASSWORD_LENGTH} karakter.",
            code="PASSWORD_TOO_SHORT",
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError("Password terlalu panjang.", code="PASSWORD_TOO_LONG")

    return clean_email, password


def register(email: str | None, password: str | None, name: str | None = None) -> dict:
    """Buat pengguna baru dengan password ter-hash dan email unik (R-01-09)."""
    clean_email, clean_password = validate_registration(email, password)

    if repository.find_by_email(clean_email) is not None:
        raise ValidationError("Email sudah terdaftar.", code="EMAIL_TAKEN")

    password_hash = generate_password_hash(clean_password)
    clean_name = (name or "").strip() or None

    return repository.create(clean_email, password_hash, clean_name)


def authenticate(email: str | None, password: str | None) -> User | None:
    """Kembalikan pengguna bila kredensial valid, ``None`` bila tidak.

    Pesan gagal login sengaja seragam agar tidak membocorkan email mana yang
    terdaftar.
    """
    clean_email = normalize_email(email)
    if not clean_email or not password:
        return None

    row = repository.find_by_email(clean_email, with_password=True)
    if row is None:
        return None

    stored_hash = row.get("password_hash") or ""
    if not check_password_hash(stored_hash, password):
        return None

    return User(row)


def load_user(user_id: str | int) -> User | None:
    """``user_loader`` Flask-Login; ``None`` bila sesi menunjuk pengguna yang hilang."""
    try:
        numeric_id = int(user_id)
    except (TypeError, ValueError):
        return None

    row = repository.find_by_id(numeric_id)
    return User(row) if row else None
