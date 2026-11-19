"""Autentikasi: registrasi, login, logout, CSRF, dan cookie sesi
(R-01-09, R-01-10, R-01-11, R-01-13).

Repository diganti penyimpanan in-memory agar test tidak menyentuh Supabase.
Lapisan yang diuji: ``service`` dan ``routes``. Repository sendiri tipis dan
diuji sebagai integration test bila kredensial tersedia.
"""

from __future__ import annotations

import pytest
from werkzeug.security import check_password_hash

from app.auth import repository, service


@pytest.fixture
def users(monkeypatch):
    """Tabel ``users`` in-memory dengan kolom yang sama seperti skema."""
    store: dict[str, dict] = {}
    state = {"next_id": 1}

    def find_by_email(email, *, with_password=False):
        row = store.get(email)
        if row is None:
            return None
        return dict(row) if with_password else {k: row[k] for k in ("id", "email", "name")}

    def find_by_id(user_id):
        for row in store.values():
            if row["id"] == user_id:
                return {k: row[k] for k in ("id", "email", "name")}
        return None

    def create(email, password_hash, name=None):
        row = {"id": state["next_id"], "email": email, "password_hash": password_hash, "name": name}
        state["next_id"] += 1
        store[email] = row
        return {"id": row["id"], "email": row["email"], "name": row["name"]}

    monkeypatch.setattr(repository, "find_by_email", find_by_email)
    monkeypatch.setattr(repository, "find_by_id", find_by_id)
    monkeypatch.setattr(repository, "create", create)

    return store


# --- Service ---------------------------------------------------------------

def test_register_hashes_password(users) -> None:
    """Password tersimpan sebagai hash, bukan teks asli (R-01-09)."""
    service.register("Budi@Example.com ", "rahasia123")

    stored = users["budi@example.com"]
    assert stored["password_hash"] != "rahasia123"
    assert check_password_hash(stored["password_hash"], "rahasia123")


def test_register_normalizes_email(users) -> None:
    service.register("  Budi@Example.COM ", "rahasia123")
    assert list(users) == ["budi@example.com"]


def test_register_rejects_duplicate_email(users) -> None:
    service.register("budi@example.com", "rahasia123")

    with pytest.raises(Exception) as caught:
        service.register("BUDI@example.com", "rahasia456")

    assert "sudah terdaftar" in str(caught.value)
    assert len(users) == 1


def test_register_rejects_short_password(users) -> None:
    with pytest.raises(Exception) as caught:
        service.register("budi@example.com", "pendek")

    assert "minimal 8 karakter" in str(caught.value)
    assert users == {}


def test_register_rejects_invalid_email(users) -> None:
    with pytest.raises(Exception):
        service.register("bukan-email", "rahasia123")


def test_authenticate_valid_and_invalid(users) -> None:
    service.register("budi@example.com", "rahasia123")

    assert service.authenticate("budi@example.com", "rahasia123") is not None
    assert service.authenticate("budi@example.com", "salah") is None
    assert service.authenticate("tidak@ada.com", "rahasia123") is None


def test_user_object_never_carries_password_hash(users) -> None:
    """Objek yang disimpan di sesi tidak boleh memuat hash password."""
    service.register("budi@example.com", "rahasia123")

    user = service.authenticate("budi@example.com", "rahasia123")

    assert user is not None
    assert not hasattr(user, "password_hash")


# --- Route -----------------------------------------------------------------

def test_register_flow_logs_user_in(app, client, users) -> None:
    response = client.post(
        "/auth/register",
        data={"email": "budi@example.com", "password": "rahasia123", "name": "Budi"},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Budi" in body          # nama tampil di header
    assert "Keluar" in body        # sesi aktif
    assert "budi@example.com" in users


def test_logout_clears_session(app, client, users) -> None:
    client.post("/auth/register", data={"email": "budi@example.com", "password": "rahasia123"})
    assert "Keluar" in client.get("/").get_data(as_text=True)

    response = client.post("/auth/logout", follow_redirects=True)

    assert response.status_code == 200
    assert "Keluar" not in response.get_data(as_text=True)
    assert "Masuk" in response.get_data(as_text=True)


def test_login_rejects_wrong_password(app, client, users) -> None:
    client.post("/auth/register", data={"email": "budi@example.com", "password": "rahasia123"})
    client.post("/auth/logout")

    response = client.post(
        "/auth/login",
        data={"email": "budi@example.com", "password": "salah"},
        follow_redirects=True,
    )

    assert response.status_code == 401
    assert "Email atau password salah" in response.get_data(as_text=True)


def test_logout_requires_csrf(users) -> None:
    """POST tanpa token CSRF ditolak (R-01-11)."""
    from app import create_app

    csrf_app = create_app("testing")
    csrf_app.config.update(WTF_CSRF_ENABLED=True)

    with csrf_app.test_client() as client:
        client.post("/auth/register", data={"email": "budi@example.com", "password": "rahasia123"})
        response = client.post("/auth/logout")

    assert response.status_code == 400


def test_session_cookie_flags(app, client, users) -> None:
    """Cookie sesi memakai HttpOnly dan SameSite (R-01-10)."""
    response = client.post("/auth/register", data={"email": "budi@example.com", "password": "rahasia123"})

    cookies = response.headers.getlist("Set-Cookie")
    session_cookie = next((cookie for cookie in cookies if "session=" in cookie), "")

    assert "HttpOnly" in session_cookie
    assert "SameSite=Lax" in session_cookie.replace(" ", "")


def test_production_config_marks_cookie_secure() -> None:
    """``Secure`` aktif pada konfigurasi produksi (R-01-10)."""
    from app.config import ProductionConfig

    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Lax"


def test_password_never_logged(app, client, users, caplog) -> None:
    """Log tidak memuat password mentah (R-01-13)."""
    with caplog.at_level("DEBUG"):
        client.post("/auth/register", data={"email": "budi@example.com", "password": "rahasia123"})

    assert "rahasia123" not in caplog.text
