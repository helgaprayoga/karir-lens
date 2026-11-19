"""Pengujian aturan design system (PRD-F01 §7.1, R-F01-01 s.d. R-F01-11).

Test ini menegakkan aturan yang mudah luntur: token lengkap, tidak ada nilai
lepas di template, hanya toggle dan progress bar yang memakai ``--r-full``, dan
``/styleguide`` benar-benar tertutup saat ``PREVIEW_UI`` mati.

Cepat, tanpa jaringan, tanpa database.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import create_app
from app.config import CONFIG_MAP
from core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
CSS = ROOT / "static" / "css"
TOKENS = CSS / "tokens.css"
COMPONENTS = CSS / "components.css"

# Token wajib: design system §3.1 (warna), §3.2 (tipografi), §3.4 (padding),
# §3.5 (radius), §3.7 (motion). Daftar ini sengaja eksplisit.
REQUIRED_TOKENS = [
    # Permukaan
    "--sheet", "--sunken", "--sunken-2", "--line", "--line-2", "--line-strong",
    # Teks
    "--ink", "--ink-2", "--ink-3",
    # Aksi dan status
    "--action", "--blue", "--violet", "--rose", "--green", "--amber",
    "--danger", "--danger-ink",
    # Permukaan status
    "--success-bg", "--warning-bg", "--info-bg", "--match-high-bg",
    "--hint-bg", "--hint-ink", "--danger-bg",
    # Sumber lowongan
    "--source-dealls", "--source-kalibrr", "--source-remotive",
    # Gradien AI
    "--ai-from", "--ai-to",
    # Tipografi
    "--font-sans", "--text-page", "--text-section", "--text-stat",
    "--text-card", "--text-body", "--text-label", "--text-meta", "--text-micro",
    # Spacing
    "--space-1", "--space-2", "--space-3", "--space-4", "--space-5",
    "--space-6", "--space-8", "--space-10",
    # Padding dan lebar
    "--gutter-sheet", "--gutter-rail", "--gap-card", "--pad-card-y",
    "--pad-card-x", "--pad-panel", "--pad-hint", "--rail-w",
    # Radius
    "--r-sm", "--r-chip", "--r-md", "--r-card", "--r-full",
    # Elevation
    "--shadow-hover", "--shadow-toast",
    # Motion
    "--dur-instant", "--dur-fast", "--dur-base", "--ease-out", "--ease-in-out",
    # Kontrol
    "--control-h",
]


def _template_files() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def _defined_tokens() -> set[str]:
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", TOKENS.read_text(encoding="utf-8")))


# --- R-F01-01: seluruh token tersedia -------------------------------------

def test_tokens_defined() -> None:
    """Setiap token design system §3 ada di tokens.css."""
    defined = _defined_tokens()
    missing = [token for token in REQUIRED_TOKENS if token not in defined]
    assert not missing, f"Token belum didefinisikan di tokens.css: {missing}"


def test_components_only_reference_defined_tokens() -> None:
    """Komponen tidak boleh memakai custom property yang tidak terdefinisi."""
    defined = _defined_tokens()
    used = set(re.findall(r"var\((--[a-z0-9-]+)", COMPONENTS.read_text(encoding="utf-8")))
    unknown = sorted(used - defined)
    assert not unknown, f"components.css memakai token yang tidak ada di tokens.css: {unknown}"


# --- R-F01-01 / §7: tidak ada nilai lepas di template ----------------------

def test_no_raw_hex_in_templates() -> None:
    """Tidak ada nilai #rrggbb di templates/**; warna hanya lewat token."""
    offenders: list[str] = []
    for path in _template_files():
        for nomor, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", line):
                offenders.append(f"{path.relative_to(ROOT)}:{nomor}")
    assert not offenders, f"Nilai hex lepas di template: {offenders}"


def test_no_inline_style_in_templates(tmp_path) -> None:
    """Atribut style= dilarang; state diatur CSS (PRD-F01 §9).

    Tidak ada pengecualian: nilai data pun lewat kelas atau atribut ``data-*``
    yang diterapkan JavaScript, bukan atribut ``style=``.

    Komentar Jinja dan blok <script> dibuang lebih dulu, karena keduanya boleh
    menyebut kata "style=" tanpa itu menjadi atribut HTML.
    """
    komentar = re.compile(r"\{#.*?#\}", re.S)
    skrip = re.compile(r"<script\b.*?</script>", re.S | re.I)
    atribut = re.compile(r"<[^>]*\bstyle\s*=", re.I | re.S)

    offenders: list[str] = []
    for path in _template_files():
        isi = path.read_text(encoding="utf-8")
        isi = skrip.sub("", komentar.sub("", isi))
        if atribut.search(isi):
            nomor = isi[: atribut.search(isi).start()].count("\n") + 1
            offenders.append(f"{path.relative_to(ROOT)}:~{nomor}")

    assert not offenders, "Atribut style= tidak diizinkan:\n- " + "\n- ".join(offenders)


# --- R-F01-06: aturan radius ---------------------------------------------

def test_radius_policy() -> None:
    """Hanya toggle dan progress bar memakai --r-full (design system §3.5)."""
    lines = COMPONENTS.read_text(encoding="utf-8").splitlines()
    offenders: list[str] = []

    for index, line in enumerate(lines, 1):
        if "var(--r-full)" not in line:
            continue
        # Cari selector terdekat di atasnya.
        selector = ""
        for back in range(index - 1, max(index - 8, 0), -1):
            if "{" in lines[back - 1]:
                selector = lines[back - 1].split("{")[0].strip()
                break
        if selector and not (
            selector.startswith(".switch")
            or ".track" in selector
            or "progress" in selector
        ):
            offenders.append(f"baris {index}: {selector} -> {line.strip()}")

    assert not offenders, (
        "Hanya toggle switch dan progress bar boleh memakai --r-full:\n- "
        + "\n- ".join(offenders)
    )


# --- R-F01-07: breakpoint lengkap ---------------------------------------

def test_breakpoints_defined() -> None:
    """Breakpoint 1240, 1180, 820, 480 px ada di CSS."""
    isi = TOKENS.read_text(encoding="utf-8") + COMPONENTS.read_text(encoding="utf-8")
    for lebar in (1240, 1180, 820, 480):
        assert f"max-width: {lebar}px" in isi, f"Breakpoint {lebar}px tidak ditemukan"


# --- R-F01-11: prefers-reduced-motion -----------------------------------

def test_reduced_motion_rules() -> None:
    """prefers-reduced-motion mematikan transition DAN animation."""
    isi = COMPONENTS.read_text(encoding="utf-8")
    blok = isi.split("@media (prefers-reduced-motion: reduce)")[-1]
    assert "animation: none !important" in blok
    assert "transition: none !important" in blok


# --- R-F01-08: /styleguide gating ---------------------------------------

def _app_with_preview(enabled: bool):
    application = create_app("testing")
    application.config.update(PREVIEW_UI=enabled)
    # Blueprint sudah terdaftar saat create_app; uji gating lewat config yang
    # dipakai untuk registrasi.
    return application


def test_styleguide_hidden_in_production() -> None:
    """/styleguide mengembalikan 404 ketika PREVIEW_UI tidak aktif."""
    app = create_app("testing")
    app.config.update(PREVIEW_UI=False)
    client = app.test_client()
    assert client.get("/preview/styleguide").status_code == 404


def test_preview_blueprint_gated() -> None:
    """Blueprint preview hanya terdaftar saat PREVIEW_UI=true."""
    off = create_app("testing")
    off.config.update(PREVIEW_UI=False)
    assert "preview.styleguide" not in off.view_functions

    CONFIG_MAP["preview_gated"] = type(
        "PreviewGated", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True}
    )
    on = create_app("preview_gated")
    assert "preview.styleguide" in on.view_functions


def _preview_app():
    """App dengan PREVIEW_UI aktif, dibuat dari kelas config sejak awal.

    Mengubah ``app.config`` setelah ``create_app`` tidak mendaftarkan blueprint,
    jadi kelas config baru didaftarkan ke CONFIG_MAP lebih dulu.
    """
    from app import create_app as factory

    CONFIG_MAP["preview_on"] = type(
        "PreviewOn", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True}
    )
    return factory("preview_on")


def test_styleguide_available_in_preview() -> None:
    """/styleguide mengembalikan 200 ketika PREVIEW_UI=true."""
    client = _preview_app().test_client()
    resp = client.get("/preview/styleguide")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Komponen wajib benar-benar dirender, bukan hanya 200 kosong.
    for penanda in ("job-card", "chip", "pager", "empty", "skeleton-card",
                    "status-pill", "banner", "metric-cell", "stat-tile"):
        assert penanda in body, f"/styleguide tidak memuat '{penanda}'"


# --- R-F01-03: setiap partial dapat dirender -----------------------------

@pytest.mark.parametrize(
    "partial,konteks",
    [
        ("components/source_badge.html", {"source": "dealls"}),
        ("components/skill_tag.html", {"skills": ["python", "sql"]}),
        ("components/salary_range.html", {"salary_min": 1, "salary_max": 2}),
        ("components/pagination.html", {"meta": {"page": 1, "per_page": 12, "total": 240, "has_next": True}, "endpoint": "main.index"}),
        ("components/status_pill.html", {"status": "success"}),
        ("components/empty_state.html", {"title": "Kosong", "message": "Tidak ada data."}),
        ("components/skeleton_card.html", {}),
        ("components/alert_banner.html", {"message": "Halo", "variant": "info"}),
        ("components/stat_tile.html", {"value": 10, "label": "Total"}),
    ],
)
def test_components_rendered(app, partial, konteks) -> None:
    """Setiap partial komponen dapat dirender dengan fixture tanpa error."""
    from jinja2 import TemplateNotFound

    module = partial.replace("/", ".").removesuffix(".html")
    try:
        template = app.jinja_env.get_template(partial)
    except TemplateNotFound:  # pragma: no cover - menjaga pesan jelas
        pytest.fail(f"Partial {partial} tidak ditemukan")

    # Partial berisi macro; impor lalu panggil macro pertama yang tersedia.
    nama_macro = {
        "components/source_badge.html": "source_badge",
        "components/skill_tag.html": "skill_tags",
        "components/salary_range.html": "salary_range",
        "components/pagination.html": "pagination",
        "components/status_pill.html": "status_pill",
        "components/empty_state.html": "empty_state",
        "components/skeleton_card.html": "skeleton_card",
        "components/alert_banner.html": "alert_banner",
        "components/stat_tile.html": "stat_tile",
    }[partial]

    with app.test_request_context("/"):
        macro = template.module.__dict__[nama_macro]
        hasil = macro(**konteks)
    assert isinstance(hasil, str)
    assert hasil.strip(), f"Macro {nama_macro} menghasilkan string kosong"


# --- R-F01-04 / §7: hook base.html --------------------------------------

def test_base_layout_has_required_hooks(client) -> None:
    """base.html memuat .shell, .top, .layout, skip-link, dan lang=\"id\"."""
    body = client.get("/").get_data(as_text=True)
    for hook in ('class="shell"', 'class="top"', 'class="layout"', 'skip-link', 'lang="id"'):
        assert hook in body, f"base.html tidak memuat {hook}"


def test_navpill_changes_by_role(client) -> None:
    """Navigasi publik tidak memuat tautan pengguna (R-06-10)."""
    body = client.get("/").get_data(as_text=True)
    assert "Keluar" not in body
    assert "Masuk" in body and "Daftar" in body


def test_no_application_tracking_language() -> None:
    """/styleguide tidak menampilkan metrik lamaran atau performa karangan."""
    body = _preview_app().test_client().get("/preview/styleguide").get_data(as_text=True)
    for dilarang in ("proposals", "Kelengkapan profil", "Performa Anda", "under review"):
        assert dilarang not in body, f"Pola terlarang muncul: {dilarang}"
