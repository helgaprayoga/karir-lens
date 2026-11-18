"""Blueprint katalog publik: cari, filter, detail lowongan (PRD-04)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("jobs", __name__, url_prefix="/jobs")

from . import routes  # noqa: E402,F401
