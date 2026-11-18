"""Blueprint asisten AI (PRD-08)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("assistant", __name__, url_prefix="/assistant")

from . import routes  # noqa: E402,F401
