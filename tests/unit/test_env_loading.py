"""``.env`` harus terbaca oleh setiap entrypoint non-web.

Bug yang dicegah: ``python -m db status`` melaporkan "belum dikonfigurasi"
padahal variabel sudah diisi di ``.env``, karena ``load_dotenv()`` hanya
dipanggil di ``wsgi.py``. Entrypoint CLI tidak melewati ``wsgi.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import config as core_config


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    """Berkas .env tiruan; bersihkan variabel terkait sebelum dan sesudah test."""
    names = ("SUPABASE_DB_HOST", "SUPABASE_DB_USER", "SUPABASE_DB_PASSWORD")
    for name in names:
        monkeypatch.delenv(name, raising=False)

    path = tmp_path / ".env"
    path.write_text(
        "SUPABASE_DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com\n"
        "SUPABASE_DB_USER=postgres.abcdefghijklm\n"
        "SUPABASE_DB_PASSWORD=rahasia-db\n",
        encoding="utf-8",
    )
    return path


def test_load_env_reads_file(env_file, monkeypatch) -> None:
    """Variabel dari .env harus masuk ke environment proses."""
    assert os.environ.get("SUPABASE_DB_HOST") is None

    assert core_config.load_env(env_file) is True

    assert os.environ["SUPABASE_DB_HOST"] == "aws-0-ap-southeast-1.pooler.supabase.com"
    assert os.environ["SUPABASE_DB_USER"] == "postgres.abcdefghijklm"


def test_load_env_enables_db_config(env_file) -> None:
    """Setelah .env dimuat, DatabaseConfig.from_env() tidak boleh gagal."""
    from core import db_direct

    core_config.load_env(env_file)
    config = db_direct.DatabaseConfig.from_env()

    assert config.user == "postgres.abcdefghijklm"
    assert config.port == 5432


def test_load_env_missing_file_is_not_fatal(tmp_path) -> None:
    assert core_config.load_env(tmp_path / "tidak-ada.env") is False


def test_load_env_does_not_override_shell(env_file, monkeypatch) -> None:
    """Nilai dari shell/CI menang atas berkas, seperti perilaku python-dotenv."""
    monkeypatch.setenv("SUPABASE_DB_HOST", "dari-shell")

    core_config.load_env(env_file)

    assert os.environ["SUPABASE_DB_HOST"] == "dari-shell"


def test_db_entrypoint_loads_env_at_import() -> None:
    """``python -m db`` harus memuat .env saat modul diimpor, bukan saat dijalankan.

    Diperiksa dari sumbernya karena memuat ulang modul akan menimpa monkeypatch
    dan tidak memberi sinyal yang jelas.
    """
    source = (core_config.PROJECT_ROOT / "db" / "__main__.py").read_text(encoding="utf-8")

    assert "load_env(" in source
    # Harus dipanggil di level modul, bukan di dalam fungsi.
    assert "core_config.load_env(ROOT" in source


def test_scraper_entrypoint_loads_env() -> None:
    source = (core_config.PROJECT_ROOT / "scraper" / "cli.py").read_text(encoding="utf-8")

    assert "core_config.load_env()" in source


def test_verify_script_loads_env() -> None:
    source = (core_config.PROJECT_ROOT / "scripts" / "verify_supabase.py").read_text(encoding="utf-8")

    assert "load_env(" in source


def test_error_message_mentions_env_file_location(monkeypatch, tmp_path) -> None:
    """Pesan gagal harus menyebut lokasi .env, bukan hanya nama variabel."""
    from core import db_direct

    for name in ("SUPABASE_DB_HOST", "SUPABASE_DB_USER", "SUPABASE_DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(core_config, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError) as caught:
        db_direct.DatabaseConfig.from_env()

    message = str(caught.value)
    assert "SUPABASE_DB_HOST" in message
    assert ".env" in message
    assert str(tmp_path) in message
