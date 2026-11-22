"""Akses data tabel ``jobs`` untuk katalog publik (PRD-04).

Semua query PostgREST hidup di sini; nilai filter diikat, tidak pernah disusun
dari string mentah (R-04-08).

Bentuk ``job`` yang keluar mengikuti kontrak PRD-F02 §4.1 / PRD-F01 §4.2,
karena template JobCard sudah ditulis terhadap bentuk itu dan tidak boleh
diubah (R-04-11). Kolom yang tidak ada di skema (mis. ``experience_level``)
dikeluarkan sebagai ``None`` alih-alih dikarang.
"""

from __future__ import annotations

import re

from core import db as core_db

TABLE = "jobs"
SOURCES = "sources"
CLUSTERS = "clusters"

# Karakter yang merusak tata bahasa PostgREST bila diteruskan apa adanya ke
# ekspresi `or_()`. Koma memisahkan kondisi, kurung mengelompokkan, kurung
# kurawal milik array literal, dan `%`/`*` adalah wildcard `ilike`.
_UNSAFE = re.compile(r'[,(){}"%*\\]')


def _client():
    return core_db.get_db()


def sanitize_term(value: str | None) -> str:
    """Buang karakter yang punya arti khusus bagi PostgREST (R-04-08).

    Ini bukan pengganti parameter terikat — PostgREST memang menerima filter
    sebagai string — tetapi menghapus karakter yang dapat mengubah struktur
    ekspresi filter yang kita susun sendiri. Spasi ganda dirapikan supaya kata
    kunci tidak berubah menjadi dua token kosong saat disisipkan ke ``ilike``.
    """
    bersih = _UNSAFE.sub(" ", str(value or ""))
    return " ".join(bersih.split())


def _apply_criteria(query, criteria: dict):
    """Terapkan kriteria pencarian dan filter ke query PostgREST.

    ``city``, ``employment_type``, dan ``source_id`` berupa **list**: satu
    nilai memakai ``eq`` (memakai index), beberapa nilai memakai ``in``.
    Memakai ``in`` untuk satu nilai juga benar, tetapi PostgREST tidak dapat
    memakai index sebaik ``eq``; perbedaan ini terasa saat data bertumbuh.
    """
    q = sanitize_term(criteria.get("q"))
    if q:
        # R-04-03: judul, perusahaan, dan skill. `cs` adalah "contains" untuk
        # kolom text[] sehingga skill dapat dicari tanpa tabel bantu.
        query = query.or_(
            f"title.ilike.%{q}%,company_name.ilike.%{q}%,skills.cs.{{{q}}}"
        )

    def _terapkan(kolom: str, nilai) -> None:
        nonlocal query
        if not nilai:
            return
        bersih = [v for v in nilai if v]
        if not bersih:
            return
        if len(bersih) == 1:
            query = query.eq(kolom, bersih[0])
        else:
            query = query.in_(kolom, bersih)

    _terapkan("location", criteria.get("city") or [])
    _terapkan("employment_type", criteria.get("employment_type") or [])
    _terapkan("source_id", criteria.get("source_id") or [])
    _terapkan("cluster_id", criteria.get("cluster_id") or [])

    return query


def _order(query, sort: str, descending: bool = True):
    """Urutan yang didukung R-04-04.

    ``relevance`` tidak punya padanan di PostgREST tanpa full-text index, jadi
    ia diurutkan di service setelah baris diambil. Di sini ia jatuh ke urutan
    tanggal agar pemotongan rentang tetap deterministik.
    """
    if sort == "posted_asc":
        return query.order("posted_at", desc=False)
    return query.order("posted_at", desc=descending)


def _source_map() -> dict[int, str]:
    """``source_id`` -> nama sumber, untuk kolom ``source`` pada kontrak."""
    return {row["id"]: row["name"] for row in list_sources()}


def _shape(row: dict, sumber: dict[int, str]) -> dict:
    """Baris database -> bentuk ``job`` kontrak PRD-F02 §4.1."""
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "company_name": row.get("company_name"),
        "company_slug": row.get("company_slug"),
        "location": row.get("location"),
        "employment_type": row.get("employment_type"),
        # Tidak ada di skema dan tidak diturunkan dari apa pun; `None` lebih
        # jujur daripada menebak tingkat pengalaman dari judul.
        "experience_level": None,
        "description": row.get("description"),
        "skills": row.get("skills") or [],
        # `declared` = sumber menyatakannya sendiri; `inferred` = hasil kamus
        # dari judul/deskripsi. Template memakainya untuk memberi keterangan,
        # supaya skill hasil tebakan tidak tampil sebagai pernyataan rekruter.
        "skills_source": row.get("skills_source"),
        "salary_min": row.get("salary_min"),
        "salary_max": row.get("salary_max"),
        "salary_currency": row.get("salary_currency"),
        "salary_period": row.get("salary_period"),
        "source": sumber.get(row.get("source_id")),
        "source_url": row.get("source_url"),
        "posted_at": row.get("posted_at"),
        # Bookmark persisten adalah PRD-06. Sampai itu ada, tidak ada lowongan
        # yang tersimpan — bukan `False` yang dikarang dari ketiadaan tabel.
        "is_saved": False,
        "match": None,
    }


def find_page(
    criteria: dict, offset: int, limit: int, sumber: dict[int, str] | None = None
) -> list[dict]:
    """Sebagian baris sesuai kriteria dan rentang halaman.

    ``sumber`` dapat diberikan pemanggil agar peta sumber tidak diambil ulang
    pada setiap fungsi. Satu halaman katalog cukup satu permintaan ke tabel
    ``sources``, bukan tiga.
    """
    query = _client().table(TABLE).select("*")
    query = _apply_criteria(query, criteria)
    query = _order(query, criteria.get("sort", "posted_desc"))
    query = query.range(offset, offset + max(0, limit - 1))

    peta = sumber if sumber is not None else _source_map()
    return [_shape(row, peta) for row in (query.execute().data or [])]


def find_all(
    criteria: dict, limit: int = 500, sumber: dict[int, str] | None = None
) -> list[dict]:
    """Baris yang cocok tanpa pagination, untuk pengurutan ``relevance``.

    Dibatasi ``limit`` agar permintaan tidak menarik seluruh tabel ke memori.
    Bila hasil melebihi batas, pengurutan relevansi hanya berlaku pada ``limit``
    baris pertama menurut tanggal — keterbatasan yang disengaja dan dicatat di
    service.
    """
    query = _client().table(TABLE).select("*")
    query = _apply_criteria(query, criteria)
    query = _order(query, "posted_desc").limit(limit)

    peta = sumber if sumber is not None else _source_map()
    return [_shape(row, peta) for row in (query.execute().data or [])]


def count(criteria: dict) -> int:
    """Jumlah baris yang cocok, untuk metadata pagination."""
    query = _client().table(TABLE).select("id", count="exact")
    query = _apply_criteria(query, criteria)
    hasil = query.execute()
    jumlah = getattr(hasil, "count", None)
    if jumlah is not None:
        return jumlah
    return len(hasil.data or [])


def find_by_id(job_id: int) -> dict | None:
    hasil = (
        _client().table(TABLE).select("*").eq("id", job_id).limit(1).execute()
    )
    baris = hasil.data or []
    if not baris:
        return None
    return _shape(baris[0], _source_map())


def find_similar(job: dict, limit: int = 6) -> list[dict]:
    """Lowongan serupa berdasarkan skill yang sama (R-04-06).

    Diambil lewat irisan skill pada sisi database (``ov`` = "overlaps"), lalu
    diperingkat di sini menurut jumlah skill yang beririsan. Lowongan tanpa
    skill tidak punya dasar kemiripan, jadi hasilnya kosong alih-alih diisi
    lowongan acak.
    """
    skills = [s for s in (job.get("skills") or []) if s]
    if not skills:
        return []

    hasil = (
        _client()
        .table(TABLE)
        .select("*")
        .ov("skills", skills)
        .neq("id", job.get("id"))
        .order("posted_at", desc=True)
        .limit(limit * 4)
        .execute()
    )
    sumber = _source_map()

    calon = []
    for row in hasil.data or []:
        skor = len(set(row.get("skills") or []) & set(skills))
        if skor:
            calon.append((skor, _shape(row, sumber)))

    calon.sort(key=lambda item: item[0], reverse=True)
    return [job_ for _, job_ in calon[:limit]]


def distinct_locations(limit: int = 10) -> list[str]:
    """Kota/lokasi dari data, diurutkan menurut **jumlah lowongan** (R-04-01).

    Urutan alfabetis menghasilkan chip yang paling tidak berguna lebih dulu —
    data nyata memberi "Aceh Besar" dan "Ambon" masing-masing satu lowongan di
    depan, sementara "Jakarta Barat" yang berisi empat lowongan tersembunyi.
    Yang sering muncul didahulukan agar chip benar-benar bisa dipakai menyaring.
    """
    baris = (
        _client()
        .table(TABLE)
        .select("location")
        .order("location")
        .limit(1000)
        .execute()
        .data
        or []
    )

    hitung: dict[str, int] = {}
    for row in baris:
        lokasi = row.get("location")
        if lokasi:
            hitung[lokasi] = hitung.get(lokasi, 0) + 1

    urut = sorted(hitung.items(), key=lambda kv: (-kv[1], kv[0]))
    return [lokasi for lokasi, _ in urut[:limit]]


def list_clusters() -> list[dict]:
    """Cluster yang **punya lowongan**, untuk chip kategori (PRD-05).

    Hanya yang ``job_count > 0``: cluster kosong adalah sisa eksekusi lama, dan
    menjadikannya chip yang selalu menghasilkan nol hasil hanya membingungkan.
    Jumlahnya dihitung dari tabel ``jobs``, bukan dari kolom tersimpan yang
    bisa basi setelah lowongan dihapus.
    """
    klaster = (
        _client().table(CLUSTERS).select("id,label").order("id").execute().data or []
    )
    if not klaster:
        return []

    pasangan = _client().table(TABLE).select("cluster_id").execute().data or []
    hitung: dict[int, int] = {}
    for baris in pasangan:
        cid = baris.get("cluster_id")
        if cid is not None:
            hitung[cid] = hitung.get(cid, 0) + 1

    hasil = [
        {
            "id": c["id"],
            "label": c.get("label") or f"Kategori {c['id']}",
            "job_count": hitung[c["id"]],
        }
        for c in klaster
        if hitung.get(c["id"])
    ]
    hasil.sort(key=lambda c: (-c["job_count"], c["id"]))
    return hasil


def list_sources() -> list[dict]:
    """Sumber yang benar-benar tercatat, untuk chip filter."""
    return (
        _client().table(SOURCES).select("id,name").order("name").execute().data or []
    )


def newest(limit: int = 6) -> list[dict]:
    """Lowongan terbaru untuk beranda."""
    hasil = (
        _client()
        .table(TABLE)
        .select("*")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
    )
    sumber = _source_map()
    return [_shape(row, sumber) for row in (hasil.data or [])]


def totals() -> dict:
    """Angka ringkasan beranda, dihitung dari tabel yang benar-benar ada."""
    klien = _client()

    jumlah_jobs = getattr(
        klien.table(TABLE).select("id", count="exact").execute(), "count", None
    ) or 0

    slugs = klien.table(TABLE).select("company_slug").execute().data or []
    perusahaan = {row["company_slug"] for row in slugs if row.get("company_slug")}

    # Kategori berasal dari `clusters` yang diisi `python -m scraper cluster`
    # (PRD-05). Tanpa clustering, angkanya nol — bukan jumlah kategori yang
    # dikarang dari skill.
    jumlah_kategori = getattr(
        klien.table("clusters").select("id", count="exact").execute(), "count", None
    ) or 0

    return {
        "total_jobs": jumlah_jobs,
        "total_companies": len(perusahaan),
        "total_categories": jumlah_kategori,
    }


def posted_sparkline(days: int = 7) -> list[int]:
    """Jumlah lowongan per hari selama ``days`` hari terakhir.

    Dihitung dari ``posted_at`` yang ada. Sumber tanpa tanggal tidak ikut
    dihitung ke hari mana pun — memasukkannya ke hari ini akan menggelembungkan
    angka "lowongan baru".
    """
    from datetime import datetime, timedelta, timezone

    batas = datetime.now(timezone.utc) - timedelta(days=days)
    baris = (
        _client()
        .table(TABLE)
        .select("posted_at")
        .gte("posted_at", batas.isoformat())
        .execute()
        .data
        or []
    )

    hitung = [0] * days
    for row in baris:
        teks = row.get("posted_at")
        if not teks:
            continue
        try:
            waktu = datetime.fromisoformat(str(teks).replace("Z", "+00:00"))
        except ValueError:
            continue
        if waktu.tzinfo is None:
            waktu = waktu.replace(tzinfo=timezone.utc)
        selisih = (datetime.now(timezone.utc) - waktu).days
        if 0 <= selisih < days:
            hitung[days - 1 - selisih] += 1
    return hitung
