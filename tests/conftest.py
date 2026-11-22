"""Fixture bersama untuk seluruh pengujian.

Kredensial Supabase dan DeepSeek diganti stub, sehingga test tidak menyentuh
jaringan (R-08-13, PRD-02 §7.1). Sejak PRD-04 beranda dan katalog membaca
database, `get_db()` juga diganti klien kosong: halaman tetap dapat dirender
tanpa satu paket pun keluar dari mesin ini.
"""

from __future__ import annotations

import pytest

from app import create_app


class _EmptyResult:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class _EmptyQuery:
    """Klien PostgREST yang selalu kosong dan mengembalikan rantai yang sama."""

    def __getattr__(self, _nama):
        def apa_saja(*_args, **_kwargs):
            return self

        return apa_saja

    def execute(self):
        return _EmptyResult()


class _EmptyDB:
    def table(self, _nama):
        return _EmptyQuery()


@pytest.fixture(autouse=True)
def empty_database(monkeypatch):
    """Ganti `core.db.get_db` dengan klien kosong untuk semua test.

    Autouse karena route publik (`/`, `/jobs`, `/companies/<slug>`) kini
    membaca database; tanpa ini setiap test yang menyentuh halaman publik akan
    mencoba menghubungi `http://localhost:54321`.

    Test yang ingin data sungguhan mengganti `_client` repository-nya sendiri,
    sehingga tetap menang atas fixture ini.
    """
    from core import db as core_db

    monkeypatch.setattr(core_db, "get_db", lambda: _EmptyDB())
    return _EmptyDB()


@pytest.fixture
def app():
    application = create_app("testing")
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
