"""Route preview dan /styleguide (R-F01-08, R-F01-09, PRD-F02).

Lapisan HTTP saja: membaca fixture, menyiapkan tautan tampilan, memilih
template. Tidak ada query dan tidak ada aturan bisnis (ARCHITECTURE §4 aturan 8).
"""

from __future__ import annotations

from flask import abort, render_template, request

from . import bp, fixtures

FILTER_KEYS = ("q", "city", "employment_type", "source", "sort")
PER_PAGE = 4


def _filters() -> dict[str, str]:
    """Nilai filter aktif dari query string, dengan default yang aman."""
    hasil = {kunci: (request.args.get(kunci) or "").strip() for kunci in FILTER_KEYS}
    if hasil["sort"] not in {"posted_desc", "posted_asc", "relevance"}:
        hasil["sort"] = "posted_desc"
    return hasil


def _url(**perubahan) -> str:
    """URL /preview/jobs dengan filter saat ini, ditimpa `perubahan`.

    Nilai None atau kosong menghapus filter tersebut, sehingga chip terapan
    benar-benar menghapus filter saat diklik (R-F02-06).
    """
    aktif = _filters()
    aktif.update({k: v for k, v in perubahan.items() if k in FILTER_KEYS})
    bersih = {k: v for k, v in aktif.items() if v and not (k == "sort" and v == "posted_desc")}
    from flask import url_for

    return url_for("preview.jobs", **bersih)


def _options(aktif: dict[str, str]) -> dict:
    """Opsi chip beserta status aktif dan tautan toggle-nya.

    Tautan toggle: bila filter sedang aktif, tautan menghapusnya; bila tidak,
    tautan menerapkannya. Template tidak perlu tahu aturan ini.
    """
    dasar = fixtures.filter_options()

    def bangun(nilai: list[tuple[str, str]] | list[str], kunci: str) -> list[dict]:
        hasil = []
        for item in nilai:
            value, label = item if isinstance(item, tuple) else (item, item)
            sedang = aktif.get(kunci) == value
            hasil.append(
                {
                    "value": value,
                    "label": label,
                    "active": sedang,
                    "href": _url(**{kunci: (None if sedang else value)}),
                }
            )
        return hasil

    return {
        "cities": bangun(dasar["cities"], "city"),
        "employment_types": bangun(
            [(o["value"], o["label"]) for o in dasar["employment_types"]], "employment_type"
        ),
        "sources": bangun([(o["value"], o["label"]) for o in dasar["sources"]], "source"),
    }


def _active_count(aktif: dict[str, str]) -> int:
    return sum(1 for kunci in ("q", "city", "employment_type", "source") if aktif.get(kunci))


@bp.get("/")
def index():
    """Daftar halaman preview yang tersedia saat Track A berjalan."""
    return render_template("preview/index.html", job_count=len(fixtures.jobs()))


@bp.get("/styleguide")
def styleguide():
    """/styleguide — setiap komponen design system §4 dalam semua state.

    Hanya dapat dibuka ketika PREVIEW_UI=true, karena blueprint ``preview``
    tidak diregistrasi sama sekali bila flag itu mati (404).
    """
    page = fixtures.jobs_page(per_page=12)
    return render_template(
        "preview/styleguide.html",
        items=page["items"],
        meta=page["meta"],
        recommended=fixtures.jobs_recommended(),
        insights=fixtures.insights(),
        profile=fixtures.profile(),
        runs=fixtures.runs(),
        admin=fixtures.admin(),
    )


def _url_params(aktif: dict[str, str]) -> dict[str, str]:
    """Query string yang harus dipertahankan saat berpindah halaman."""
    return {k: v for k, v in aktif.items() if v and not (k == "sort" and v == "posted_desc")}


@bp.get("/jobs")
def jobs():
    """Katalog: pencarian, filter, urutan, pagination (PRD-F02 R-F02-01)."""
    aktif = _filters()
    halaman = request.args.get("page", type=int) or 1
    loading = request.args.get("loading") == "1"
    kosong = request.args.get("empty") == "1"

    page = fixtures.jobs_page_empty() if kosong else fixtures.jobs_page(aktif, halaman, PER_PAGE)

    return render_template(
        "jobs/list.html",
        items=page["items"],
        meta=page["meta"],
        filters=aktif,
        options=_options(aktif),
        active_count=_active_count(aktif),
        is_loading=loading,
        url_params=_url_params(aktif),
        categories=fixtures.home().get("categories", []),
    )


@bp.get("/jobs/<int:job_id>")
def job_detail(job_id: int):
    """Detail lowongan beserta lowongan serupa (R-F02-11, R-F02-12)."""
    job = fixtures.job_by_id(job_id)
    if job is None:
        abort(404)
    return render_template(
        "jobs/detail.html",
        job=job,
        similar=fixtures.similar_jobs(job),
    )


@bp.get("/companies/<slug>")
def company_detail(slug: str):
    """Halaman perusahaan, hanya dari data lowongan (R-F02-13, R-F02-14)."""
    company = fixtures.company_by_slug(slug)
    if company is None:
        abort(404)
    return render_template("companies/detail.html", company=company)


@bp.get("/home")
def home():
    """Beranda katalog (PRD-F02 §4.1: stats, latest, categories)."""
    data = fixtures.home()
    return render_template(
        "jobs/home.html",
        stats=data.get("stats", {}),
        latest=data.get("latest", []),
        categories=data.get("categories", []),
    )
