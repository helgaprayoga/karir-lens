"""Route preview dan /styleguide (R-F01-08, R-F01-09).

Lapisan HTTP saja: membaca fixture, memilih template. Tidak ada query, tidak
ada aturan bisnis (docs/ARCHITECTURE.md §4 aturan 8).
"""

from __future__ import annotations

from flask import render_template

from . import bp, fixtures


def _sample_jobs() -> list[dict]:
    items = fixtures.jobs()
    if items:
        return items
    return []


@bp.get("/")
def index():
    """Daftar halaman preview yang tersedia saat Track A berjalan."""
    return render_template(
        "preview/index.html",
        job_count=len(fixtures.jobs()),
    )


@bp.get("/styleguide")
def styleguide():
    """/styleguide — setiap komponen design system §4 dalam semua state.

    Halaman ini hanya dapat dibuka ketika PREVIEW_UI=true, karena blueprint
    ``preview`` tidak diregistrasi sama sekali bila flag itu mati (404).
    """
    page = fixtures.jobs_page()
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
