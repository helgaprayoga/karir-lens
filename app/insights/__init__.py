"""Blueprint insight: kategori, skill, gaji, halaman perusahaan (PRD-05)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("insights", __name__)

from . import routes  # noqa: E402,F401
