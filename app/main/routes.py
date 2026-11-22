"""Route beranda.

Lapisan HTTP saja: membaca request, memanggil service, memilih template.
Tidak ada query dan tidak ada aturan bisnis (ARCHITECTURE §4 aturan 8).
"""

from __future__ import annotations

from flask import jsonify, render_template
from flask_login import current_user

from . import bp


@bp.get("/healthz")
def healthz():
    """``/healthz`` — liveness check untuk Render.

    **Tidak memeriksa database.** Kalau health check ikut menanyakan Supabase,
    gangguan sementara di sana membuat Render menganggap container tidak sehat
    lalu me-restart terus-menerus — gangguan singkat berubah menjadi loop
    restart. Yang dijawab di sini satu hal: apakah proses ini hidup dan
    melayani HTTP.

    Tanpa ``login_required``: Render memanggilnya tanpa sesi.
    """
    return jsonify({"status": "ok"}), 200


@bp.get("/")
def index():
    """``/`` — beranda dengan angka ringkasan dari database.

    ``categories`` diisi PRD-05. Kategori kosong tetap diserahkan ke template
    yang menyembunyikan bagiannya, bukan diisi daftar karangan.
    """
    from app.jobs import service as jobs_service
    from app.insights import service as insights_service

    data = jobs_service.get_home(
        user_id=current_user.id if current_user.is_authenticated else None
    )
    return render_template(
        "main/index.html",
        stats=data["stats"],
        latest=data["latest"],
        categories=insights_service.get_categories(),
    )
