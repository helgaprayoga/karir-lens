"""Penjaga aturan dependensi (docs/ARCHITECTURE.md §4, §10).

Diagram arsitektur yang tidak diuji akan luntur pada task ketiga. Test ini
membaca AST setiap berkas sumber dan menegakkan tiga hal:

1. ``routes.py`` tidak mengimpor ``supabase`` atau ``repository``.
2. ``core/`` dan ``scraper/`` tidak mengimpor ``flask``.
3. ``service.py`` tidak mengimpor repository modul lain.

Cepat, tanpa jaringan, tanpa database.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
CORE_DIR = ROOT / "core"
SCRAPER_DIR = ROOT / "scraper"


def _python_files(*directories: Path) -> list[Path]:
    files: list[Path] = []
    for directory in directories:
        files.extend(sorted(directory.rglob("*.py")))
    return files


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


def _package_of(path: Path) -> str:
    """Nama paket tempat berkas berada, untuk menyelesaikan impor relatif."""
    return _module_name(path.parent)


def _resolve_relative(module: str | None, level: int, package: str) -> str:
    parts = package.split(".") if package else []
    if level > 1:
        parts = parts[: len(parts) - (level - 1)]
    if module:
        parts.extend(module.split("."))
    return ".".join(part for part in parts if part)


def imported_modules(path: Path) -> list[str]:
    """Semua nama modul yang diimpor sebuah berkas, impor relatif sudah diselesaikan."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = _package_of(path)
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                resolved = _resolve_relative(node.module, node.level, package)
                modules.append(resolved)
                # ``from ..jobs import repository`` harus menghasilkan
                # ``app.jobs.repository``, bukan hanya ``app.jobs``.
                modules.extend(f"{resolved}.{alias.name}" for alias in node.names)
            elif node.module:
                modules.append(node.module)
                modules.extend(f"{node.module}.{alias.name}" for alias in node.names)

    return modules


def _routes_files() -> list[Path]:
    return sorted(APP_DIR.glob("*/routes.py"))


def _service_files() -> list[Path]:
    return sorted(APP_DIR.glob("*/service.py"))


def test_found_source_files() -> None:
    """Sanity check: test tidak lulus hanya karena tidak menemukan berkas."""
    assert _routes_files(), "Tidak ada app/*/routes.py yang ditemukan."
    assert _service_files(), "Tidak ada app/*/service.py yang ditemukan."
    assert _python_files(CORE_DIR), "Tidak ada berkas di core/."
    assert _python_files(SCRAPER_DIR), "Tidak ada berkas di scraper/."


@pytest.mark.parametrize("path", _routes_files(), ids=lambda path: path.name)
def test_routes_never_touch_data_layer(path: Path) -> None:
    """Aturan 1: route hanya boleh memanggil service, bukan repository atau Supabase."""
    for module in imported_modules(path):
        assert not module.startswith("supabase"), (
            f"{path.relative_to(ROOT)} mengimpor {module!r}. "
            "Route tidak boleh menyentuh client Supabase; gunakan service."
        )
        assert not module.startswith("app.") or ".repository" not in module, (
            f"{path.relative_to(ROOT)} mengimpor {module!r}. "
            "Route tidak boleh mengimpor repository; gunakan service modulnya."
        )


@pytest.mark.parametrize("directory", [CORE_DIR, SCRAPER_DIR], ids=["core", "scraper"])
def test_framework_free_directories(directory: Path) -> None:
    """Aturan 4 dan 5: shared kernel dan pipeline data harus bebas Flask."""
    offenders: list[str] = []
    for path in _python_files(directory):
        for module in imported_modules(path):
            root_module = module.split(".")[0]
            if root_module in {"flask", "werkzeug"} and module != "werkzeug.security":
                offenders.append(f"{path.relative_to(ROOT)} mengimpor {module!r}")
            if root_module in {"app"}:
                offenders.append(f"{path.relative_to(ROOT)} mengimpor {module!r}")

    assert not offenders, (
        "core/ dan scraper/ harus bebas Flask dan tidak boleh mengimpor app/ "
        "(docs/ARCHITECTURE.md §4 aturan 4 dan 5):\n- " + "\n- ".join(offenders)
    )


@pytest.mark.parametrize("path", _service_files(), ids=lambda path: path.name)
def test_service_uses_only_own_repository(path: Path) -> None:
    """Aturan 2: service boleh memakai repository modulnya sendiri, bukan modul lain."""
    own_module = path.parent.name
    offenders: list[str] = []

    for module in imported_modules(path):
        if "repository" not in module:
            continue
        if not module.startswith("app."):
            continue
        # app.<modul>.repository -> hanya modul sendiri yang sah
        parts = module.split(".")
        if len(parts) >= 3 and parts[1] != own_module:
            offenders.append(module)

    assert not offenders, (
        f"{path.relative_to(ROOT)} mengimpor repository modul lain: {offenders}. "
        "Panggil service modul tersebut, bukan repository-nya."
    )


# --- Meta-test: buktikan penjaga benar-benar menangkap pelanggaran ----------

def _write(tmp_path: Path, relative: str, source: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


@pytest.fixture
def synthetic_tree(tmp_path, monkeypatch):
    """Bangun pohon berkas tiruan dan arahkan konstanta modul ini ke sana."""
    monkeypatch.setattr("tests.unit.test_architecture.ROOT", tmp_path)
    monkeypatch.setattr("tests.unit.test_architecture.APP_DIR", tmp_path / "app")
    monkeypatch.setattr("tests.unit.test_architecture.CORE_DIR", tmp_path / "core")
    monkeypatch.setattr("tests.unit.test_architecture.SCRAPER_DIR", tmp_path / "scraper")
    return tmp_path


def test_guard_detects_route_importing_repository(synthetic_tree) -> None:
    """route yang mengimpor repository harus tertangkap."""
    path = _write(
        synthetic_tree,
        "app/jobs/routes.py",
        "from .repository import find_page\n",
    )
    modules = imported_modules(path)
    assert any("repository" in module for module in modules)


def test_guard_detects_core_importing_flask(synthetic_tree) -> None:
    """core/ yang mengimpor flask harus tertangkap."""
    path = _write(
        synthetic_tree,
        "core/bad.py",
        "from flask import current_app\n",
    )
    modules = imported_modules(path)
    assert any(module.split(".")[0] == "flask" for module in modules)


def test_guard_resolves_relative_imports(synthetic_tree) -> None:
    """Impor relatif harus diselesaikan agar tidak lolos dari pemeriksaan."""
    path = _write(
        synthetic_tree,
        "app/cv/service.py",
        "from ..jobs import repository\n",
    )
    modules = imported_modules(path)
    assert "app.jobs.repository" in modules

