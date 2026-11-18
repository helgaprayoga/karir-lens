"""Kerangka aplikasi dapat dibuat dan seluruh blueprint terdaftar (R-01-02).

Menguji struktur, bukan fitur: memastikan ``create_app`` hidup dan sembilan
blueprint dari docs/ARCHITECTURE.md §6 sudah terpasang sebelum PRD-01 diisi.
"""

from __future__ import annotations

from app import create_app

EXPECTED_BLUEPRINTS = {
    "admin",
    "api",
    "assistant",
    "auth",
    "cv",
    "insights",
    "jobs",
    "main",
    "profile",
}


def test_create_app_registers_all_blueprints() -> None:
    application = create_app("testing")
    assert set(application.blueprints) == EXPECTED_BLUEPRINTS


def test_create_app_is_repeatable() -> None:
    """Application factory dapat dipanggil berkali-kali tanpa efek samping."""
    first = create_app("testing")
    second = create_app("testing")

    assert first is not second
    assert set(first.blueprints) == set(second.blueprints)
    assert first.config["TESTING"] is True


def test_testing_config_skips_credentials() -> None:
    """Konfigurasi testing tidak menuntut kredensial Supabase sungguhan (R-01-04)."""
    from app.config import TestingConfig

    assert TestingConfig.REQUIRE_CREDENTIALS is False
    assert TestingConfig.SETTINGS.problems(require_credentials=False) == []


def test_development_requires_credentials(monkeypatch) -> None:
    """Environment pengembangan tanpa kredensial harus berhenti dengan pesan jelas."""
    from core import config as core_config

    for name in ("SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        monkeypatch.delenv(name, raising=False)

    settings = core_config.Settings.from_env()
    problems = settings.problems()

    assert any("SECRET_KEY" in problem for problem in problems)
    assert any("SUPABASE_URL" in problem for problem in problems)


def test_error_page_is_friendly(client) -> None:
    """404 merender halaman ramah tanpa stack trace (R-01-12)."""
    response = client.get("/alamat-yang-tidak-ada")
    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert "tidak ditemukan" in body.lower()
    assert "Traceback" not in body


def test_api_error_is_json(client) -> None:
    """Route /api/ yang tidak ada mengembalikan format error JSON (R-09-13)."""
    response = client.get("/api/tidak-ada")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "message" in payload["error"]
