"""Route REST API.

Setiap route hanya membaca request, memanggil ``service`` modul terkait, lalu
membungkus hasilnya lewat ``response``. Selebihnya diisi pada PRD-09.

Yang ada di sini sekarang hanya endpoint yang **kontraknya sudah ditetapkan**
dan dipakai halaman yang sudah berjalan: ``POST /api/cv/extract`` (PRD-F04 §4.1).
"""

from __future__ import annotations

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from core.errors import AppError

from . import bp


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
