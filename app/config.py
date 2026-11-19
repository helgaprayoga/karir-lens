"""Konfigurasi Flask per environment (R-01-03).

Nilai dibaca dari ``core.config.Settings`` agar aplikasi web dan pipeline data
memakai sumber konfigurasi yang sama.
"""

from __future__ import annotations

import logging

from core.config import Settings

_SAFE_COOKIE = {
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
}


class BaseConfig:
    SETTINGS: Settings = Settings.from_env()
    REQUIRE_CREDENTIALS = True
    LOG_LEVEL = logging.INFO
    MAX_CONTENT_LENGTH = SETTINGS.max_upload_bytes
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7
    SESSION_COOKIE_HTTPONLY = _SAFE_COOKIE["SESSION_COOKIE_HTTPONLY"]
    SESSION_COOKIE_SAMESITE = _SAFE_COOKIE["SESSION_COOKIE_SAMESITE"]
    SESSION_COOKIE_SECURE = SETTINGS.session_cookie_secure
    SECRET_KEY = SETTINGS.secret_key or "dev-secret-key-tidak-untuk-produksi"
    # Blueprint preview dan /styleguide hanya aktif bila diaktifkan eksplisit
    # (PRD-F01 R-F01-08, R-F01-09; PRD-10 R-10-17).
    PREVIEW_UI = SETTINGS.preview_ui


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    REQUIRE_CREDENTIALS = False
    SECRET_KEY = "testing-secret-key"
    WTF_CSRF_ENABLED = False
    PREVIEW_UI = False
    # Diperlukan agar url_for() dapat dipanggil di luar request context
    # (mis. saat macro pagination dirender langsung oleh test).
    SERVER_NAME = "localhost"
    SETTINGS = Settings(
        secret_key="testing-secret-key",
        supabase_url="http://localhost:54321",
        supabase_key="testing-key",
        deepseek_api_key=None,
        deepseek_model="deepseek-chat",
        scraper_user_agent="KarirLensBot-Test/1.0",
        scraper_max_retry=1,
        ai_daily_limit=100,
        cluster_n_clusters=3,
        cluster_pca_components=2,
        max_upload_bytes=5 * 1024 * 1024,
        session_cookie_secure=False,
        preview_ui=False,
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = logging.WARNING


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
