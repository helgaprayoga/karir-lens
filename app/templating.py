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

# Hanya halaman yang sudah punya backend produksi (PRD-04). Halaman pratinjau
# lain (profil, CV, asisten, admin) belum punya padanan dan tidak dipetakan.
ALIASES = {
    "preview.jobs": "jobs.index",
    "preview.job_detail": "jobs.detail",
    "preview.company_detail": "insights.company",
    "preview.home": "main.index",
}


def install(app: Flask) -> None:
    """Pasang penerjemah endpoint pada lingkungan Jinja aplikasi."""
    bawaan = app.jinja_env.globals.get("url_for", url_for)

    def _terdaftar(endpoint: str) -> bool:
        return endpoint in app.view_functions

    def url_for_kompatibel(endpoint: str, **nilai):
        """Tautan mengikuti halaman yang sedang dirender, bukan flag.

        Saat pratinjau aktif keduanya terdaftar, dan memilih berdasarkan
        endpoint yang sedang dirender mencegah halaman produksi menautkan ke
        ``/preview/...`` (atau sebaliknya).
        """
        from flask import has_request_context, request

        sedang_pratinjau = (
            has_request_context() and (request.endpoint or "").startswith("preview.")
        )
        pengganti = ALIASES.get(endpoint)

        urutan = [endpoint]
        if pengganti and _terdaftar(pengganti):
            urutan = [pengganti, endpoint] if not sedang_pratinjau else [endpoint, pengganti]

        for kandidat in urutan:
            if _terdaftar(kandidat):
                return bawaan(kandidat, **nilai)
        return bawaan(endpoint, **nilai)

    app.jinja_env.globals["url_for"] = url_for_kompatibel
