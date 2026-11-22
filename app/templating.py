"""Jembatan nama endpoint untuk template yang dipakai dua track.

Template katalog ditulis pada PRD-F02 dan menautkan ke endpoint pratinjau
(``preview.jobs``, ``preview.job_detail``, ``preview.company_detail``). Sejak
PRD-04 halaman yang sama juga dirender oleh route produksi, sementara blueprint
``preview`` hanya terdaftar ketika ``PREVIEW_UI=true``.

R-04-11 mewajibkan template katalog tidak berubah, jadi nama endpoint itu tidak
boleh diganti di template. Modul ini menerjemahkannya satu kali di lapisan
Jinja: endpoint pratinjau yang tidak terdaftar dipetakan ke padanan produksinya.
Endpoint lain dibiarkan gagal seperti biasa, supaya salah ketik tetap terlihat
alih-alih diam-diam menghasilkan URL salah.
"""

from __future__ import annotations

from flask import Flask, url_for

# Pemetaan dua arah: nama endpoint pratinjau -> padanan produksinya, dan
# sebaliknya. Arah balik diperlukan karena template ditulis pada salah satu
# track dan dirender oleh keduanya. Tanpa itu, halaman pratinjau yang memakai
# `url_for('profile.saved')` akan menaut ke route produksi (`/saved`) padahal
# yang dilihat penggguna adalah fixture `/preview/saved`.
ALIASES = {
    "preview.jobs": "jobs.index",
    "preview.job_detail": "jobs.detail",
    "preview.company_detail": "insights.company",
    "preview.home": "main.index",
    "preview.insights": "insights.index",
    # Profil dan tersimpan kini punya route produksi (PRD-06).
    "preview.profile": "profile.index",
    "preview.saved": "profile.saved",
    # CV punya route produksi sejak PRD-07.
    "preview.cv": "cv.index",
    # Asisten punya route produksi sejak PRD-08.
    "preview.assistant": "assistant.index",
}

# Kebalikannya, dibangun sekali dari ALIASES.
_BALIK = {produksi: pratinjau for pratinjau, produksi in ALIASES.items()}


def install(app: Flask) -> None:
    """Pasang penerjemah endpoint pada lingkungan Jinja aplikasi."""
    bawaan = app.jinja_env.globals.get("url_for", url_for)

    def _terdaftar(endpoint: str) -> bool:
        return endpoint in app.view_functions

    def url_for_kompatibel(endpoint: str, **nilai):
        """Tautan mengikuti halaman yang sedang dirender, bukan flag.

        Saat pratinjau aktif keduanya terdaftar. Memilih berdasarkan endpoint
        yang sedang dirender mencegah halaman produksi menautkan ke
        ``/preview/...`` dan sebaliknya — dua track yang tautannya bercampur
        membuat pengguna berpindah ke data fixture tanpa sadar.
        """
        from flask import has_request_context, request

        sedang_pratinjau = (
            has_request_context() and (request.endpoint or "").startswith("preview.")
        )
        if sedang_pratinjau:
            # Halaman pratinjau: pakai endpoint pratinjau bila ada.
            kandidat = [_BALIK.get(endpoint, endpoint), endpoint]
        else:
            # Halaman produksi: pakai padanan produksi bila ada.
            kandidat = [ALIASES.get(endpoint, endpoint), endpoint]

        for nama in kandidat:
            if _terdaftar(nama):
                return bawaan(nama, **nilai)
        return bawaan(endpoint, **nilai)

    app.jinja_env.globals["url_for"] = url_for_kompatibel
