"""Route panel admin (PRD-09).

Lapisan HTTP saja: membaca request, memanggil ``service``, memilih template.
Tidak ada query dan tidak ada aturan bisnis.

Semua route memakai ``admin_required`` (R-09-01). Template yang dirender adalah
template PRD-F05 tanpa perubahan; tautan di dalamnya menunjuk endpoint
``preview.admin_*`` dan diterjemahkan ke padanan produksi oleh
``app/templating.py``, seperti yang sudah dilakukan untuk katalog.
"""

from __future__ import annotations

from flask import redirect, render_template, request, url_for
from flask_login import login_required

from app.auth.decorators import admin_required
from core.errors import AppError

from . import bp, service

PER_PAGE = 20


@bp.get("")
@bp.get("/")
@login_required
@admin_required
def index():
    """``/admin`` — kartu ringkasan dan lima proses terakhir (R-09-02)."""
    return render_template(
        "admin/index.html",
        summary=service.summary(),
        latest_runs=service.list_runs(limit=5),
    )


@bp.get("/jobs")
@login_required
@admin_required
def jobs():
    """``/admin/jobs`` — daftar lowongan dengan pencarian dan pagination."""
    q = (request.args.get("q") or "").strip()
    data = service.list_jobs(q or None, request.args.get("page"), PER_PAGE)
    return render_template(
        "admin/jobs.html",
        items=data["items"],
        meta=data["meta"],
        q=q,
        url_params={"q": q} if q else {},
    )


@bp.post("/jobs/<int:job_id>/delete")
@login_required
@admin_required
def delete_job(job_id: int):
    """``POST /admin/jobs/<id>/delete`` — hapus lowongan setelah konfirmasi.

    POST, bukan GET: tautan yang dapat dipicu prefetch browser atau crawler
    tidak boleh menghapus data (R-09-04).
    """
    try:
        service.remove_job(job_id)
    except AppError as error:
        # Kembali ke daftar dengan pesan, bukan halaman galat: admin sedang
        # meninjau tabel dan mungkin menghapus baris yang sudah hilang.
        data = service.list_jobs(None, 1, PER_PAGE)
        return render_template(
            "admin/jobs.html",
            items=data["items"],
            meta=data["meta"],
            q="",
            url_params={},
            error=error.message,
        ), error.status
    return redirect(url_for("admin.jobs"))


@bp.get("/users")
@login_required
@admin_required
def users():
    """``/admin/users`` — daftar pengguna tanpa password atau CV (R-09-05)."""
    data = service.list_users(request.args.get("page"), PER_PAGE)
    return render_template(
        "admin/users.html",
        items=data["items"],
        meta=data["meta"],
        url_params={},
    )


@bp.get("/runs")
@login_required
@admin_required
def runs():
    """``/admin/runs`` — riwayat pembaruan dengan status dan galat (R-09-06)."""
    return render_template("admin/runs.html", runs=service.list_runs())


@bp.get("/clusters")
@login_required
@admin_required
def clusters():
    """``/admin/clusters`` — hasil clustering untuk ditinjau (R-09-07)."""
    return render_template("admin/clusters.html", clusters=service.list_clusters())
