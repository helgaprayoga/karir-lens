"""Navigasi header yang hanya menampilkan tautan yang sudah terdaftar.

PRD-01 baru mengisi ``main`` dan ``auth``; blueprint lain menyusul pada PRD-04
sampai PRD-09. Memanggil ``url_for`` untuk endpoint yang belum ada akan
melempar ``BuildError``, jadi daftar tautan disaring terhadap
``app.view_functions``.
"""

from __future__ import annotations

from flask import current_app

PUBLIC_LINKS = (
    ("main.index", "Beranda"),
    ("jobs.index", "Lowongan"),
    ("insights.index", "Insight"),
)

USER_LINKS = (
    ("profile.index", "Profil"),
    ("profile.saved", "Tersimpan"),
    ("cv.index", "CV"),
    ("assistant.index", "Asisten"),
)

ADMIN_LINKS = (("admin.index", "Admin"),)

# Tautan pratinjau: hanya muncul saat PREVIEW_UI=true, karena endpoint-nya
# memang tidak terdaftar di produksi. Profil dan tersimpan pada Track A hidup
# di blueprint preview, bukan blueprint produksi (PRD-F03 §6).
PREVIEW_LINKS = (
    ("preview.jobs", "Lowongan"),
    ("preview.profile", "Profil"),
    ("preview.saved", "Tersimpan"),
    ("preview.cv", "CV"),
    ("preview.assistant", "Asisten"),
)

# Endpoint yang bukan menu, tetapi tetap milik sebuah menu. Halaman detail dan
# perusahaan tidak punya tautan sendiri di navpill, jadi tanpa peta ini keduanya
# tampil tanpa satu pun menu aktif.
PARENT = {
    "preview.job_detail": "preview.jobs",
    "preview.company_detail": "preview.jobs",
    "preview.home": "preview.jobs",
    "preview.index": "preview.jobs",
    "preview.styleguide": "preview.jobs",
    "jobs.detail": "jobs.index",
    "insights.detail": "insights.index",
}


def _available(links) -> list[dict[str, str]]:
    endpoints = current_app.view_functions
    return [{"endpoint": endpoint, "label": label} for endpoint, label in links if endpoint in endpoints]


def nav_links() -> list[dict[str, str]]:
    """Tautan navigasi sesuai peran; admin melihat tautan tambahan (R-06-10).

    ``active`` dihitung di sini, bukan di template. Dua aturan:
    1. Endpoint halaman anak menyorot menunya lewat ``PARENT`` — halaman detail
       dan perusahaan tidak punya tautan sendiri.
    2. Kecocokan nama blueprint hanya dipakai bila satu blueprint punya SATU
       menu. Ketiga menu pratinjau semuanya milik ``preview``, jadi aturan
       longgar akan menyalakan ketiganya sekaligus.
    """
    links = _available(PUBLIC_LINKS)

    from flask import request
    from flask_login import current_user

    if "preview.styleguide" in current_app.view_functions:
        links = _available(PREVIEW_LINKS)

    if current_user.is_authenticated:
        links.extend(_available(USER_LINKS))
        if getattr(current_user, "is_admin", False):
            links.extend(_available(ADMIN_LINKS))

    endpoint = request.endpoint or ""
    target = PARENT.get(endpoint, endpoint)
    akar = target.split(".")[0]

    dari_akar: dict[str, int] = {}
    for link in links:
        blok = link["endpoint"].split(".")[0]
        dari_akar[blok] = dari_akar.get(blok, 0) + 1

    for link in links:
        blok = link["endpoint"].split(".")[0]
        if target == link["endpoint"]:
            link["active"] = True
        elif blok == akar and dari_akar.get(blok, 0) == 1:
            link["active"] = True
        else:
            link["active"] = False

    return links
