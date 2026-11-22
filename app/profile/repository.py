"""Akses data tabel ``user_skills`` dan ``saved_jobs`` (PRD-06).

Satu-satunya berkas di ``app/profile/`` yang boleh menyentuh Supabase.

Bookmark di KarirLens adalah **penanda**, bukan pencatatan lamaran. Tidak ada
kolom status, tahapan, atau tanggal melamar di sini — dan tidak akan ada
(PRD-06 §3.2).
"""

from __future__ import annotations

from core import db as core_db

USER_SKILLS = "user_skills"
SAVED_JOBS = "saved_jobs"
JOBS = "jobs"


def _client():
    return core_db.get_db()


# --- skill -----------------------------------------------------------------

def find_skills(user_id: int, only_confirmed: bool = False) -> list[dict]:
    """Skill milik satu pengguna.

    ``only_confirmed=True`` dipakai fitur yang menghitung rekomendasi: skill
    yang belum dikonfirmasi belum menjadi pernyataan pengguna, jadi tidak boleh
    ikut (R-06-12).
    """
    query = _client().table(USER_SKILLS).select("*").eq("user_id", user_id)
    if only_confirmed:
        query = query.eq("is_confirmed", True)
    baris = query.execute().data or []

    return [
        {
            "id": row["id"],
            "skill": row.get("skill"),
            "source": row.get("source"),
            "is_confirmed": bool(row.get("is_confirmed")),
            "created_at": row.get("created_at"),
        }
        for row in baris
    ]


def upsert_skills(user_id: int, skills: list[dict]) -> list[dict]:
    """Simpan skill yang dikonfirmasi; skill yang sama tidak digandakan.

    Dipakai PRD-07 saat konfirmasi dari CV. Keunikannya dijaga dengan membaca
    lebih dulu: ``user_skills`` tidak punya constraint unik pada
    ``(user_id, skill)`` di skema PRD-01, jadi menyerahkan pada database akan
    membiarkan duplikat.
    """
    if not skills:
        return []

    sudah = {s["skill"].lower() for s in find_skills(user_id)}
    baru = []
    for item in skills:
        nama = (item.get("skill") or "").strip().lower()
        if not nama or nama in sudah:
            continue
        sudah.add(nama)
        baru.append(
            {
                "user_id": user_id,
                "skill": nama,
                "source": item.get("source") or "manual",
                "is_confirmed": bool(item.get("is_confirmed", True)),
            }
        )

    if baru:
        _client().table(USER_SKILLS).insert(baru).execute()
    return find_skills(user_id)


def delete_skill(user_id: int, skill_id: int) -> None:
    """Hapus satu skill milik pengguna tersebut.

    ``user_id`` ikut disyaratkan, bukan hanya ``id``: tanpa itu, menebak id
    skill pengguna lain akan menghapus data orang (R-06-04).
    """
    (
        _client()
        .table(USER_SKILLS)
        .delete()
        .eq("id", skill_id)
        .eq("user_id", user_id)
        .execute()
    )


# --- bookmark --------------------------------------------------------------

def insert_saved_job(user_id: int, job_id: int) -> bool:
    """Simpan bookmark. ``True`` bila baris baru, ``False`` bila sudah ada.

    Memakai ``upsert`` dengan ``on_conflict`` pada pasangan unik
    ``(user_id, job_id)``: menyimpan dua kali tidak menambah baris (R-06-05),
    dan tidak ada balapan antara "cek dulu" dan "insert" yang bisa menghasilkan
    duplikat pada dua permintaan bersamaan.
    """
    ada = find_saved_job(user_id, job_id) is not None
    if ada:
        return False

    (
        _client()
        .table(SAVED_JOBS)
        .upsert(
            {"user_id": user_id, "job_id": job_id},
            on_conflict="user_id,job_id",
            ignore_duplicates=True,
        )
        .execute()
    )
    return True


def find_saved_job(user_id: int, job_id: int) -> dict | None:
    """Satu baris bookmark milik pengguna ini, atau ``None``."""
    hasil = (
        _client()
        .table(SAVED_JOBS)
        .select("user_id,job_id,created_at")
        .eq("user_id", user_id)
        .eq("job_id", job_id)
        .limit(1)
        .execute()
    )
    baris = hasil.data or []
    return baris[0] if baris else None


def delete_saved_job(user_id: int, job_id: int) -> None:
    """Hapus bookmark milik pengguna tersebut saja (R-06-04)."""
    (
        _client()
        .table(SAVED_JOBS)
        .delete()
        .eq("user_id", user_id)
        .eq("job_id", job_id)
        .execute()
    )


def find_saved_jobs(user_id: int) -> list[dict]:
    """Baris bookmark pengguna, terbaru lebih dulu, beserta id lowongannya."""
    baris = (
        _client()
        .table(SAVED_JOBS)
        .select("job_id,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    return baris


def find_jobs_by_ids(job_ids: list[int]) -> list[dict]:
    """Baris ``jobs`` untuk sekumpulan id, untuk halaman tersimpan."""
    if not job_ids:
        return []
    return (
        _client().table(JOBS).select("*").in_("id", list(job_ids)).execute().data or []
    )


def count_saved(user_id: int) -> int:
    """Jumlah bookmark pengguna, untuk ringkasan profil dan badge navigasi."""
    hasil = (
        _client()
        .table(SAVED_JOBS)
        .select("job_id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    jumlah = getattr(hasil, "count", None)
    return jumlah if jumlah is not None else len(hasil.data or [])


def saved_job_ids(user_id: int) -> set[int]:
    """Himpunan ``job_id`` yang disimpan pengguna ini.

    Dipakai katalog untuk menandai tombol simpan pada setiap kartu. Satu query
    untuk seluruh halaman, bukan satu per kartu.
    """
    baris = (
        _client()
        .table(SAVED_JOBS)
        .select("job_id")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    return {row["job_id"] for row in baris if row.get("job_id") is not None}


def find_user(user_id: int) -> dict | None:
    """Baris ``users`` milik pengguna ini, kolom publik saja.

    Dimiliki repository profil sendiri, bukan dipinjam dari
    ``app.auth.repository``: aturan arsitektur §4 butir 2 membatasi setiap
    service pada repository modulnya sendiri. ``password_hash`` tidak pernah
    diambil.
    """
    hasil = (
        _client()
        .table("users")
        .select("id,email,name,created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    baris = hasil.data or []
    return baris[0] if baris else None


def simpan_nama(user_id: int, name: str) -> dict | None:
    """Perbarui nama tampilan pengguna (R-06-02)."""
    from datetime import datetime, timezone

    (
        _client()
        .table("users")
        .update(
            {
                "name": name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", user_id)
        .execute()
    )
    return find_user(user_id)


def find_job(job_id: int) -> dict | None:
    """Satu baris ``jobs``, untuk memastikan bookmark menunjuk lowongan nyata.

    Dipakai ``service.save_job`` agar lowongan yang tidak ada menghasilkan
    ``NotFoundError``, bukan bookmark yang menunjuk baris hantu (R-06-11).
    """
    hasil = (
        _client().table(JOBS).select("id").eq("id", job_id).limit(1).execute()
    )
    baris = hasil.data or []
    return baris[0] if baris else None


def find_sources() -> list[dict]:
    """``source_id`` -> nama sumber, untuk kolom ``source`` pada kartu tersimpan."""
    return _client().table("sources").select("id,name").execute().data or []
