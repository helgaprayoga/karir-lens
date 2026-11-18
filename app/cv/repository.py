"""Akses data yang dibutuhkan alur CV (PRD-07).

Membaca ``user_skills`` dan kandidat lowongan. Modul lain dipanggil lewat
``service``, bukan lewat repository mereka (docs/ARCHITECTURE.md §4 aturan 2).
"""

from __future__ import annotations


def find_confirmed_skills(user_id: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-07.")


def find_candidate_jobs(limit: int = 200) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-07.")
