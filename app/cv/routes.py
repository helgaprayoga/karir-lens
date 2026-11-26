"""Route CV dan rekomendasi (PRD-07).

Lapisan HTTP saja: membaca request, memanggil service, memilih template. Tidak
ada ekstraksi maupun perhitungan di sini.

Semua route memakai ``login_required``: rekomendasi hanya tersedia untuk
pengguna login dengan skill terkonfirmasi (R-07-12).
"""

from __future__ import annotations

from flask import redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from core.errors import AppError

from . import bp, service


def _state(user_id: int) -> dict:
    """Keadaan halaman: ``idle`` | ``extracted`` | ``no_skills`` | ``ready``.

    Empat keadaan ini yang dikenal template (PRD-F04 §4.1); memilihnya di satu
    tempat mencegah route dan template berbeda pendapat.

    Hanya skill yang dibaca di sini. Skor rekomendasi **tidak** dihitung:
    halaman ini berhenti setelah skill tersimpan, dan lowongan tampil di
    ``/jobs`` (``?sort=relevance``). Menghitung 200 kandidat untuk kartu yang
    tidak dirender hanya membebani setiap kunjungan.
    """
    skills = service.confirmed_skills(user_id)
    if not skills:
        return {"state": "no_skills", "skills": []}
    return {"state": "ready", "skills": skills}


@bp.get("")
@bp.get("/")
@login_required
def index():
    """``/cv`` — unggah, pratinjau skill, konfirmasi, rekomendasi.

    **Kandidat hasil ekstraksi dibaca dari sesi.** Endpoint ``/api/cv/extract``
    mengembalikan skill ke JavaScript, lalu halaman dimuat ulang untuk
    menampilkannya. Tanpa tempat menyimpan di antara dua permintaan itu,
    hasilnya hilang dan pengguna hanya melihat "belum ada skill" setelah
    mengunggah — persis yang terjadi sebelum perbaikan ini.

    Yang disimpan di sesi hanya **nama skill** (beberapa puluh karakter), bukan
    teks atau berkas CV. Cookie sesi ditandatangani Flask, dan isinya dihapus
    begitu pengguna mengonfirmasi.
    """
    kandidat = session.get("cv_suggestions") or {}
    skills = service.normalize_suggestions(kandidat.get("skills") or [])
    ambigu = kandidat.get("ambiguous") or []

    data = _state(current_user.id)

    if skills:
        return render_template(
            "cv/index.html",
            state="extracted",
            suggested_skills=skills,
            ambiguous=ambigu,
            confirmed_skills=data["skills"],
            max_size_mb=service.MAX_SIZE_BYTES // 1048576,
            accepted_types=list(service.ALLOWED_EXTENSIONS),
        )

    return render_template(
        "cv/index.html",
        state=data["state"],
        suggested_skills=[],
        ambiguous=[],
        confirmed_skills=data["skills"],
        max_size_mb=service.MAX_SIZE_BYTES // 1048576,
        accepted_types=list(service.ALLOWED_EXTENSIONS),
    )


@bp.post("/confirm")
@login_required
def confirm():
    """Simpan skill yang dicentang pengguna (R-07-06, R-07-07).

    Skill yang gagal disimpan tidak menggagalkan halaman: pengguna diarahkan
    kembali ke ``/cv`` dan dapat mencoba lagi. Pesan galatnya tidak memuat isi
    CV — hanya alasan validasi (R-07-08).
    """
    dipilih = request.form.getlist("skills")
    try:
        service.save_confirmed_skills(current_user.id, dipilih, source="cv")
    except AppError:
        # Tidak dicatat isinya; `service` sudah mencatat jenis kegagalannya.
        pass
    else:
        # Kandidat sudah diputuskan; jangan biarkan panel konfirmasi muncul lagi
        # pada kunjungan berikutnya.
        session.pop("cv_suggestions", None)

    return redirect(url_for("cv.index"))


@bp.post("/skills/<int:skill_id>/remove")
@login_required
def remove_skill(skill_id: int):
    """Hapus satu skill terkonfirmasi (R-07-15)."""
    from app.profile import service as profile_service

    profile_service.remove_skill(current_user.id, skill_id)
    return redirect(url_for("cv.index"))
