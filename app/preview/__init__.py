"""Blueprint preview: merender template produksi dengan data contoh.

Hanya diregistrasi ketika ``PREVIEW_UI=true`` (R-F01-09), sehingga tidak pernah
aktif di produksi (PRD-10 R-10-17).

Aturan arsitektur 8 (docs/ARCHITECTURE.md §4): blueprint ini **hanya** membaca
``tests/fixtures/ui/*.json`` dan merender template. Ia tidak boleh mengimpor
``repository``, ``supabase``, maupun memanggil ``service`` produksi.
"""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("preview", __name__, url_prefix="/preview")

from . import routes  # noqa: E402,F401
