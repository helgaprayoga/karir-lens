"""Aturan bisnis profil (PRD-06).

Tempat tinggal: hanya skill ``is_confirmed = true`` yang dipakai fitur lain, dan
bookmark unik per pengguna dan lowongan (R-06).
"""

from __future__ import annotations


def list_confirmed_skills(user_id: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-06.")


def confirm_skills(user_id: int, skills: list[str], source: str = "cv") -> list[dict]:
    """Simpan hanya skill yang dikonfirmasi pengguna (R-07-07)."""
    raise NotImplementedError("Diisi pada PRD-06.")


def save_job(user_id: int, job_id: int) -> dict:
    """Simpan lowongan sebagai bookmark; duplikat tidak menambah baris (R-06)."""
    raise NotImplementedError("Diisi pada PRD-06.")


def remove_saved_job(user_id: int, job_id: int) -> None:
    raise NotImplementedError("Diisi pada PRD-06.")


def list_saved_jobs(user_id: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-06.")
