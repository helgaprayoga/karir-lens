"""Route REST API.

Setiap route hanya membaca request, memanggil ``service`` modul terkait, lalu
membungkus hasilnya lewat ``response``. Tidak ada query dan tidak ada aturan
bisnis di sini (R-09-15): endpoint di bawah memanggil fungsi yang sama persis
dengan yang dipakai halaman web.

Bentuk respons mengikuti R-09-12/§4.4:
``{"data": ..., "meta": {...}}`` untuk daftar, ``{"error": {code,message}}``
untuk kesalahan.
"""

from __future__ import annotations

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from core.errors import AppError

from . import bp
from .response import error as error_response
from .response import ok


def api_login_required(view):
    """401 JSON untuk permintaan tanpa sesi (R-09-17).

    ``flask_login.login_required`` mengalihkan 302 ke halaman login — benar
    untuk halaman, salah untuk API: klien JSON tidak dapat mengikuti pengalihan.
    Endpoint PRD-07/PRD-08 sengaja tetap memakai ``login_required`` karena
    kontraknya sudah diuji sebagai 302; endpoint PRD-09 memakai ini.
    """
    from functools import wraps

    from core.errors import UnauthorizedError

    @wraps(view)
    def terbungkus(*args, **kwargs):
        if not current_user.is_authenticated:
            raise UnauthorizedError("Anda perlu masuk terlebih dahulu.")
        return view(*args, **kwargs)

    return terbungkus


# --- Publik (R-09-14) ----------------------------------------------------

@bp.get("/jobs")
def jobs():
    """``GET /api/jobs`` — daftar lowongan (R-09-11, R-09-12).

    Memakai ``app.jobs.service.search_jobs`` yang sama dengan halaman
    ``/jobs``, jadi filter dan urutannya tidak mungkin berbeda (R-09-15).
    """
    from app.jobs import service as jobs_service

    data = jobs_service.search_jobs(
        q=request.args.get("q"),
        city=request.args.getlist("city"),
        employment_type=request.args.getlist("employment_type"),
        source=request.args.getlist("source"),
        category=request.args.getlist("category"),
        sort=request.args.get("sort"),
        page=request.args.get("page"),
        per_page=request.args.get("per_page"),
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    return ok(data["items"], meta=data["meta"])


@bp.get("/jobs/<int:job_id>")
def job_detail(job_id: int):
    """``GET /api/jobs/<id>`` — detail lowongan atau 404 (R-09-13)."""
    from app.jobs import service as jobs_service

    try:
        data = jobs_service.get_job(
            job_id,
            user_id=current_user.id if current_user.is_authenticated else None,
        )
    except AppError as galat:
        return error_response(galat)
    return ok(data["job"])


@bp.get("/companies/<slug>")
def company_detail(slug: str):
    """``GET /api/companies/<slug>`` — ringkasan perusahaan dari tabel jobs."""
    from app.insights import service as insights_service

    try:
        return ok(insights_service.get_company(slug))
    except AppError as galat:
        return error_response(galat)


@bp.get("/insights/categories")
def insights_categories():
    """``GET /api/insights/categories`` — distribusi kategori."""
    from app.insights import service as insights_service

    return ok(insights_service.get_categories())


@bp.get("/insights/skills")
def insights_skills():
    """``GET /api/insights/skills`` — skill paling banyak dicari."""
    from app.insights import service as insights_service

    return ok(insights_service.get_top_skills())


@bp.get("/insights/salary")
def insights_salary():
    """``GET /api/insights/salary`` — statistik gaji faktual (R-05-08..R-05-10).

    Aturan sampel minimal tetap berlaku: bila sampel kurang dari lima, grupnya
    tidak muncul. Endpoint ini tidak menambahkan jalan pintas.
    """
    from app.insights import service as insights_service

    return ok(insights_service.get_salary_stats())


# --- Personal (R-09-14, R-09-17) -----------------------------------------

@bp.get("/recommendations")
@api_login_required
def recommendations():
    """``GET /api/recommendations`` — rekomendasi dari skill terkonfirmasi."""
    from app.cv import service as cv_service

    data = cv_service.get_recommendations(current_user.id)
    return ok(data["recommendations"])


@bp.get("/saved-jobs")
@api_login_required
def saved_jobs():
    """``GET /api/saved-jobs`` — daftar tersimpan dengan pagination."""
    from app.profile import service as profile_service

    data = profile_service.list_saved_jobs(
        current_user.id, request.args.get("page"), request.args.get("per_page")
    )
    return ok(data["items"], meta=data["meta"])


@bp.post("/saved-jobs")
@api_login_required
def save_job():
    """``POST /api/saved-jobs`` — simpan lowongan (idempoten).

    Body JSON ``{"job_id": 12}``. Endpoint ini dimutasi lewat JSON, jadi CSRF
    ditegakkan lewat header ``X-CSRFToken`` yang sama dengan form web; klien
    tanpa token ditolak 400 oleh ``CSRFProtect`` (PRD-09 §9).
    """
    from core.errors import ValidationError
    from app.profile import service as profile_service

    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id") if isinstance(data, dict) else None
    try:
        hasil = profile_service.save_job(current_user.id, int(job_id))
    except (TypeError, ValueError):
        return error_response(ValidationError("job_id harus berupa angka."))
    except AppError as galat:
        return error_response(galat)
    return ok(hasil, status=201 if hasil["created"] else 200)


@bp.delete("/saved-jobs/<int:job_id>")
@api_login_required
def delete_saved_job(job_id: int):
    """``DELETE /api/saved-jobs/<id>`` — hapus bookmark milik sendiri."""
    from app.profile import service as profile_service

    profile_service.remove_saved_job(current_user.id, job_id)
    return ok({"job_id": job_id, "deleted": True})


# --- CV dan asisten ------------------------------------------------------


@bp.post("/cv/extract")
@login_required
def cv_extract():
    """``POST /api/cv/extract`` — ekstraksi skill dari berkas CV.

    Kontrak PRD-F04 §4.1:

        {"data": {"skills": [...], "ambiguous": [{text, reason}]}}

    Bentuk galat memakai ``AppError.to_dict()`` yang sama dengan handler global,
    sehingga klien hanya perlu mengenal satu bentuk.

    **AI fallback tidak dipanggil di sini** (R-07-05, R-07-16): kandidat ambigu
    dikembalikan untuk diputuskan pengguna, bukan dikirim ke layanan luar pada
    setiap unggahan.
    """
    from flask import session

    from app.cv import service as cv_service

    try:
        hasil = cv_service.extract_and_suggest(request.files.get("file"))
    except AppError as error:
        return jsonify({"error": error.to_dict()}), error.status

    # Simpan kandidat di sesi supaya halaman `/cv` dapat menampilkannya setelah
    # dimuat ulang. Yang disimpan hanya nama skill, bukan teks atau berkas CV.
    session["cv_suggestions"] = {
        "skills": hasil.get("skills") or [],
        "ambiguous": hasil.get("ambiguous") or [],
    }

    return jsonify({"data": hasil})


@bp.get("/cv/recommendations")
@login_required
def cv_recommendations():
    """Rekomendasi untuk pengguna login (R-07-09, R-07-11).

    Sama seperti halaman ``/cv``, tidak memanggil AI: skor dihitung dari skill
    terkonfirmasi dan kategori lowongan.
    """
    from app.cv import service as cv_service

    data = cv_service.get_recommendations(current_user.id)
    return jsonify(
        {
            "data": {
                "skills": [s["skill"] for s in data["skills"]],
                "recommendations": data["recommendations"],
            }
        }
    )


@bp.post("/assistant")
@login_required
def assistant():
    """``POST /api/assistant`` — jawaban asisten dari data aplikasi (PRD-08).

    Kontrak PRD-F04 §4.1: ``{"data": {"reply": "...", "sources": [...]}}``.

    Rate limit dan pesan galat ditangani ``service`` lewat ``AppError``,
    sehingga bentuk galatnya sama dengan endpoint lain:
    ``{"error": {code, message}}``.
    """
    from app.assistant import routes as assistant_routes
    from app.assistant import service as assistant_service
    from core.errors import AppError

    data = request.get_json(silent=True) or {}
    pertanyaan = data.get("message") if isinstance(data, dict) else None

    if not pertanyaan or not str(pertanyaan).strip():
        return jsonify(
            {"error": {"code": "VALIDATION_ERROR",
                       "message": "Tulis pertanyaan terlebih dahulu."}}
        ), 400

    batas = int(current_app.config["SETTINGS"].ai_daily_limit or 20)
    try:
        hasil = assistant_service.ask(
            str(pertanyaan),
            current_user.id,
            client=assistant_routes.klien_atas_permintaan(),
            batas_harian=batas,
        )
    except AppError as error:
        return jsonify({"error": error.to_dict()}), error.status
    except Exception:  # noqa: BLE001 - jangan bocorkan detail internal
        current_app.logger.exception("Asisten gagal menjawab")
        return jsonify(
            {"error": {"code": "ASSISTANT_FAILED",
                       "message": "Asisten sedang tidak dapat menjawab. Coba lagi."}}
        ), 502

    return jsonify({"data": hasil})
