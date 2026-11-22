"""Route profil, lowongan tersimpan, dan aksi bookmark (PRD-06).

Lapisan HTTP saja: membaca form, memanggil service, memilih template. Tidak ada
query dan tidak ada aturan bisnis (ARCHITECTURE §4 aturan 8).

Semua route di sini memakai ``login_required`` (R-06-09). Pengunjung diarahkan
ke halaman login dengan ``?next=`` sehingga dapat kembali ke tempat semula.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from core.errors import AppError

from . import bp, service

# Route tujuan "kembali" setelah aksi POST. Hanya path internal yang diterima,
# supaya parameter ini tidak menjadi open redirect.
KEMBALI_KE = {"/jobs", "/saved", "/profile"}


def _kembali(kunci: str = "next") -> str:
    """Tentukan tujuan redirect: halaman asal bila wajar, selain itu /saved."""
    tujuan = request.form.get(kunci) or request.args.get(kunci) or ""
    if tujuan.startswith("/") and not tujuan.startswith("//"):
        dasar = tujuan.split("?", 1)[0]
        if dasar in KEMBALI_KE or dasar.startswith("/jobs/"):
            return tujuan
    return url_for("profile.saved")


@bp.get("/profile")
@login_required
def index():
    """``/profile`` — identitas, skill terkonfirmasi, dan ringkasan (R-06-01)."""
    data = service.get_profile(current_user.id)
    return render_template(
        "profile/index.html",
        profile=data["profile"],
        skills=data["skills"],
        summary=data["summary"],
    )


@bp.post("/profile/name")
@login_required
def update_name():
    """Ubah nama tampilan (R-06-02).

    POST + CSRF + PRG (R-06-08): setelah berhasil, pengguna diarahkan kembali
    ke halaman profil, sehingga refresh tidak mengirim ulang form.
    """
    try:
        service.update_name(current_user.id, request.form.get("name"))
    except AppError as error:
        flash(error.message, "error")
    else:
        flash("Nama berhasil diperbarui.", "success")
    return redirect(url_for("profile.index"))


@bp.get("/saved")
@login_required
def saved():
    """``/saved`` — daftar bookmark dengan pagination (R-06-06, R-06-07)."""
    data = service.list_saved_jobs(
        current_user.id,
        page=request.args.get("page"),
        per_page=request.args.get("per_page"),
    )
    return render_template(
        "profile/saved.html",
        items=data["items"],
        meta=data["meta"],
        url_params={},
    )


@bp.post("/saved/<int:job_id>/add")
@login_required
def add(job_id: int):
    """Simpan bookmark (R-06-03).

    ``NotFoundError`` sengaja **tidak** ditangkap di sini: handler global
    PRD-01 mengubahnya menjadi 404 dengan halaman error yang ramah (R-06-11).
    Menangkapnya lalu mengalihkan ke ``/saved`` akan menyamarkan bahwa
    lowongannya tidak ada — pengguna mengira bookmark-nya sedang bermasalah.
    """
    hasil = service.save_job(current_user.id, job_id)
    flash(
        "Lowongan disimpan." if hasil["created"] else "Lowongan sudah tersimpan.",
        "success" if hasil["created"] else "info",
    )
    return redirect(_kembali())


@bp.post("/saved/<int:job_id>/remove")
@login_required
def remove(job_id: int):
    """Hapus bookmark milik pengguna ini (R-06-04)."""
    service.remove_saved_job(current_user.id, job_id)
    flash("Lowongan dihapus dari tersimpan.", "info")
    return redirect(_kembali())
