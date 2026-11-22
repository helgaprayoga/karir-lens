"""Aturan bisnis insight (PRD-05).

PRD-04 hanya mengisi bagian perusahaan (R-04-07). Sisanya diisi PRD-05.
"""

from __future__ import annotations

from collections import Counter

from core.errors import NotFoundError

from . import repository


def _shape_job(row: dict, source: str | None = None) -> dict:
    """Baris database -> bentuk ``job`` kontrak PRD-F02 §4.1.

    ``is_saved`` selalu ``False``: bookmark persisten baru ada di PRD-06.
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
        "source": source,
        "source_url": row.get("source_url"),
        "posted_at": row.get("posted_at"),
        "is_saved": False,
        "match": None,
    }


def get_company(slug: str) -> dict:
    """Ringkasan perusahaan yang **hanya** diturunkan dari tabel ``jobs`` (R-04-07).

    Tidak ada tabel perusahaan, sehingga nama, jumlah lowongan, lokasi, tipe
    kerja, dan skill sering muncul dihitung dari lowongan yang ada. Perusahaan
    yang tidak punya lowongan tidak dapat muncul di sini — dan itu memang
    batas yang benar: tidak ada profil resmi yang boleh ditampilkan (§8).
    """
    baris = repository.find_jobs_by_company(slug)
    if not baris:
        raise NotFoundError("Perusahaan tidak ditemukan.")

    # Nama diambil dari baris terbaru, bukan dikarang dari slug: slug sudah
    # kehilangan kapitalisasi dan tanda baca aslinya.
    nama = baris[0].get("company_name") or slug

    lokasi: list[str] = []
    tipe: list[str] = []
    skill: Counter[str] = Counter()
    sumber = {row["id"]: row["name"] for row in repository.find_sources()}

    for row in baris:
        if row.get("location") and row["location"] not in lokasi:
            lokasi.append(row["location"])
        if row.get("employment_type") and row["employment_type"] not in tipe:
            tipe.append(row["employment_type"])
        for s in row.get("skills") or []:
            if s:
                skill[s] += 1

    return {
        "name": nama,
        "slug": slug,
        "job_count": len(baris),
        "locations": lokasi,
        "employment_types": tipe,
        # Diurutkan menurut frekuensi lalu abjad, supaya hasilnya stabil antar
        # permintaan dan yang paling sering muncul benar-benar di atas.
        "top_skills": [s for s, _ in sorted(skill.items(), key=lambda kv: (-kv[1], kv[0]))][:12],
        "jobs": [_shape_job(row, sumber.get(row.get("source_id"))) for row in baris],
    }


def get_categories() -> dict:
    """Distribusi lowongan per kategori/cluster (R-05-06)."""
    raise NotImplementedError("Diisi pada PRD-05.")


def get_top_skills(limit: int = 15) -> dict:
    """Skill paling banyak dicari (R-05-07)."""
    raise NotImplementedError("Diisi pada PRD-05.")


def get_salary_stats(currency: str | None = None, period: str | None = None) -> dict:
    """Statistik gaji faktual dengan aturan sampel minimal (R-05-08..R-05-10)."""
    raise NotImplementedError("Diisi pada PRD-05.")
