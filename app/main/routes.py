"""Route beranda.

Lapisan HTTP saja: membaca request, memanggil service, memilih template.
Tidak ada query dan tidak ada aturan bisnis (ARCHITECTURE §4 aturan 8).
"""

from __future__ import annotations

from flask import render_template

from . import bp


@bp.get("/")
def index():
    """``/`` — beranda dengan angka ringkasan dari database.

    ``categories`` diisi PRD-05. Kategori kosong tetap diserahkan ke template
    yang menyembunyikan bagiannya, bukan diisi daftar karangan.
    """
    from app.jobs import service as jobs_service
    from app.insights import service as insights_service

    data = jobs_service.get_home()
    return render_template(
        "main/index.html",
        stats=data["stats"],
        latest=data["latest"],
        categories=insights_service.get_categories(),
    )
