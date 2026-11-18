"""Route REST API.

Setiap route hanya membaca request, memanggil ``service`` modul terkait, lalu
membungkus hasilnya lewat ``response``. Diisi pada PRD-09.
"""

from __future__ import annotations

from . import bp
