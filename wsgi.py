"""Entry point WSGI untuk Render (PRD-10) dan ``flask run``.

``flask --app wsgi run`` saat pengembangan lokal.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (setelah .env dimuat)

app = create_app(os.environ.get("FLASK_ENV", "development"))
