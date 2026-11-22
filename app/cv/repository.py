"""Akses data yang dibutuhkan alur CV (PRD-07).

Membaca ``user_skills`` dan kandidat lowongan. Modul lain dipanggil lewat
``service``, bukan lewat repository mereka (docs/ARCHITECTURE.md §4 aturan 2).
"""

from __future__ import annotations

from core import db as core_db

USER_SKILLS = "user_skills"
JOBS = "jobs"
SAVED_JOBS = "saved_jobs"


def _client():
    return core_db.get_db()


def find_confirmed_skills(user_id: int) -> list[dict]:
    """Skill terkonfirmasi pengguna (R-07-09).

    Hanya ``is_confirmed = true``: rekomendasi yang dihitung dari skill yang
    belum disetujui pengguna akan terasa seperti tebakan.
    """
    baris = (
        _client()
        .table(USER_SKILLS)
        .select("id,skill,source,is_confirmed")
        .eq("user_id", user_id)
        .eq("is_confirmed", True)
        .execute()
        .data
        or []
    )
    return [
        {
            "id": r["id"],
            "skill": r.get("skill"),
            "source": r.get("source"),
            "is_confirmed": True,
        }
        for r in baris
    ]


def find_candidate_jobs(limit: int = 200) -> list[dict]:
    """Lowongan kandidat untuk dihitung skornya.

    Hanya kolom yang dipakai penilaian: menarik ``description`` untuk ratusan
    baris hanya untuk membandingkan skill berarti memindahkan ratusan kilobyte
    tanpa guna.
    """
    return (
        _client()
        .table(JOBS)
        .select("id,title,company_name,company_slug,location,employment_type,"
                "description,skills,skills_source,salary_min,salary_max,"
                "salary_currency,salary_period,source_id,source_url,posted_at,cluster_id")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def find_saved_job_ids(user_id: int) -> set[int]:
    """Lowongan yang sudah di-bookmark pengguna (R-07-14)."""
    baris = (
        _client()
        .table(SAVED_JOBS)
        .select("job_id")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    return {r["job_id"] for r in baris if r.get("job_id") is not None}


def find_sources() -> list[dict]:
    """``source_id`` -> nama sumber, untuk kolom ``source`` pada kartu."""
    return _client().table("sources").select("id,name").execute().data or []
