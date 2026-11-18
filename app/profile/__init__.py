"""Blueprint profil: skill terkonfirmasi dan lowongan tersimpan (PRD-06)."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("profile", __name__)

from . import routes  # noqa: E402,F401
