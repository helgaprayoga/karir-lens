"""Blueprint beranda (PRD-04)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("main", __name__)

from . import routes  # noqa: E402,F401  (registrasi route)
