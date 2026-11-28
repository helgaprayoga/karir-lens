"""Uji entry point produksi: default aman dan dapat diimpor gunicorn."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Kredensial palsu untuk subprocess. `wsgi` memakai konfigurasi **production**
# yang memang menolak start tanpa SECRET_KEY/SUPABASE_*, dan perilaku itu benar.
# Tanpa nilai ini, test hanya lulus di mesin yang punya `.env` dan gagal di CI —
# persis yang terjadi: tiga test hijau lokal, merah di runner.
#
# Nilainya sengaja bukan bentuk kunci asli, dan `load_dotenv()` tidak menimpa
# variabel yang sudah ada di environment, jadi `.env` lokal tidak berpengaruh.
KREDENSIAL_UJI = {
    "SECRET_KEY": "uji-bukan-secret-key-asli-0123456789abcdef",
    "SUPABASE_URL": "https://uji.supabase.co",
    "SUPABASE_KEY": "uji-bukan-kunci-asli",
}


def _jalankan(kode: str, env: dict | None = None) -> tuple[int, str]:
    """Jalankan potongan Python di proses baru, dengan cwd root proyek."""
    lingkungan = {**os.environ, "PYTHONIOENCODING": "utf-8", **KREDENSIAL_UJI}
    lingkungan.pop("FLASK_ENV", None)
    lingkungan.update(env or {})
    hasil = subprocess.run(
        [sys.executable, "-c", kode],
        cwd=ROOT, capture_output=True, text=True, env=lingkungan, timeout=120,
    )
    return hasil.returncode, (hasil.stdout + hasil.stderr).strip()


def test_wsgi_defaults_to_production() -> None:
    """Tanpa `FLASK_ENV`, aplikasi berjalan sebagai production.

    Sebelumnya bawaannya `development`, sehingga lupa mengisi `FLASK_ENV` di
    Render berarti `DEBUG=True`: traceback lengkap terbuka ke publik pada setiap
    galat. Test ini menjaga bawaannya tetap aman.
    """
    kode, keluaran = _jalankan(
        "import wsgi; print(wsgi.app.config.get('DEBUG'));"
        "print(wsgi.app.config.get('SESSION_COOKIE_SECURE'))"
    )
    assert kode == 0, keluaran

    baris = keluaran.splitlines()
    assert baris[-2] == "False", f"DEBUG harus mati, dapat {baris[-2]}"


def test_wsgi_can_be_imported_by_gunicorn() -> None:
    """`gunicorn wsgi:app` hanya butuh modul `wsgi` dan atribut `app`."""
    kode, keluaran = _jalankan(
        "import wsgi;"
        "assert callable(wsgi.app), 'app bukan WSGI callable';"
        "print(type(wsgi.app).__name__)"
    )
    assert kode == 0, keluaran


def test_wsgi_honours_explicit_flask_env() -> None:
    """`FLASK_ENV=development` tetap dihormati saat pengembangan lokal."""
    kode, keluaran = _jalankan(
        "import wsgi; print(wsgi.app.config.get('DEBUG'))",
        {"FLASK_ENV": "development"},
    )
    assert kode == 0, keluaran
    assert keluaran.splitlines()[-1] == "True"


def test_deploy_files_exist() -> None:
    """Berkas yang dibutuhkan Render ada dan tidak kosong."""
    for nama in ("Procfile", ".python-version"):
        berkas = ROOT / nama
        assert berkas.is_file(), f"{nama} tidak ada"
        assert berkas.read_text(encoding="utf-8").strip(), f"{nama} kosong"

    procfile = (ROOT / "Procfile").read_text(encoding="utf-8")
    assert procfile.startswith("web: gunicorn wsgi:app"), procfile
    assert "$PORT" in procfile, "Render memberi port lewat $PORT"


def test_gunicorn_is_declared() -> None:
    """`gunicorn` ada di requirements, karena Procfile memanggilnya."""
    isi = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in isi.lower()


def test_healthz_responds_without_login() -> None:
    """`/healthz` mengembalikan 200 tanpa sesi.

    Render memanggil health check tanpa cookie apa pun. Bila route ini memakai
    `login_required`, deploy akan ditandai tidak sehat lalu di-restart terus
    menerus.
    """
    from app import create_app

    r = create_app("testing").test_client().get("/healthz")

    assert r.status_code == 200, f"/healthz -> {r.status_code}"
    assert r.get_json() == {"status": "ok"}


def test_healthz_touches_no_database() -> None:
    """Health check tidak boleh bergantung pada Supabase.

    Diperiksa dari sumber fungsinya: bila kelak ada yang menambahkan query di
    sana, gangguan sesaat pada database akan menjatuhkan seluruh service.
    """
    import inspect

    from app.main import routes

    sumber = inspect.getsource(routes.healthz)
    for dilarang in ("get_db", "repository", "supabase"):
        assert dilarang not in sumber, f"healthz memuat {dilarang!r}"


def test_scrape_workflow_exists() -> None:
    """Workflow cron ada, memakai `--detail`, dan menjalankan clustering."""
    jalur = ROOT / ".github" / "workflows" / "scrape.yml"
    assert jalur.is_file(), "workflow scraping belum dibuat"

    isi = jalur.read_text(encoding="utf-8")
    assert "cron:" in isi
    # `--detail` bawaannya mati; tanpa flag ini deskripsi dan skill tidak
    # pernah diperbarui, dan statusnya tetap `success` sehingga tidak ada yang
    # memberi tahu.
    assert "--detail" in isi, "workflow harus memakai --detail"
    assert "scraper cluster" in isi, "cluster harus dibentuk ulang setelah scrape"
