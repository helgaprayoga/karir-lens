"""Konfigurasi terpusat dari environment variable.

Modul ini adalah bagian shared kernel: tidak boleh mengimpor Flask, ``app``,
maupun ``scraper`` (docs/ARCHITECTURE.md §4, aturan 4).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_str(name: str, default: str | None = None) -> str | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"Environment variable {name} harus berupa bilangan bulat, bukan {raw!r}."
        ) from None


def _env_bool(name: str, default: bool) -> bool:
    raw = _env_str(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


DEFAULT_USER_AGENT = "KarirLensBot/1.0 (agregator lowongan; hubungi pemilik aplikasi)"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    """Nilai konfigurasi yang dapat berubah antar environment."""

    secret_key: str | None
    supabase_url: str | None
    supabase_key: str | None
    deepseek_api_key: str | None
    deepseek_model: str
    scraper_user_agent: str
    scraper_max_retry: int
    ai_daily_limit: int
    cluster_n_clusters: int
    cluster_pca_components: int
    max_upload_bytes: int
    session_cookie_secure: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=_env_str("SECRET_KEY"),
            supabase_url=_env_str("SUPABASE_URL"),
            supabase_key=_env_str("SUPABASE_KEY"),
            deepseek_api_key=_env_str("DEEPSEEK_API_KEY"),
            deepseek_model=_env_str("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL) or DEFAULT_DEEPSEEK_MODEL,
            scraper_user_agent=_env_str("SCRAPER_USER_AGENT", DEFAULT_USER_AGENT) or DEFAULT_USER_AGENT,
            scraper_max_retry=_env_int("SCRAPER_MAX_RETRY", 3),
            ai_daily_limit=_env_int("AI_DAILY_LIMIT", 20),
            cluster_n_clusters=_env_int("CLUSTER_N_CLUSTERS", 6),
            cluster_pca_components=_env_int("CLUSTER_PCA_COMPONENTS", 2),
            max_upload_bytes=_env_int("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES),
            session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
        )

    def problems(self, require_credentials: bool = True) -> list[str]:
        """Daftar masalah konfigurasi, kosong jika semuanya tersedia."""
        problems: list[str] = []
        if not self.secret_key:
            problems.append("SECRET_KEY belum diisi.")
        if require_credentials:
            if not self.supabase_url:
                problems.append("SUPABASE_URL belum diisi.")
            if not self.supabase_key:
                problems.append("SUPABASE_KEY belum diisi.")
        return problems


def validate_settings(settings: Settings | None = None, require_credentials: bool = True) -> None:
    """Berhenti dengan pesan jelas bila konfigurasi wajib belum tersedia (R-01-04)."""
    settings = settings or Settings.from_env()
    problems = settings.problems(require_credentials=require_credentials)
    if problems:
        raise RuntimeError(
            "Konfigurasi KarirLens belum lengkap:\n- " + "\n- ".join(problems)
        )
