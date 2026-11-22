"""Aturan bisnis profil dan bookmark (PRD-06).

Tempat tinggal: hanya skill ``is_confirmed = true`` yang dipakai fitur lain, dan
bookmark unik per pengguna dan lowongan (R-06).

``service`` tidak mengenal Flask (docs/ARCHITECTURE.md §4 aturan 2), sehingga
dapat dipakai ulang oleh ``app/api`` pada PRD-09 dan diuji tanpa request.
"""

from __future__ import annotations

from core.errors import NotFoundError, ValidationError
from core.pagination import build_meta, parse_page

from . import repository

MAX_NAME_LENGTH = 80


def _shape_job(row: dict, sumber: dict[int, str], disimpan: set[int]) -> dict:
    """Baris database -> bentuk ``job`` kontrak PRD-F02 §4.1.

    ``is_saved`` diisi dari himpunan id yang disimpan: di halaman tersimpan
    semuanya tentu ``True``, tetapi bentuknya harus sama dengan kartu di
    katalog agar partial `job_card` tidak perlu tahu asalnya.
    """
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "company_name": row.get("company_name"),
        "company_slug": row.get("company_slug"),
        "location": row.get("location"),
        "employment_type": row.get("employment_type"),
        "experience_level": None,
        "description": row.get("description"),
        "skills": row.get("skills") or [],
        "skills_source": row.get("skills_source"),
        "salary_min": row.get("salary_min"),
        "salary_max": row.get("salary_max"),
        "salary_currency": row.get("salary_currency"),
        "salary_period": row.get("salary_period"),
        "source": sumber.get(row.get("source_id")),
        "source_url": row.get("source_url"),
        "posted_at": row.get("posted_at"),
        "is_saved": row.get("id") in disimpan,
        "match": None,
    }


# --- skill -----------------------------------------------------------------

def list_confirmed_skills(user_id: int) -> list[dict]:
    """Skill yang sudah dikonfirmasi pengguna (R-06-12).

    Hanya yang ``is_confirmed``: skill yang belum dikonfirmasi belum menjadi
    pernyataan pengguna, jadi tidak boleh dipakai menghitung rekomendasi
    maupun ditampilkan sebagai skill miliknya.
    """
    return repository.find_skills(user_id, only_confirmed=True)


def confirm_skills(user_id: int, skills: list[str], source: str = "cv") -> list[dict]:
    """Simpan hanya skill yang dikonfirmasi pengguna (R-07-07).

    Milik PRD-07, tetapi tinggal di sini karena tabelnya sama. Belum dipanggil
    dari mana pun pada PRD-06 — R-06-12 menegaskan bahwa task ini **membaca**
    skill, tidak mengubahnya.
    """
    bersih = [
        {"skill": str(s).strip().lower(), "source": source, "is_confirmed": True}
        for s in (skills or [])
        if str(s).strip()
    ]
    return repository.upsert_skills(user_id, bersih)


def remove_skill(user_id: int, skill_id: int) -> None:
    """Hapus satu skill milik pengguna ini."""
    repository.delete_skill(user_id, skill_id)


# --- profil ----------------------------------------------------------------

def get_profile(user_id: int) -> dict:
    """Profil, skill, dan ringkasan sesuai kontrak PRD-F03 §4.1 (R-06-01).

    ``summary`` hanya memuat angka yang punya tabel sumber: jumlah skill
    terkonfirmasi dan jumlah bookmark. Tidak ada "kelengkapan profil" — itu
    angka karangan yang tidak dimiliki data.
    """
    baris = repository.find_user(user_id)
    if baris is None:
        raise NotFoundError("Pengguna tidak ditemukan.")

    skills = list_confirmed_skills(user_id)

    return {
        "profile": {
            "name": baris.get("name"),
            "email": baris.get("email"),
            # Template membaca `joined_at` (PRD-F03 §4.1 menyebut `created_at`,
            # tetapi partial yang sudah ada memakai nama ini). Keduanya diisi
            # agar kontrak dan template sama-sama terpenuhi tanpa mengubah
            # template.
            "created_at": baris.get("created_at"),
            "joined_at": baris.get("created_at"),
        },
        "skills": skills,
        "summary": {
            "skill_count": len(skills),
            "saved_count": repository.count_saved(user_id),
        },
    }


def update_name(user_id: int, name: str | None) -> dict:
    """Ubah nama tampilan (R-06-02). Email tetap pada task ini."""
    bersih = " ".join((name or "").split())
    if not bersih:
        raise ValidationError("Nama tidak boleh kosong.")
    if len(bersih) > MAX_NAME_LENGTH:
        raise ValidationError(f"Nama maksimal {MAX_NAME_LENGTH} karakter.")

    if repository.simpan_nama(user_id, bersih) is None:
        raise NotFoundError("Pengguna tidak ditemukan.")

    return get_profile(user_id)


# --- bookmark --------------------------------------------------------------

def save_job(user_id: int, job_id: int) -> dict:
    """Simpan lowongan sebagai bookmark (R-06-03, R-06-05, R-06-11).

    Lowongan yang tidak ada menghasilkan ``NotFoundError`` — bukan 500, dan
    bukan bookmark yang menunjuk baris hantu.

    Kembalian memuat ``created`` agar route dapat membedakan pesan "disimpan"
    dari "sudah tersimpan" tanpa menebak dari jumlah baris.
    """
    if repository.find_job(job_id) is None:
        raise NotFoundError("Lowongan tidak ditemukan.")

    created = repository.insert_saved_job(user_id, job_id)
    return {"job_id": job_id, "created": created}


def remove_saved_job(user_id: int, job_id: int) -> None:
    """Hapus bookmark milik pengguna ini saja (R-06-04)."""
    repository.delete_saved_job(user_id, job_id)


def list_saved_jobs(
    user_id: int,
    page: str | int | None = None,
    per_page: str | int | None = None,
) -> dict:
    """Daftar bookmark dengan pagination (R-06-06, R-06-07).

    Urutannya **terbaru disimpan lebih dulu**, bukan tanggal terbit lowongan:
    halaman ini menjawab "apa yang baru saya tandai", dan yang baru ditandai
    adalah yang paling relevan bagi pengguna.

    Pagination dilakukan di sini, bukan di database, karena jumlah bookmark satu
    pengguna kecil dan urutannya berasal dari tabel ``saved_jobs`` sementara
    isi kartunya dari ``jobs`` — memotong di database akan memerlukan join yang
    tidak dimiliki PostgREST lewat client ini.
    """
    halaman, per_halaman, offset = parse_page({"page": page, "per_page": per_page})

    tersimpan = repository.find_saved_jobs(user_id)
    total = len(tersimpan)
    potong = tersimpan[offset : offset + per_halaman]

    ids = [row["job_id"] for row in potong]
    baris = {row["id"]: row for row in repository.find_jobs_by_ids(ids)}
    sumber = {row["id"]: row["name"] for row in repository.find_sources()}
    disimpan = {row["job_id"] for row in tersimpan}

    # Urutan mengikuti `tersimpan`, bukan urutan hasil query `jobs`.
    items = [
        _shape_job(baris[job_id], sumber, disimpan)
        for job_id in ids
        if job_id in baris
    ]

    return {
        "items": items,
        "meta": build_meta(halaman, per_halaman, total),
    }


def saved_ids(user_id: int) -> set[int]:
    """Himpunan ``job_id`` yang disimpan, untuk menandai tombol di katalog."""
    return repository.saved_job_ids(user_id)
