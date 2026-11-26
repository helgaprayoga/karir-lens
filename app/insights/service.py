"""Aturan bisnis insight (PRD-05).

Tempat tinggal: aturan sampel gaji minimal, pemisahan mata uang, dan larangan
menampilkan prediksi. Dipakai ulang oleh ``/api/insights/*`` (R-05-15, R-09-15).

``service`` tidak mengenal Flask dan tidak menyentuh Supabase langsung
(docs/ARCHITECTURE.md §8.3): seluruh akses data lewat ``repository``.
"""

from __future__ import annotations

from collections import Counter

from core.errors import NotFoundError

from . import repository, salary

# Batas skill yang ditampilkan. Grafik batang horizontal menjadi tidak terbaca
# di atas ~12 baris, terutama pada 360px (R-F05-05).
DEFAULT_SKILL_LIMIT = 6


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


# --- Kategori dan skill --------------------------------------------------

def get_categories() -> list[dict]:
    """Distribusi lowongan per kategori/cluster (R-05-06).

    Mengembalikan list, bukan dict: template mengiterasinya langsung
    (``{% for kategori in categories %}``), dan bentuk itu yang tertulis di
    kontrak PRD-F05 §4.1.
    """
    return repository.find_clusters()


def get_top_skills(limit: int = DEFAULT_SKILL_LIMIT) -> list[dict]:
    """Skill paling banyak dicari (R-05-07)."""
    return repository.find_skill_counts(limit=limit)


# --- Gaji ----------------------------------------------------------------

def get_salary_stats(currency: str | None = None, period: str | None = None) -> dict:
    """Statistik gaji faktual dengan aturan sampel minimal (R-05-08..R-05-10).

    Seluruh aturan tinggal di ``salary.py``: titik tengah rentang, ambang lima
    sampel, pemisahan mata uang dan periode, serta kuartil. Service hanya
    menyediakan barisnya.

    ``by_category`` berisi rata-rata per kategori, dihitung dari baris yang sama
    sehingga dua bagian halaman tidak pernah berbeda angka.
    """
    baris = repository.find_jobs_with_salary(currency, period)
    total = salary.salary_stats(baris)

    labels = {row["cluster_id"]: row.get("label") for row in repository.find_clusters()}
    total["by_category"] = salary.group_salaries_by_cluster(baris, labels)
    return total


# --- Ringkasan halaman ---------------------------------------------------

def get_insights() -> dict:
    """Semua bagian halaman ``/insights`` dalam satu panggilan.

    Bentuknya mengikuti kontrak PRD-F05 §4.1, ditambah ``summary`` yang dipakai
    ``StatTile`` di atas halaman. Template memakai keduanya, jadi keduanya
    dihitung di satu tempat agar angkanya tidak berasal dari dua query berbeda
    yang dapat berbeda hasilnya.
    """
    kategori = get_categories()
    skills = get_top_skills()
    gaji = get_salary_stats()

    semua = repository.find_all_skills()
    unik = {s for daftar in semua for s in daftar if s}
    total = repository.count_jobs()

    return {
        "categories": kategori,
        "skills": skills,
        "salary": gaji,
        "sample_sufficient": gaji["sample_sufficient"],
        "summary": {
            "total_jobs": total,
            "unique_skills": len(unik),
            "categories": len(kategori),
        },
    }


# --- Perusahaan ---------------------------------------------------------

def get_company(slug: str) -> dict:
    """Ringkasan perusahaan yang **hanya** diturunkan dari tabel ``jobs`` (R-05-12).

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
