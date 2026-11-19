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
    gagal = request.args.get("error") == "1"

    if gagal:
        # State error wajib dimiliki setiap daftar (§3.1). Pada Track A
        # kegagalan disimulasikan lewat query string.
        return render_template(
            "jobs/list.html",
            items=[],
            meta={"page": 1, "per_page": PER_PAGE, "total": 0, "has_next": False},
            filters=aktif,
            options=_options(aktif),
            active_count=_active_count(aktif),
            is_loading=False,
            is_error=True,
            url_params={},
            stats={"total_jobs": 0, "total_companies": 0},
            sparkline=[],
            categories=[],
        )

    page = fixtures.jobs_page_empty() if kosong else fixtures.jobs_page(aktif, halaman, PER_PAGE)
    rumah = fixtures.home()
    profil = fixtures.profile()

    return render_template(
        "jobs/list.html",
        items=page["items"],
        meta=page["meta"],
        filters=aktif,
        options=_options(aktif),
        active_count=_active_count(aktif),
        is_loading=loading,
        is_error=False,
        url_params=_url_params(aktif),
        stats=rumah.get("stats", {}),
        sparkline=rumah.get("sparkline", []),
        current_skills=profil.get("skills", []),
        categories=rumah.get("categories", []),
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


@bp.get("/profile")
def profile():
    """Profil pengguna (PRD-F03 R-F03-04, R-F03-05, R-F03-11).

    ``skills`` hanya berisi yang ``is_confirmed`` — skill yang belum
    dikonfirmasi belum dihitung untuk rekomendasi, jadi tidak ditampilkan
    sebagai skill milik pengguna.
    """
    data = fixtures.profile()
    skills = [s for s in data.get("skills", []) if s.get("is_confirmed")]
    return render_template(
        "profile/index.html",
        profile=data.get("user", {}),
        skills=skills,
        summary=data.get("summary", {}),
    )


@bp.get("/saved")
def saved():
    """Lowongan tersimpan (PRD-F03 R-F03-06, R-F03-07)."""
    halaman = request.args.get("page", type=int) or 1
    kosong = request.args.get("empty") == "1"

    page = (
        {"items": [], "meta": {"page": 1, "per_page": PER_PAGE, "total": 0, "has_next": False}}
        if kosong
        else fixtures.saved_page(halaman, PER_PAGE)
    )

    return render_template(
        "profile/saved.html",
        items=page["items"],
        meta=page["meta"],
        url_params={},
    )


@bp.get("/cv")
def cv():
    """Alur CV (PRD-F04 §4.1): unggah → pratinjau skill → konfirmasi → rekomendasi.

    ``?state=`` memilih keadaan yang dirender: ``idle`` (belum unggah),
    ``extracted`` (kandidat skill tersedia), ``no_skills`` (pengguna belum punya
    skill terkonfirmasi), ``ready`` (rekomendasi dapat dihitung).
    """
    data = fixtures.cv()
    keadaan = request.args.get("state", data.get("state", "extracted"))
    if keadaan not in {"idle", "extracted", "no_skills", "ready"}:
        keadaan = "extracted"

    profil = fixtures.profile()
    terkonfirmasi = [s for s in profil.get("skills", []) if s.get("is_confirmed")]

    return render_template(
        "cv/index.html",
        state=keadaan,
        suggested_skills=data.get("suggested_skills", []) if keadaan != "idle" else [],
        ambiguous=data.get("ambiguous", []) if keadaan == "extracted" else [],
        confirmed_skills=terkonfirmasi,
        recommendations=data.get("recommendations", []) if keadaan == "ready" else [],
        max_size_mb=data.get("max_size_mb", 5),
        accepted_types=data.get("accepted_types", [".pdf", ".docx"]),
    )


@bp.get("/assistant")
def assistant():
    """Asisten AI (PRD-F04 R-F04-10 s.d. R-F04-14)."""
    data = fixtures.assistant()
    return render_template(
        "assistant/index.html",
        messages=data.get("messages", []),
        suggestions=data.get("suggestions", []),
        error=None,
    )


# --- API tiruan untuk Track A -------------------------------------------
# Kontrak §4.1 menyebut POST /api/cv/extract dan POST /api/assistant. Endpoint
# produksi itu belum ada (PRD-07/PRD-08). Tiruan ini hidup di blueprint preview
# sehingga URL-nya /preview/api/... dan tidak pernah terdaftar di produksi.
# Template memakai url_for, jadi bentuk responsnya tetap satu kontrak.

@bp.post("/api/cv/extract")
def api_cv_extract():
    """Meniru hasil ekstraksi CV: ``{"data": {"skills": [...], "ambiguous": []}}``."""
    data = fixtures.cv()
    return {
        "data": {
            "skills": data.get("suggested_skills", []),
            "ambiguous": data.get("ambiguous", []),
        }
    }


@bp.post("/api/assistant")
def api_assistant():
    """Meniru jawaban asisten: ``{"data": {"reply": "...", "sources": []}}``."""
    data = fixtures.assistant()
    balasan = data.get("reply", {})
    return {
        "data": {
            "reply": balasan.get("text", ""),
            "sources": balasan.get("sources", []),
        }
    }
