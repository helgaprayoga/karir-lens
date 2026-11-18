"""Blueprint CV: upload, ekstraksi skill, konfirmasi, rekomendasi (PRD-07)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("cv", __name__, url_prefix="/cv")

from . import routes  # noqa: E402,F401
