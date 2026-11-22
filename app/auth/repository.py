"""Akses data tabel ``users`` (PRD-01).

Hanya berkas ini yang boleh menyentuh client Supabase untuk modul auth
(docs/ARCHITECTURE.md §4 aturan 3). Semua query memakai parameter terikat.
"""

from __future__ import annotations

from core import db
from core.errors import ValidationError

TABLE = "users"

PUBLIC_COLUMNS = "id,email,name,created_at"
AUTH_COLUMNS = "id,email,name,password_hash,created_at"


def find_by_email(email: str, *, with_password: bool = False) -> dict | None:
    """Cari pengguna berdasarkan email (unik)."""
    columns = AUTH_COLUMNS if with_password else PUBLIC_COLUMNS
    response = (
        db.get_db()
        .table(TABLE)
        .select(columns)
        .eq("email", email)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def find_by_id(user_id: int) -> dict | None:
    response = (
        db.get_db()
        .table(TABLE)
        .select(PUBLIC_COLUMNS)
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def update_name(user_id: int, name: str | None) -> dict | None:
    """Perbarui nama tampilan pengguna (PRD-06 R-06-02).

    Email sengaja tidak dapat diubah: ia identitas login, dan menggantinya
    memerlukan verifikasi kepemilikan alamat yang belum ada di aplikasi ini.
    Mengembalikan baris terbaru, atau ``None`` bila pengguna tidak ada.
    """
    from datetime import datetime, timezone

    (
        db.get_db()
        .table(TABLE)
        .update(
            {
                "name": name,
                # Waktu dihitung di sini, bukan `"now()"`: PostgREST memakai
                # parameter terikat, dan string "now()" akan tersimpan sebagai
                # teks, bukan dipanggil sebagai fungsi SQL.
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", user_id)
        .execute()
    )
    return find_by_id(user_id)


def create(email: str, password_hash: str, name: str | None = None) -> dict:
    """Simpan pengguna baru dan kembalikan kolom publik.

    Pelanggaran constraint unik ``users.email`` diterjemahkan menjadi
    ``ValidationError`` agar race condition tetap menghasilkan pesan yang jelas,
    bukan 502 dari lapisan data.
    """
    try:
        response = (
            db.get_db()
            .table(TABLE)
            .insert({"email": email, "password_hash": password_hash, "name": name})
            .execute()
        )
    except Exception as error:  # noqa: BLE001 - pesan driver berbeda-beda antar versi
        message = str(error).lower()
        if "duplicate" in message or "unique" in message:
            raise ValidationError("Email sudah terdaftar.", code="EMAIL_TAKEN") from error
        raise

    rows = response.data or []
    if not rows:
        raise ValidationError("Pendaftaran gagal disimpan.", code="REGISTRATION_FAILED")

    return {key: rows[0].get(key) for key in ("id", "email", "name")}
