"""Akses data tabel ``user_skills`` dan ``saved_jobs`` (PRD-06)."""

from __future__ import annotations

USER_SKILLS = "user_skills"
SAVED_JOBS = "saved_jobs"


def find_skills(user_id: int, only_confirmed: bool = False) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-06.")


def upsert_skills(user_id: int, skills: list[dict]) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-06.")


def delete_skill(user_id: int, skill_id: int) -> None:
    raise NotImplementedError("Diisi pada PRD-06.")


def insert_saved_job(user_id: int, job_id: int) -> dict:
    raise NotImplementedError("Diisi pada PRD-06.")


def delete_saved_job(user_id: int, job_id: int) -> None:
    raise NotImplementedError("Diisi pada PRD-06.")


def find_saved_jobs(user_id: int) -> list[dict]:
    raise NotImplementedError("Diisi pada PRD-06.")
