"""Route autentikasi.

Lapisan HTTP saja. Aturan validasi dan hashing password tinggal di ``service``.
Diisi pada PRD-01.
"""

from __future__ import annotations

from . import bp
