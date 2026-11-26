"""PRD-10 §7.1: pemeriksaan akhir rilis.

Test ini menjaga **janji produk**, bukan perilaku satu fungsi. Masing-masing
memeriksa satu constraint yang bila bocor akan merusak kepercayaan pengguna
atau membocorkan data pribadi:

- R-10-11: tidak ada tracker lamaran atau status lamaran.
- R-10-12: berkas dan teks CV tidak tersimpan dan tidak di-log.
- R-10-13: ambang lima sampel gaji berlaku di web maupun API.
- R-10-06: cookie sesi produksi aman.
- R-10-17: blueprint preview tidak aktif bila flag mati.
- R-10-04: tidak ada secret di repository.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import create_app
from app.config import CONFIG_MAP

ROOT = Path(__file__).resolve().parents[2]


# --- R-10-11: tidak ada tracker lamaran ----------------------------------

def test_no_application_tracker() -> None:
    """Tidak ada route, tabel, atau kolom untuk status lamaran (R-10-11).

    Ini batasan produk yang disengaja (PRD §11.2): KarirLens mengumpulkan
    lowongan, bukan mengelola lamaran. Kalau suatu saat "status" muncul di
    route atau migrasi, berarti lingkup produk melebar tanpa keputusan.
    """
    jalur = {rule.rule for rule in create_app("testing").url_map.iter_rules()}
    for path in jalur:
        for terlarang in ("/applications", "/lamaran", "/status-lamar"):
            assert terlarang not in path, f"route tracker lamaran: {path}"

    migrasi = " ".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "migrations").glob("*.sql")
    ).lower()
    assert "create table if not exists applications" not in migrasi
    assert "status_lamaran" not in migrasi


def test_no_application_status_in_services() -> None:
    """Tidak ada modul yang menyimpan status lamaran."""
    for path in (ROOT / "app").rglob("*.py"):
        isi = path.read_text(encoding="utf-8").lower()
        for terlarang in ("applied_at", "application_status", "status_lamaran"):
            assert terlarang not in isi, f"{path} memuat {terlarang}"


# --- R-10-12: CV tidak tersimpan dan tidak di-log ------------------------

def test_no_cv_persistence() -> None:
    """Tidak ada kolom atau tabel untuk berkas/teks CV (R-10-12)."""
    migrasi = " ".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "migrations").glob("*.sql")
    ).lower()

    for terlarang in ("cv_text", "cv_file", "resume_text", "cv_path"):
        assert terlarang not in migrasi, f"skema memuat {terlarang}"

    # `user_skills` hanya menyimpan nama skill — itu yang memang boleh ada.
    assert "create table if not exists user_skills" in migrasi


def test_cv_text_never_logged() -> None:
    """Modul CV tidak mencatat isi teks CV ke log (R-10-12, R-10-15)."""
    for nama in ("extractor.py", "service.py", "routes.py"):
        sumber = (ROOT / "app" / "cv" / nama).read_text(encoding="utf-8")
        for baris in sumber.splitlines():
            if "logger." in baris or "logging." in baris:
                assert "text" not in baris.lower() or "type(" in baris, (
                    f"{nama} mencatat isi CV: {baris.strip()}"
                )


def test_temp_upload_is_deleted() -> None:
    """Berkas sementara CV dihapus di `finally`, termasuk saat gagal (R-10-12)."""
    sumber = (ROOT / "app" / "cv" / "service.py").read_text(encoding="utf-8")
    assert "mkstemp" in sumber, "berkas sementara harus memakai nama unik"
    assert "finally" in sumber, "penghapusan berkas harus di finally"
    assert "os.unlink" in sumber, "berkas sementara harus benar-benar dihapus"


# --- R-10-13: ambang sampel gaji di semua permukaan ---------------------

def test_salary_threshold_all_surfaces(monkeypatch) -> None:
    """Web dan API memakai ambang yang sama dan tidak menampilkannya bila < 5."""
    from app.insights import repository as insights_repo
    from app.insights import service as insights_service

    # Tiga lowongan bergaji: cukup untuk data, tidak cukup untuk statistik.
    baris = [
        {"salary_min": 9_000_000, "salary_max": 12_000_000,
         "salary_currency": "IDR", "salary_period": "month"}
        for _ in range(3)
    ]
    monkeypatch.setattr(insights_repo, "find_jobs_with_salary", lambda *a, **k: baris)

    data = insights_service.get_salary_stats()

    assert data["sample_sufficient"] is False
    assert data["groups"] == [], "grup dengan 3 sampel tidak boleh ditampilkan"
    assert data["minimum_sample"] == 5


def test_api_salary_threshold_matches_web(monkeypatch) -> None:
    """API tidak memberi jalan pintas di bawah ambang (R-10-13)."""
    from app.insights import repository as insights_repo

    baris = [
        {"salary_min": 9_000_000, "salary_max": 12_000_000,
         "salary_currency": "IDR", "salary_period": "month"}
        for _ in range(4)
    ]
    monkeypatch.setattr(insights_repo, "find_jobs_with_salary", lambda *a, **k: baris)

    app = create_app("testing")
    app.config.update(TESTING=True)
    body = app.test_client().get("/api/insights/salary").get_json()

    assert body["data"]["sample_sufficient"] is False
    assert body["data"]["groups"] == []


# --- R-10-06: cookie sesi produksi --------------------------------------

def test_secure_cookie_production() -> None:
    """Produksi memakai Secure, HttpOnly, dan SameSite (R-10-06)."""
    produksi = CONFIG_MAP["production"]

    assert produksi.SESSION_COOKIE_SECURE is True, "cookie harus Secure"
    assert produksi.SESSION_COOKIE_HTTPONLY is True, "cookie harus HttpOnly"
    assert produksi.SESSION_COOKIE_SAMESITE in ("Lax", "Strict")

    # Pengembangan tidak boleh memaksa Secure: `flask run` memakai http dan
    # browser akan membuang cookie-nya.
    assert CONFIG_MAP["testing"].SESSION_COOKIE_SECURE is False


# --- R-10-17: preview tidak aktif di produksi ---------------------------

def test_preview_off_when_flag_unset() -> None:
    """Blueprint preview tidak terdaftar bila PREVIEW_UI mati (R-10-17)."""
    config = type(
        "TanpaPreview", (CONFIG_MAP["testing"],), {"PREVIEW_UI": False}
    )
    CONFIG_MAP["prd10_preview_off"] = config
    app = create_app("prd10_preview_off")

    assert "preview.styleguide" not in app.view_functions
    assert app.test_client().get("/preview/").status_code == 404


# --- R-10-04: tidak ada secret di repository ---------------------------

def test_no_secrets_committed() -> None:
    """Tidak ada kunci asli yang tertulis di berkas yang di-commit (R-10-04)."""
    pola = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),          # DeepSeek
        re.compile(r"sb_publishable_[A-Za-z0-9_-]{20,}"),
        re.compile(r"eyJ[A-Za-z0-9_-]{30,}"),        # JWT anon lama
    ]

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".md", ".yml", ".yaml", ".ini", ".toml"}:
            continue
        if any(bagian in path.parts for bagian in ("venv", ".git", "node_modules")):
            continue
        isi = path.read_text(encoding="utf-8", errors="ignore")
        for p in pola:
            temuan = p.search(isi)
            assert not temuan, f"{path.relative_to(ROOT)} memuat secret: {temuan.group()[:12]}..."


def test_env_not_tracked() -> None:
    """`.env` di-ignore; `.env.example` hanya berisi placeholder, bukan kunci asli."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in ignore

    # Placeholder seperti "ganti-dengan-string-acak-panjang" memang disengaja:
    # ia memberi tahu apa yang harus diisi tanpa memberi nilai yang bisa dipakai.
    contoh = (ROOT / ".env.example").read_text(encoding="utf-8")
    for tempat in ("ganti-dengan", "contoh", "example"):
        if tempat in contoh:
            break
    else:
        pytest.fail(".env.example tidak memuat placeholder yang jelas")

    # Yang benar-benar dilarang: nilai yang bentuknya kunci sungguhan.
    for p in (re.compile(r"sk-[A-Za-z0-9]{20,}"), re.compile(r"sb_publishable_[A-Za-z0-9_-]{20,}")):
        assert not p.search(contoh), ".env.example memuat kunci asli"
