"""Blueprint REST API.

Adapter presentasi murni: tidak ada aturan bisnis dan tidak ada query di sini
(docs/ARCHITECTURE.md §4 aturan 7). Diisi pada PRD-09.
"""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("api", __name__, url_prefix="/api")

from . import routes  # noqa: E402,F401
