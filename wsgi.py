"""Entry point WSGI untuk Render (PRD-10) dan ``flask run``.

Pemakaian lokal:
    flask --app wsgi run

Pemakaian produksi (Render, lewat ``Procfile``):
    gunicorn wsgi:app
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (setelah .env dimuat)

# **Bawaannya ``production``, bukan ``development``.**
#
# Sebelumnya baris ini memakai ``development`` sebagai bawaan, sehingga lupa
# mengisi ``FLASK_ENV`` di Render berarti aplikasi berjalan dengan ``DEBUG=True``:
# traceback lengkap — nilai variabel, path berkas, potongan kode — terbuka ke
# publik pada setiap galat. Default yang aman tidak boleh bergantung pada ingatan
# orang.
#
# ``development`` kini harus diminta secara eksplisit saat pengembangan lokal.
app = create_app(os.environ.get("FLASK_ENV", "production"))
