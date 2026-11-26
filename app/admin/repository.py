"""Akses data panel admin (PRD-09).

Membaca tabel ``jobs``, ``users``, ``scrape_runs``, dan ``clusters`` untuk
keperluan pemantauan. Tidak ada kolom atau tabel CV yang disentuh (R-09-09):
``user_skills`` hanya dihitung jumlahnya, isinya tidak pernah diambil.
"""

from __future__ import annotations

from core import db as core_db

JOBS = "jobs"
USERS = "users"
RUNS = "scrape_runs"
CLUSTERS = "clusters"
SOURCES = "sources"
SAVED = "saved_jobs"
USER_SKILLS = "user_skills"

JOB_COLUMNS = "id,title,company_name,location,posted_at,source_id"
RUN_COLUMNS = (
    "id,source_id,started_at,finished_at,status,"
    "jobs_found,jobs_inserted,jobs_updated,error_message"
)


def _client():
    return core_db.get_db()


def _count(table: str, query: str | None = None) -> int:
    """Jumlah baris; memakai ``count="exact"`` agar tidak menarik seluruh tabel."""
    q = _client().table(table).select("id", count="exact")
    if query:
        q = q.or_(query)
    hasil = q.execute()
    jumlah = getattr(hasil, "count", None)
    if jumlah is not None:
        return jumlah
    return len(hasil.data or [])


def count_jobs() -> int:
    return _count(JOBS)


def count_users() -> int:
    return _count(USERS)


def count_clusters() -> int:
    return _count(CLUSTERS)


def count_runs() -> int:
    return _count(RUNS)


def _source_names() -> dict[int, str]:
    baris = _client().table(SOURCES).select("id,name").execute().data or []
    return {row["id"]: row["name"] for row in baris}


def find_recent_runs(limit: int = 10) -> list[dict]:
    """Riwayat pembaruan, terbaru lebih dulu (R-09-06)."""
    baris = (
        _client()
        .table(RUNS)
        .select(RUN_COLUMNS)
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    sumber = _source_names()
    return [{**row, "source": sumber.get(row.get("source_id"))} for row in baris]


def _search_clause(query: str | None) -> str | None:
    """Klausa pencarian judul/perusahaan, atau ``None`` bila tidak ada kata kunci.

    Karakter yang punya arti bagi PostgREST dibuang, sama seperti
    ``app/jobs/repository.sanitize_term`` — filternya disusun di sini, jadi
    nilainya tidak boleh mengubah struktur ekspresi (R-09-18).
    """
    bersih = " ".join(
        "".join(c if c.isalnum() or c.isspace() else " " for c in str(query or "")).split()
    )
    if not bersih:
        return None
    return f"title.ilike.%{bersih}%,company_name.ilike.%{bersih}%"


def count_jobs_matching(query: str | None) -> int:
    return _count(JOBS, _search_clause(query))


def find_jobs_page(query: str | None, offset: int, limit: int) -> list[dict]:
    """Sebagian lowongan untuk tabel admin (R-09-03)."""
    q = _client().table(JOBS).select(JOB_COLUMNS)
    klausa = _search_clause(query)
    if klausa:
        q = q.or_(klausa)

    baris = (
        q.order("posted_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
        .data
        or []
    )
    sumber = _source_names()
    return [{**row, "source": sumber.get(row.get("source_id"))} for row in baris]


def skill_counts() -> dict[int, int]:
    """``user_id`` -> jumlah skill terkonfirmasi (kolom "Skill" di admin).

    Hanya ``user_id`` yang diambil: nama skill pun tidak dibutuhkan untuk
    menghitung, dan panel admin memang tidak boleh menampilkannya (R-09-09).
    """
    baris = (
        _client()
        .table(USER_SKILLS)
        .select("user_id")
        .eq("is_confirmed", True)
        .execute()
        .data
        or []
    )
    hitung: dict[int, int] = {}
    for row in baris:
        uid = row.get("user_id")
        if uid is not None:
            hitung[uid] = hitung.get(uid, 0) + 1
    return hitung


def find_users_page(offset: int, limit: int) -> list[dict]:
    """Sebagian pengguna tanpa password maupun data CV (R-09-05)."""
    baris = (
        _client()
        .table(USERS)
        .select("id,email,name,role,created_at")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
        .data
        or []
    )
    hitung = skill_counts()
    return [{**row, "skill_count": hitung.get(row.get("id"), 0)} for row in baris]


def find_clusters() -> list[dict]:
    """Cluster hasil clustering untuk ditinjau (R-09-07)."""
    return (
        _client()
        .table(CLUSTERS)
        .select("id,label,keywords,job_count")
        .order("job_count", desc=True)
        .execute()
        .data
        or []
    )


def delete_job(job_id: int) -> None:
    """Hapus satu lowongan beserta bookmark yang menunjuknya.

    ``saved_jobs.job_id`` mereferensikan ``jobs.id`` tanpa ON DELETE CASCADE,
    jadi baris bookmark harus dilepas lebih dulu — kalau tidak, penghapusan
    ditolak foreign key dan admin melihat 500.
    """
    _client().table(SAVED).delete().eq("job_id", job_id).execute()
    _client().table(JOBS).delete().eq("id", job_id).execute()


def job_exists(job_id: int) -> bool:
    hasil = (
        _client().table(JOBS).select("id").eq("id", job_id).limit(1).execute()
    )
    return bool(hasil.data)
