"""Route katalog lowongan.

Lapisan HTTP saja (ARCHITECTURE §4 aturan 8): membaca request, memanggil
service, memilih template. Tidak ada query, tidak ada aturan bisnis.

Template yang dirender adalah template PRD-F02 tanpa perubahan (R-04-11).
"""

from __future__ import annotations

from flask import render_template, request, url_for
from flask_login import current_user

from . import bp, service

FILTER_KEYS = ("q", "city", "employment_type", "source", "category", "sort")


def _params(filters: dict, **timpa) -> dict[str, str]:
    """Query string aktif, ditimpa ``timpa``; nilai kosong/default dibuang.

    Filter bernilai banyak digabung dengan koma (``city=Bandung,Jakarta``),
    bukan diulang sebagai parameter yang sama. Bentuk koma membuat URL dapat
    dibaca, dan ``_as_list`` di service menerima keduanya.

    Dipakai untuk tautan chip dan pagination supaya filter tidak hilang saat
    berpindah halaman (R-F02-10).
    """
    gabung = {}
    for kunci in FILTER_KEYS:
        nilai = filters.get(kunci, "")
        # Nilai filter dapat berupa list (multipilih) atau string. `category`
        # berisi `cluster_id` berupa int, jadi setiap elemen dijadikan str
        # sebelum digabung — `",".join()` menolak int.
        gabung[kunci] = ",".join(str(v) for v in nilai) if isinstance(nilai, list) else nilai
    gabung.update(timpa)
    return {
        kunci: nilai
        for kunci, nilai in gabung.items()
        if nilai and not (kunci == "sort" and nilai == service.DEFAULT_SORT)
    }


def _with_href(options: dict, filters: dict) -> dict:
    """Tambahkan ``href`` pada setiap chip: klik = toggle filter (R-F02-06).

    Klik chip yang **belum** aktif menambahkannya ke daftar nilai; klik chip
    yang sudah aktif menghapusnya dari daftar. Dengan begitu beberapa kota atau
    beberapa tipe kerja dapat dipilih sekaligus, dan menghapus salah satunya
    tidak menghapus yang lain.
    """
    nama_parameter = {
        "cities": "city",
        "employment_types": "employment_type",
        "sources": "source",
        "categories": "category",
    }
    hasil = {}
    for kunci, daftar in options.items():
        nama = nama_parameter[kunci]
        terpilih = list(filters.get(nama) or [])
        hasil[kunci] = [
            {
                **chip,
                "href": url_for(
                    "jobs.index",
                    **_params(
                        filters,
                        **{
                            nama: ",".join(
                                str(v)
                                for v in (
                                    [v for v in terpilih if v != chip["value"]]
                                    if chip["active"]
                                    else terpilih + [chip["value"]]
                                )
                            )
                        },
                    ),
                ),
            }
            for chip in daftar
        ]
    return hasil


@bp.get("")
@bp.get("/")
def index():
    """``/jobs`` — pencarian, filter, urutan, pagination server-side (R-04-01).

    Dua aturan menangani bentuk URL yang sama: blueprint memakai
    ``url_prefix="/jobs"``, jadi ``""`` menghasilkan ``/jobs`` dan ``"/"``
    menghasilkan ``/jobs/``. Tanpa keduanya, ``/jobs`` (tautan yang dipakai
    navigasi) akan dialihkan 308 ke ``/jobs/`` — pengalihan yang tidak perlu
    dan memecah URL kanonik.
    """
    data = service.search_jobs(
        q=request.args.get("q"),
        # `getlist` menangkap `?city=A&city=B`; service juga menerima bentuk
        # koma (`?city=A,B`). Keduanya didukung karena tautan chip memakai koma
        # sedangkan API dan tautan luar bisa memakai bentuk berulang.
        city=request.args.getlist("city"),
        employment_type=request.args.getlist("employment_type"),
        source=request.args.getlist("source"),
        category=request.args.getlist("category"),
        sort=request.args.get("sort"),
        page=request.args.get("page"),
        per_page=request.args.get("per_page"),
        # Pengguna login melihat tombol simpan yang mencerminkan keadaan
        # sebenarnya; tamu tidak punya bookmark (PRD-06).
        user_id=current_user.id if current_user.is_authenticated else None,
    )

    filters = data["filters"]

    # `active_count` menghitung nilai yang terpilih, bukan dimensi: memilih dua
    # kota berarti dua filter aktif, sama seperti yang dilakukan pengguna.
    aktif = len([filters["q"]]) if filters.get("q") else 0
    for kunci in ("city", "employment_type", "source", "category"):
        aktif += len(filters.get(kunci) or [])

    return render_template(
        "jobs/list.html",
        items=data["items"],
        meta=data["meta"],
        filters=filters,
        options=_with_href(data["options"], filters),
        active_count=aktif,
        is_loading=False,
        is_error=False,
        url_params=_params(filters),
        # `sparkline` dan `categories` dibiarkan kosong: keduanya bagian beranda
        # dan insight. Template sudah menanganinya kosong, dan menghitungnya di
        # setiap halaman daftar berarti tiga permintaan database yang hasilnya
        # tidak ditampilkan.
        stats={},
        sparkline=[],
        categories=[],
    )


@bp.get("/<int:job_id>")
def detail(job_id: int):
    """``/jobs/<id>`` — detail dan lowongan serupa (R-04-06).

    ``service.get_job`` melempar ``NotFoundError`` bila ID tidak ada; handler
    global yang mengubahnya menjadi 404 (R-04-09).
    """
    data = service.get_job(
        job_id,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    return render_template("jobs/detail.html", job=data["job"], similar=data["similar"])
