"""Fixture bersama untuk seluruh pengujian.

Kredensial Supabase dan DeepSeek diganti stub, sehingga test tidak menyentuh
jaringan (R-08-13, PRD-02 §7.1).
"""

from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app("testing")
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
