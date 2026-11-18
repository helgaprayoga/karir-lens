"""Satu client Supabase untuk seluruh aplikasi (R-01-05).

Hanya ``repository.py`` (di setiap modul) dan ``scraper/pipeline/persist.py``
yang boleh mengimpor modul ini. ``service.py`` dan ``routes.py`` tidak boleh.

Import ``supabase`` dilakukan di dalam ``get_db()`` agar aplikasi dan test dapat
berjalan tanpa memasang atau menghubungi Supabase selama client belum dipakai.
"""

from __future__ import annotations

from typing import Any

_credentials: dict[str, str | None] = {"url": None, "key": None}
_client: Any | None = None


def configure(url: str | None, key: str | None) -> None:
    """Simpan kredensial. Client dibuat lazy pada pemanggilan ``get_db()`` pertama."""
    global _client
    if (url, key) != (_credentials["url"], _credentials["key"]):
        _client = None
    _credentials["url"] = url
    _credentials["key"] = key


def get_db() -> Any:
    """Kembalikan client Supabase, membuatnya sekali bila belum ada."""
    global _client
    if _client is None:
        url, key = _credentials["url"], _credentials["key"]
        if not url or not key:
            raise RuntimeError(
                "Koneksi Supabase belum dikonfigurasi. Isi SUPABASE_URL dan SUPABASE_KEY."
            )
        from supabase import create_client

        _client = create_client(url, key)
    return _client


def set_db(client: Any) -> None:
    """Injeksi client pengganti untuk pengujian."""
    global _client
    _client = client


def reset_db() -> None:
    """Lupakan client aktif. Dipakai di fixture test agar tidak bocor antar test."""
    global _client
    _client = None
    _credentials["url"] = None
    _credentials["key"] = None
