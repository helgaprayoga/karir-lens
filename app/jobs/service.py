"""Aturan bisnis katalog lowongan (PRD-04).

Tempat tinggal: validasi filter defensif (nilai di luar himpunan direset ke
default), penyusunan kriteria, dan pembangunan metadata halaman. Fungsi di sini
dipakai ulang oleh ``app/api`` tanpa perubahan (R-09-15).

``service`` tidak mengenal Flask dan tidak menyentuh Supabase langsung
(docs/ARCHITECTURE.md §8.3): seluruh akses data lewat ``repository``.
"""

from __future__ import annotations

from core.errors import NotFoundError
from core.pagination import build_meta, parse_page

from . import repository

VALID_EMPLOYMENT_TYPES = ("full-time", "part-time", "contract", "internship", "freelance")
VALID_SOURCES = ("dealls", "kalibrr", "remotive")
VALID_SORTS = ("posted_desc", "posted_asc", "relevance")
DEFAULT_SORT = "posted_desc"

# `relevance` diurutkan di memori, jadi jumlah baris yang diambil dibatasi.
# 500 cukup untuk seluruh katalog saat ini (49 lowongan) dan tetap aman bila
# data bertumbuh; bila terlewati, hasilnya tetap benar tetapi hanya mencakup
# 500 lowongan terbaru. Keterbatasan ini sengaja daripada membuat full-text
# index yang belum ada di skema.
RELEVANCE_POOL = 500


def _clean_text(value) -> str:
    return str(value or "").strip()


def _as_list(value) -> list[str]:
    """Normalisasi nilai filter menjadi list tanpa duplikat.

    Menerima tiga bentuk yang semuanya lazim di URL:

    - ``?city=Bandung`` (satu nilai)
    - ``?city=Bandung,Jakarta`` (dipisah koma, bentuk yang dipakai chip)
    - ``?city=Bandung&city=Jakarta`` (diulang; ``request.args.getlist``)

    List Python juga diterima, karena ``app/api`` (PRD-09) memanggil service ini
    langsung.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        bagian = []
        for item in value:
            bagian.extend(str(item).split(","))
    else:
        bagian = str(value).split(",")

    hasil: list[str] = []
    for item in bagian:
        bersih = item.strip()
        if bersih and bersih not in hasil:
            hasil.append(bersih)
    return hasil


def _criteria(filters: dict) -> dict:
    """Filter yang sudah divalidasi -> kriteria siap pakai untuk repository."""
    sumber = {
        row.get("name"): row.get("id")
        for row in repository.list_sources()
    }
    return {
        "q": filters["q"],
        "city": filters["city"],
        "employment_type": filters["employment_type"],
        # Nama sumber tak dikenal dibuang, bukan menghasilkan halaman kosong:
        # R-04-02 meminta filter salah direset, bukan error.
        "source_id": [sumber[n] for n in filters["source"] if n in sumber],
        # Kategori disaring lewat `cluster_id`, bukan teks: label cluster
        # berbentuk "Data & Ai & Python" dan tidak akan cocok dengan `q`.
        "cluster_id": filters["category"],
        "sort": filters["sort"],
    }


def _score(job: dict, q: str) -> int:
    """Skor relevansi sederhana dan jujur: makin ke atas field, makin besar.

    Judul lebih menentukan daripada perusahaan, dan perusahaan lebih menentukan
    daripada skill. Tanpa pembobotan seperti ini, "python" akan mengembalikan
    lowongan yang kebetulan menyebut python di daftar skill di atas lowongan
    yang judulnya memang Python Developer.
    """
    teks = q.lower()
    judul = (job.get("title") or "").lower()
    perusahaan = (job.get("company_name") or "").lower()
    skills = [str(s).lower() for s in (job.get("skills") or [])]

    skor = 0
    if judul == teks:
        skor += 100
    elif teks in judul:
        skor += 50
    if teks in perusahaan:
        skor += 20
    skor += 10 * sum(1 for s in skills if teks in s)
    return skor


def _tandai_tersimpan(items: list[dict], user_id: int | None) -> list[dict]:
    """Isi ``is_saved`` dari tabel ``saved_jobs`` (PRD-06).

    Satu query untuk seluruh halaman, bukan satu per kartu: 12 kartu berarti 12
    permintaan ke Supabase bila dilakukan per item. ``user_id=None`` (tamu)
    berarti tidak ada yang tersimpan — bukan "belum dicek".
    """
    if not user_id or not items:
        return items

    from . import repository as jobs_repository

    tersimpan = jobs_repository.saved_ids_for_user(user_id)
    for item in items:
        item["is_saved"] = item.get("id") in tersimpan
    return items


def search_jobs(
    *,
    q: str | None = None,
    city: str | None = None,
    employment_type: str | None = None,
    source: str | None = None,
    category: str | int | None = None,
    sort: str | None = None,
    page: str | int | None = None,
    per_page: str | int | None = None,
    user_id: int | None = None,
) -> dict:
    """Cari lowongan dan kembalikan ``{items, meta, filters, options}`` (R-04-01..R-04-05).

    ``city``, ``employment_type``, ``source``, dan ``category`` menerima
    **banyak nilai**; lihat :func:`_as_list` untuk bentuk yang diterima.
    Hasilnya adalah OR di dalam satu dimensi (Bandung *atau* Jakarta) dan AND
    antar dimensi (kota *dan* tipe kerja).

    ``category`` berisi ``cluster_id`` dari tabel ``clusters``, bukan teks.
    Menyaring kategori lewat pencarian kata tidak mungkin: label cluster
    berbentuk "Data & Ai & Python", gabungan kata pembeda yang tidak muncul
    sebagai satu frasa di judul mana pun.

    Nilai di luar himpunan baku dibuang, bukan menghasilkan error (R-04-02).
    Ini yang membuat ``?employment_type=ngawur`` tetap menampilkan halaman normal.
    """
    kota = _as_list(city)
    tipe = [t for t in _as_list(employment_type) if t in VALID_EMPLOYMENT_TYPES]
    sumber_terpilih = [s for s in _as_list(source) if s in VALID_SOURCES]
    # cluster_id berasal dari database, jadi tidak ada himpunan baku di sini.
    # Yang bukan angka dibuang; yang tidak ada di database tidak menghasilkan
    # error, hanya halaman kosong yang jujur.
    kategori = []
    for nilai in _as_list(category):
        try:
            kategori.append(int(nilai))
        except (TypeError, ValueError):
            continue

    susunan = {
        "q": _clean_text(q),
        "city": kota,
        "employment_type": tipe,
        "source": sumber_terpilih,
        "category": kategori,
        "sort": _clean_text(sort) or DEFAULT_SORT,
    }

    if susunan["sort"] not in VALID_SORTS:
        susunan["sort"] = DEFAULT_SORT
    # `relevance` hanya bermakna bila ada kata kunci.
    if susunan["sort"] == "relevance" and not susunan["q"]:
        susunan["sort"] = DEFAULT_SORT

    halaman, per_halaman, offset = parse_page(
        {"page": page, "per_page": per_page}
    )
    kriteria = _criteria(susunan)

    # Satu permintaan ke tabel `sources` untuk seluruh halaman. Sebelumnya
    # `find_page`, `count`, dan `_options` masing-masing mengambilnya sendiri,
    # dan setiap permintaan ke Supabase berbiaya satu perjalanan jaringan.
    sumber = repository.list_sources()
    peta = {row["id"]: row["name"] for row in sumber}

    if susunan["sort"] == "relevance":
        semua = repository.find_all(kriteria, limit=RELEVANCE_POOL, sumber=peta)
        semua.sort(key=lambda job: _score(job, susunan["q"]), reverse=True)
        total = len(semua)
        items = semua[offset : offset + per_halaman]
    else:
        items = repository.find_page(kriteria, offset, per_halaman, sumber=peta)
        total = repository.count(kriteria)

    items = _tandai_tersimpan(items, user_id)

    return {
        "items": items,
        "meta": build_meta(halaman, per_halaman, total),
        "filters": susunan,
        "options": _options(susunan, sumber=sumber),
    }


def _options(filters: dict, sumber: list[dict] | None = None) -> dict:
    """Chip filter beserta status aktif dan tautan toggle-nya.

    Tautan dibangun di route (yang mengenal ``url_for``), bukan di sini —
    ``service`` tidak boleh mengenal Flask. Bentuknya tetap sama dengan
    kontrak: ``{value, label, active, href}``.
    """
    sumber = sumber if sumber is not None else repository.list_sources()
    lokasi = repository.distinct_locations()
    klaster = repository.list_clusters()

    return {
        "cities": [
            {"value": kota, "label": kota, "active": kota in filters["city"]}
            for kota in lokasi
        ],
        "employment_types": [
            {
                "value": tipe,
                "label": tipe.replace("-", " ").title(),
                "active": tipe in filters["employment_type"],
            }
            for tipe in VALID_EMPLOYMENT_TYPES
        ],
        "sources": [
            {
                "value": row["name"],
                "label": row["name"].title(),
                "active": row["name"] in filters["source"],
            }
            for row in sumber
        ],
        # Kategori berasal dari hasil clustering (PRD-05). Nilainya `cluster_id`,
        # bukan label: label tidak dapat dipakai sebagai kata kunci pencarian.
        "categories": [
            {
                "value": c["id"],
                "label": c["label"],
                "job_count": c["job_count"],
                "active": c["id"] in filters["category"],
            }
            for c in klaster
        ],
    }


def get_job(job_id: int, user_id: int | None = None) -> dict:
    """Detail satu lowongan beserta lowongan serupa (R-04-06, R-04-09).

    Melempar ``NotFoundError`` (``AppError``) agar handler global PRD-01 yang
    memetakannya ke 404 dan memilih tampilan HTML atau JSON.

    ``user_id`` mengisi ``is_saved`` pada lowongan ini dan pada kartu "serupa",
    supaya tombol simpan di halaman detail mencerminkan keadaan sebenarnya
    (PRD-06).
    """
    job = repository.find_by_id(job_id)
    if job is None:
        raise NotFoundError("Lowongan tidak ditemukan.")

    similar = _tandai_tersimpan(
        repository.find_similar(job, limit=6), user_id
    )
    _tandai_tersimpan([job], user_id)

    return {"job": job, "similar": similar}


def get_home(user_id: int | None = None) -> dict:
    """Beranda: ``stats``, ``categories``, dan ``sparkline``.

    ``latest`` sengaja tidak ada: beranda tidak lagi menampilkan kartu lowongan
    (itu tugas ``/jobs``), dan mengambil enam baris untuk sesuatu yang tidak
    dirender hanya menambah satu perjalanan ke database.

    ``categories`` diambil dari ``app.insights.service``, bukan dihitung ulang
    di sini: kategori adalah hasil clustering, dan menghitungnya di dua tempat
    akan menghasilkan dua angka yang bisa berbeda. Impor dilakukan di dalam
    fungsi karena ``insights`` sudah mengimpor ``app.jobs`` (menghindari
    impor melingkar di tingkat modul).
    """
    from app.insights import service as insights_service

    return {
        "stats": repository.totals(),
        "categories": insights_service.get_categories(),
        "sparkline": repository.posted_sparkline(days=7),
    }
