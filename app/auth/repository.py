"""Akses data tabel ``users`` (PRD-01).

Hanya berkas ini yang boleh menyentuh client Supabase untuk modul auth.
"""

from __future__ import annotations

TABLE = "users"


def find_by_email(email: str) -> dict | None:
    raise NotImplementedError("Diisi pada PRD-01.")


def create(email: str, password_hash: str, name: str | None = None) -> dict:
    raise NotImplementedError("Diisi pada PRD-01.")
