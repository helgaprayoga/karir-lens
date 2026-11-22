"""Route insight dan halaman perusahaan.

PRD-04 mengisi halaman perusahaan (R-04-07). Halaman insight diisi PRD-05.

Lapisan HTTP saja: tidak ada query dan tidak ada aturan bisnis.
"""

from __future__ import annotations

from flask import render_template

from . import bp, service


@bp.get("/companies/<slug>")
def company(slug: str):
    """``/companies/<slug>`` — ringkasan turunan dari tabel ``jobs``.

    ``service.get_company`` melempar ``NotFoundError`` bila tidak ada lowongan
    untuk slug itu; handler global mengubahnya menjadi 404 (R-04-09).
    """
    return render_template("companies/detail.html", company=service.get_company(slug))
