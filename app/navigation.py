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

# Penjelajahan publik pada Track A.
#
# Yang TIDAK ada di sini:
#   - Profil. Profil adalah halaman akun, bukan bagian penjelajahan. Ia tinggal
#     di menu pengguna pada pojok kanan atas setelah masuk.
#   - Asisten. Hanya ada SATU pintu masuk AI (design system §6: "dua pintu masuk
#     AI dengan nama berbeda" dilarang). Pintunya tombol "Asisten AI" di header.
PREVIEW_LINKS = (
    ("preview.jobs", "Lowongan"),
    ("preview.insights", "Insight"),
)

# Tautan yang hanya masuk akal setelah pengguna punya akun. Tamu tidak melihat
# "Tersimpan", "CV", atau "Admin" — sebelumnya ketiganya ikut tampil karena
# seluruh daftar pratinjau dipasang tanpa memandang status sesi.
#
# "Admin" sengaja di sini tanpa memeriksa peran: pada Track A belum ada kolom
# `users.role`, jadi seluruh pengguna pratinjau memang melihatnya. PRD-09 yang
# menambahkan pengecekan peran sungguhan.
PREVIEW_USER_LINKS = (
    ("preview.saved", "Tersimpan"),
    ("preview.cv", "CV"),
    ("preview.admin_index", "Admin"),
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
    "preview.admin_index": "preview.admin_index",
    "preview.admin_jobs": "preview.admin_index",
    "preview.admin_users": "preview.admin_index",
    "preview.admin_runs": "preview.admin_index",
    "preview.admin_clusters": "preview.admin_index",
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

    pratinjau = "preview.styleguide" in current_app.view_functions
    if pratinjau:
        links = _available(PREVIEW_LINKS)

    if current_user.is_authenticated:
        if pratinjau:
            # Daftar pratinjau sudah memuat Admin; jangan ditambah lagi.
            links.extend(_available(PREVIEW_USER_LINKS))
        else:
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


def _href(kandidat: tuple[str, ...]) -> str | None:
    """URL endpoint pertama yang benar-benar terdaftar, atau None.

    Track A dan Track B memakai nama endpoint berbeda untuk halaman yang sama
    (``preview.profile`` vs ``profile.index``). Memanggil ``url_for`` untuk
    endpoint yang tidak ada akan melempar BuildError, jadi kandidat disaring
    terhadap ``app.view_functions`` lebih dulu.
    """
    from flask import url_for

    for endpoint in kandidat:
        if endpoint in current_app.view_functions:
            return url_for(endpoint)
    return None


def saved_count() -> int:
    """Jumlah bookmark pengguna login, untuk indikator di navigasi (PRD-06).

    Dihitung hanya bila pengguna login: tamu tidak punya bookmark, dan
    menampilkan "0" pada menu yang tidak mereka miliki hanya menambah derau.
    Kegagalan query tidak boleh menggagalkan render — navigasi adalah hiasan,
    bukan isi halaman.
    """
    from flask_login import current_user

    if not getattr(current_user, "is_authenticated", False):
        return 0

    try:
        from app.profile import repository as profile_repository

        return profile_repository.count_saved(current_user.id)
    except Exception:  # noqa: BLE001 - navigasi tidak boleh mematahkan halaman
        return 0


def header_hrefs() -> dict[str, str | None]:
    """URL untuk menu header: AI, profil, tersimpan, CV, dan admin.

    Dihitung di sini agar template tidak perlu tahu blueprint mana yang aktif.
    """
    return {
        "ai_href": _href(("preview.assistant", "assistant.index")),
        "profile_href": _href(("preview.profile", "profile.index")),
        "saved_href": _href(("preview.saved", "profile.saved")),
        "cv_href": _href(("preview.cv", "cv.index")),
        "admin_href": _href(("preview.admin_index", "admin.index")),
        "saved_count": saved_count(),
    }
