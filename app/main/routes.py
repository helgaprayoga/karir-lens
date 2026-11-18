"""Route beranda.

Lapisan HTTP saja: membaca request, memanggil service, memilih template.
Diisi pada PRD-04.
"""

from __future__ import annotations

from flask import render_template

from . import bp


@bp.get("/")
def index():
    return render_template("main/index.html")
