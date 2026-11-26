"""Akses data untuk insight (PRD-05).

Modul insight membaca tabel ``jobs`` dan ``clusters`` lewat repository miliknya
sendiri, bukan lewat ``app/jobs/repository.py`` (docs/ARCHITECTURE.md §5).

Agregasi dilakukan di sini, bukan di ``service``: service memutuskan *apa* yang
ditampilkan, repository memutuskan *bagaimana* mengambilnya.
"""

from __future__ import annotations

from core import db as core_db

TABLE = "jobs"
CLUSTERS = "clusters"


def _client():
    return core_db.get_db()


def find_jobs_by_company(slug: str) -> list[dict]:
    """Semua lowongan satu perusahaan, terbaru lebih dulu (R-05-12)."""
    hasil = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("company_slug", slug)
        .order("posted_at", desc=True)
        .execute()
    )
    return hasil.data or []


def find_sources() -> list[dict]:
    """``source_id`` -> nama sumber, untuk kolom ``source`` pada kontrak job."""
    return _client().table("sources").select("id,name").execute().data or []


def find_clusters() -> list[dict]:
    """Semua cluster beserta jumlah lowongan yang benar-benar menunjuknya.

    ``job_count`` dihitung ulang dari tabel ``jobs`` alih-alih memakai kolom
    tersimpan: kolom itu ditulis saat clustering berjalan, dan bila ada
    lowongan yang dihapus sesudahnya angkanya akan basi. Angka yang tampil di
    halaman harus sama dengan isi database saat halaman dibuka.
    """
    klaster = (
        _client().table(CLUSTERS).select("id,label,keywords").order("id").execute().data
        or []
    )
    if not klaster:
        return []

    pasangan = _client().table(TABLE).select("cluster_id").execute().data or []
    hitung: dict[int, int] = {}
    for baris in pasangan:
        cid = baris.get("cluster_id")
        if cid is not None:
            hitung[cid] = hitung.get(cid, 0) + 1

    hasil = []
    for c in klaster:
        jumlah = hitung.get(c["id"], 0)
        if jumlah == 0:
            # Cluster tanpa lowongan tidak ditampilkan: ia sisa eksekusi lama
            # yang datanya berubah, dan menampilkannya sebagai "0 lowongan"
            # hanya membingungkan.
            continue
        hasil.append(
            {
                "cluster_id": c["id"],
                "label": c.get("label") or f"Kategori {c['id']}",
                "keywords": c.get("keywords") or [],
                "job_count": jumlah,
            }
        )

    hasil.sort(key=lambda c: (-c["job_count"], c["cluster_id"]))
    return hasil


def find_all_jobs() -> list[dict]:
    """Seluruh lowongan dengan kolom yang dipakai agregasi insight.

    Hanya kolom yang dibutuhkan: menarik ``description`` untuk 356 baris hanya
    untuk menghitung skill berarti memindahkan ratusan kilobyte tanpa guna.
    """
    return (
        _client()
        .table(TABLE)
        .select("id,skills,salary_min,salary_max,salary_currency,salary_period")
        .execute()
        .data
        or []
    )


def find_jobs_with_salary(currency: str | None = None, period: str | None = None) -> list[dict]:
    """Lowongan yang mencantumkan gaji, beserta ``cluster_id`` (R-05-08).

    ``cluster_id`` ikut diambil karena statistik per kategori dihitung dari
    baris yang sama: dua query terpisah dapat menghasilkan angka yang berbeda
    bila data berubah di antara keduanya.

    Filter mata uang/periode di sini hanya mempercepat; aturan sebenarnya ada
    di ``salary.py`` yang tetap memisahkan dan membuang sampel kecil.
    """
    query = _client().table(TABLE).select(
        "salary_min,salary_max,salary_currency,salary_period,cluster_id"
    )
    if currency:
        query = query.eq("salary_currency", currency)
    if period:
        query = query.eq("salary_period", period)
    return query.execute().data or []


def count_jobs() -> int:
    """Jumlah lowongan aktif."""
    hasil = _client().table(TABLE).select("id", count="exact").execute()
    jumlah = getattr(hasil, "count", None)
    return jumlah if jumlah is not None else len(hasil.data or [])


def find_all_skills() -> list[list[str]]:
    """Daftar skill per lowongan, untuk menghitung skill popularitas.

    Mengembalikan list-of-list (bukan Counter) karena repository tidak
    seharusnya tahu bentuk akhirnya.
    """
    baris = _client().table(TABLE).select("skills").execute().data or []
    return [list(b.get("skills") or []) for b in baris]


def find_skill_counts(limit: int = 15) -> list[dict]:
    """Skill dan jumlah lowongan yang memintanya (R-05-07)."""
    from collections import Counter

    hitung: Counter[str] = Counter()
    for skills in find_all_skills():
        for nama in skills:
            if nama:
                hitung[str(nama)] += 1

    return [
        {"skill": nama, "job_count": jumlah}
        for nama, jumlah in hitung.most_common(limit)
    ]
