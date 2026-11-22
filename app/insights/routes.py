"""Route insight dan halaman perusahaan.

Lapisan HTTP saja: membaca request, memanggil service, memilih template.
Tidak ada query dan tidak ada aturan bisnis (ARCHITECTURE §4 aturan 8).

Clustering TIDAK dijalankan di sini. Ia proses terpisah
(``python -m scraper cluster``) karena memuat scikit-learn dan memakan detik —
menjalankannya per permintaan akan menahan setiap pengunjung (R-05-13).
"""

from __future__ import annotations

from flask import render_template, request

from . import bp, service


@bp.get("/insights")
def index():
    """``/insights`` — kategori, skill, dan statistik gaji.

    ``?sample=low`` memaksa keadaan "data terbatas" agar pesannya dapat
    diperiksa tanpa mengubah data. Dipakai untuk pengujian manual §7.2 butir 4.
    """
    data = service.get_insights()

    gaji = data["salary"]
    if request.args.get("sample") == "low":
        # Keadaan sampel kurang: kelompok dikosongkan, bukan diisi angka nol.
        gaji = {
            "sample_sufficient": False,
            "minimum_sample": gaji["minimum_sample"],
            "groups": [],
        }

    return render_template(
        "insights/index.html",
        categories=data["categories"],
        skills=data["skills"],
        salary=gaji,
        summary=data["summary"],
    )


@bp.get("/companies/<slug>")
def company(slug: str):
    """``/companies/<slug>`` — ringkasan turunan dari tabel ``jobs``.

    ``service.get_company`` melempar ``NotFoundError`` bila tidak ada lowongan
    untuk slug itu; handler global mengubahnya menjadi 404 (R-04-09).
    """
    return render_template("companies/detail.html", company=service.get_company(slug))
