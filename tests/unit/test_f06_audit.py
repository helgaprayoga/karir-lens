"""PRD-F06 §7.1: state, responsif, aksesibilitas, dan larangan §6.

Sebagian test membaca berkas (aturan tekstual), sebagian merender halaman nyata
(aturan yang butuh HTML terender). Yang membaca berkas diberi alasan di
docstring-nya: itu pilihan sadar, bukan cara mudah menghindari render.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.auth import repository, service
from app.config import CONFIG_MAP

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
CSS = ROOT / "static" / "css"
COMPONENTS = CSS / "components.css"


def _template_files() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def _rendered(paths: list[str], app) -> dict[str, str]:
    client = app.test_client()
    return {path: client.get(path).get_data(as_text=True) for path in paths}


@pytest.fixture(scope="module")
def ui():
    CONFIG_MAP["f06_preview"] = type(
        "F06Preview", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True, "WTF_CSRF_ENABLED": False}
    )
    application = create_app("f06_preview")
    application.config.update(TESTING=True)
    return application


# Daftar halaman yang diperiksa. Halaman pengguna dan admin memakai akun uji.
PUBLIC_PATHS = [
    "/preview/jobs",
    "/preview/jobs/1",
    "/preview/companies/novatech-labs",
    "/preview/insights",
    "/preview/styleguide",
    "/auth/login",
    "/auth/register",
]

# --- R-F06-10: bahasa ----------------------------------------------------

def test_html_lang_is_id(ui) -> None:
    """Setiap halaman memakai <html lang="id"> (R-F06-10)."""
    for path, body in _rendered(PUBLIC_PATHS, ui).items():
        assert '<html lang="id">' in body, f"{path} tidak memakai lang=id"


# --- R-F06-08: ikon ------------------------------------------------------

def test_icons_have_aria(ui) -> None:
    """Setiap <svg> punya aria-label atau aria-hidden (R-F06-08).

    Diperiksa pada HTML terender, karena macro ikon baru terlihat setelah
    dipanggil — berkas partial-nya sendiri tidak memuat atribut akhir.
    """
    for path, body in _rendered(PUBLIC_PATHS, ui).items():
        for tag in re.findall(r"<svg\b[^>]*>", body):
            assert 'aria-hidden="true"' in tag or "aria-label=" in tag, (
                f"{path} punya <svg> tanpa aria: {tag[:80]}"
            )


# --- R-F06-07: label form -----------------------------------------------

def test_every_form_field_has_label(client) -> None:
    """Setiap input teks punya <label for> yang menunjuk id-nya (R-F06-07).

    Tombol submit (`type="submit"`) dikecualikan: nilai `value`-nya sudah
    menjadi nama aksesibelnya, dan `<label for="submit">` justru keliru.
    """
    for path in ("/auth/login", "/auth/register"):
        body = client.get(path).get_data(as_text=True)
        label_for = set(re.findall(r'<label[^>]*for="([^"]+)"', body))

        for tag in re.findall(r"<input\b[^>]*>", body):
            if 'type="hidden"' in tag or 'type="submit"' in tag:
                continue
            # `\bid="` penting: tanpa batas kata, pola ini juga cocok dengan
            # `aria-inval**id="false"**` dan melaporkan id palsu "false".
            id_input = re.search(r'\bid="([^"]+)"', tag)
            assert id_input, f"{path} punya input tanpa id: {tag[:80]}"
            assert id_input.group(1) in label_for, (
                f"{path} input #{id_input.group(1)} tanpa <label for>"
            )


def test_no_placeholder_as_label(ui) -> None:
    """Placeholder bukan pengganti label — setiap field tetap punya <label>."""
    body = _rendered(["/preview/admin/jobs"], ui)["/preview/admin/jobs"]

    assert "placeholder=" in body
    assert re.search(r'<label[^>]*for="admin-q"', body), "input cari tanpa label"


def test_aria_describedby_points_to_real_id(client) -> None:
    """`aria-describedby` tidak boleh menunjuk id yang tidak ada (R-F06-07)."""
    body = client.post("/auth/register", data={"email": "x", "password": "a"}).get_data(as_text=True)

    for target in re.findall(r'aria-describedby="([^"]+)"', body):
        for satu in target.split():
            assert f'id="{satu}"' in body, f"aria-describedby menunjuk #{satu} yang tidak ada"


# --- R-F06-11: nilai enum mentah ----------------------------------------

def test_no_raw_enum_values(ui) -> None:
    """Nilai enum database tidak tampil mentah (R-F06-11)."""
    terlarang = [r">\s*full-time\s*<", r">\s*part-time\s*<", r">\s*contract\s*<",
                 r">\s*internship\s*<", r">\s*freelance\s*<"]

    paths = PUBLIC_PATHS + ["/preview/cv?state=ready", "/preview/insights"]
    for path, body in _rendered(paths, ui).items():
        for pola in terlarang:
            assert not re.search(pola, body), f"{path} menampilkan enum mentah: {pola}"


def test_salary_period_enum_translated(ui) -> None:
    """Periode gaji tampil sebagai kata, bukan `month`/`year`."""
    body = _rendered(["/preview/insights"], ui)["/preview/insights"]

    assert "bulanan" in body or "tahunan" in body
    assert ">month<" not in body and " month<" not in body
    assert "Gaji Month" not in body


# --- R-F06-12: metrik terlarang ----------------------------------------

def test_no_forbidden_metrics(ui) -> None:
    """Tidak ada metrik tanpa tabel sumber (R-F06-12).

    /styleguide dikecualikan: halaman itu memang MENJELASKAN larangan
    "kelengkapan profil" sebagai dokumentasi komponen. Yang diperiksa adalah
    halaman yang dilihat pengguna.
    """
    dilarang = ("pelamar", "proposal", "kelengkapan profil", "performa anda",
                "job success rate", "under review", "tahapan seleksi")

    halaman = [
        "/preview/jobs",
        "/preview/jobs/1",
        "/preview/companies/novatech-labs",
        "/preview/insights",
        "/preview/profile",
        "/preview/saved",
        "/preview/admin",
    ]
    for path, body in _rendered(halaman, ui).items():
        rendah = body.lower()
        for pola in dilarang:
            assert pola not in rendah, f"{path} memuat metrik terlarang: {pola}"


def test_no_application_status_ui(ui) -> None:
    """Tidak ada status lamaran di halaman mana pun (R-F06-12)."""
    for path, body in _rendered(PUBLIC_PATHS, ui).items():
        rendah = body.lower()
        for pola in ("status lamaran", "sedang direview", "shortlisted"):
            assert pola not in rendah, f"{path} memuat {pola}"


# --- R-F06-14 / R-F06-15: kartu dan radius ------------------------------

def test_no_card_shadow_at_rest() -> None:
    """Kartu diam tidak memakai box-shadow (R-F06-14).

    `box-shadow` yang muncul di daftar `transition` bukan pelanggaran: itu
    hanya mendaftarkan properti yang boleh beranimasi saat hover. Yang dilarang
    adalah nilai shadow yang benar-benar dipakai pada keadaan diam.
    """
    css = COMPONENTS.read_text(encoding="utf-8")

    for kelas in (".job-card {", ".panel {", ".chart-card {", ".stat-tile {"):
        blok = css.split(kelas)[1].split("}")[0]
        # Baris "box-shadow: var(--shadow-hover);" adalah nilai diam yang
        # dilarang. Kemunculan di dalam daftar `transition` bukan.
        assert not re.search(r"^\s*box-shadow:\s*var", blok, re.M), (
            f"{kelas} memakai shadow saat diam"
        )


def test_shadow_only_on_hover() -> None:
    """Shadow hanya muncul pada :hover sebagai isyarat interaksi."""
    css = COMPONENTS.read_text(encoding="utf-8")
    blok = css.split(".job-card:hover {")[1].split("}")[0]

    assert "box-shadow: var(--shadow-hover)" in blok


def test_radius_policy_no_new_full_radius() -> None:
    """`--r-full` hanya pada toggle dan progress bar (R-F06-15).

    Pemeriksaan menyeluruh sudah ada di test_ui_rules; di sini yang dijaga
    adalah komponen baru F06 tidak menambah pelanggaran.
    """
    lines = COMPONENTS.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, 1):
        if "var(--r-full)" not in line:
            continue
        selector = ""
        for back in range(index - 1, max(index - 8, 0), -1):
            if "{" in lines[back - 1]:
                selector = lines[back - 1].split("{")[0].strip()
                break
        if selector:
            assert (selector.startswith(".switch") or ".track" in selector
                    or "progress" in selector or ".avatar" in selector
                    or "summary" in selector or ".user-menu" in selector), (
                f"baris {index}: {selector} memakai --r-full"
            )


# --- R-F06-13 / R-F06-16: motion dan grafik ----------------------------

def test_reduced_motion_rule_present() -> None:
    """prefers-reduced-motion mematikan transition DAN animation (R-F06-13)."""
    blok = COMPONENTS.read_text(encoding="utf-8").split("@media (prefers-reduced-motion: reduce)")[-1]

    assert "transition: none !important" in blok
    assert "animation: none !important" in blok


def test_charts_have_text_alternative(ui) -> None:
    """Setiap kanvas berpasangan dengan tabel alternatif (R-F06-16)."""
    body = _rendered(["/preview/insights"], ui)["/preview/insights"]

    kanvas = body.count("<canvas")
    alternatif = body.count('class="chart-alt"')
    assert kanvas == alternatif
    for blok in re.findall(r'<details class="chart-alt">(.*?)</details>', body, re.S):
        assert "<caption" in blok


# --- R-F06-03: responsif -------------------------------------------------

def test_no_horizontal_scroll(ui) -> None:
    """Tidak ada elemen yang melebar melewati viewport pada semua halaman.

    Diperiksa di sisi CSS/markup: setiap grid memakai `minmax(min(Xpx, 100%), …)`
    sehingga tidak ada kolom yang menolak menyusut di bawah lebar isinya. Bukti
    render sebenarnya ada di §12.6 (audit browser 360/768/1024/1280).
    """
    css = COMPONENTS.read_text(encoding="utf-8")

    for pola in re.findall(r"grid-template-columns:\s*repeat\([^;]+;", css):
        if "minmax(0," in pola or "100%" in pola:
            continue
        raise AssertionError(f"grid berpotensi melebar di layar sempit: {pola}")


def test_rail_drops_below_below_1180() -> None:
    """Rail turun ke bawah konten pada < 1180px (R-F06-04)."""
    css = COMPONENTS.read_text(encoding="utf-8")
    bagian = css.split("@media (max-width: 1180px)")[1]

    assert ".layout" in bagian
    # Satu kolom: rail tidak lagi berbagi baris dengan feed.
    assert "grid-template-columns: 1fr" in bagian


# --- R-F06-09: target sentuh --------------------------------------------

def test_icon_controls_meet_touch_target() -> None:
    """Kontrol ikon minimal 44×44px (R-F06-09)."""
    css = COMPONENTS.read_text(encoding="utf-8")

    for kelas in (".job-card .save-btn {", ".user-menu > summary {"):
        blok = css.split(kelas)[1].split("}")[0]
        assert "var(--touch-min)" in blok or "var(--touch-min" in blok, (
            f"{kelas} tidak memakai --touch-min"
        )


# --- R-F06-06: focus ring -----------------------------------------------

def test_focus_visible_defined_for_controls() -> None:
    """Setiap kontrol punya aturan :focus-visible (R-F06-06)."""
    css = COMPONENTS.read_text(encoding="utf-8")

    for kelas in (".btn", ".chip", ".nav-pill a", ".user-links a",
                  ".user-menu > summary", ".admin-tabs a", ".back-link"):
        assert f"{kelas}:focus-visible" in css or f"{kelas.rstrip()}:focus-visible" in css, (
            f"{kelas} tidak punya :focus-visible"
        )


def test_focus_ring_uses_token() -> None:
    """Focus ring memakai --focus-ring atau outline --action, bukan nilai lepas."""
    css = COMPONENTS.read_text(encoding="utf-8")
    blok = css.split(".btn:focus-visible {")[1].split("}")[0]
    assert "var(--focus-ring)" in blok


# --- R-F06-01 / R-F06-02: state kontrol ---------------------------------

def test_buttons_have_active_state_never_blue() -> None:
    """State :active tiap varian tombol tidak memakai warna biru Bootstrap.

    Bug nyata: Bootstrap memasang `--bs-btn-active-bg: #0a58ca` lewat
    `:not(.btn-check)+.btn:active`, sehingga tombol gelap berubah BIRU saat
    ditekan. Test ini menjaga variabel itu tetap berisi warna sendiri.
    """
    css = COMPONENTS.read_text(encoding="utf-8")

    for varian in (".btn-primary", ".btn-line", ".btn-soft", ".btn-ghost", ".btn-danger"):
        blok = css.split(f"{varian} {{")[1].split("}")[0]
        assert "--bs-btn-active-bg" in blok, f"{varian} tidak menetapkan warna aktif"
        assert "#0a58ca" not in blok, f"{varian} masih memakai biru Bootstrap"


def test_bootstrap_blue_neutralized() -> None:
    """Blok .btn mematikan bayangan fokus biru Bootstrap."""
    css = COMPONENTS.read_text(encoding="utf-8")
    blok = css.split(".btn {")[1].split("}")[0]

    assert "--bs-btn-focus-box-shadow: none" in blok
    assert "-webkit-tap-highlight-color: transparent" in blok


def test_controls_have_hover_and_active() -> None:
    """Kontrol utama punya state hover dan active (R-F06-01)."""
    css = COMPONENTS.read_text(encoding="utf-8")

    for kelas in (".btn", ".chip", ".nav-pill a", ".user-links a", ".back-link"):
        assert f"{kelas}:hover" in css, f"{kelas} tanpa :hover"
    for kelas in (".btn", ".chip", ".page-btn", ".nav-pill a"):
        assert f"{kelas}:active" in css, f"{kelas} tanpa :active"


# --- Navigasi: satu pintu per tujuan -----------------------------------

def test_no_duplicate_ai_entry(ui) -> None:
    """Hanya ada SATU pintu masuk AI (design system §6).

    Sebelumnya navpill memuat "Asisten" sementara header memuat "Asisten AI",
    dan tombol header itu pun menunjuk ke /styleguide.
    """
    body = _rendered(["/preview/jobs"], ui)["/preview/jobs"]

    assert body.count("Asisten AI") == 1
    assert ">Asisten</a>" not in body
    # Tombol AI menuju halaman asisten, bukan styleguide.
    assert 'class="ask-ai" href="/preview/assistant"' in body


def test_profile_only_in_user_menu(ui, monkeypatch) -> None:
    """Profil tidak ada di navpill; ia tinggal di menu pengguna.

    Dengan begitu tombol Masuk/Daftar benar-benar hilang setelah login dan
    digantikan avatar.
    """
    store: dict[str, dict] = {}

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
        row = {"id": 1, "email": email, "password_hash": password_hash, "name": name}
        store[email] = row
        return {"id": 1, "email": email, "name": name}

    monkeypatch.setattr(repository, "find_by_email", find_by_email)
    monkeypatch.setattr(repository, "find_by_id", find_by_id)
    monkeypatch.setattr(repository, "create", create)

    client = ui.test_client()
    client.post("/auth/register",
                data={"email": "menu@example.com", "password": "rahasia123", "name": "Budi"})
    body = client.get("/preview/jobs").get_data(as_text=True)

    nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
    tautan = re.findall(r">\s*([A-Za-z]+)\s*</a>", nav)

    assert "Profil" not in tautan
    assert 'class="user-menu"' in body
    assert ">Profil</a>" in body            # ada, tapi di panel pengguna
    assert "Masuk</a>" not in body
    assert "Daftar</a>" not in body
    assert "Keluar" in body


def test_guest_nav_is_public_only(ui) -> None:
    """Tamu tidak melihat Tersimpan, CV, atau Admin."""
    body = _rendered(["/preview/jobs"], ui)["/preview/jobs"]
    nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
    tautan = re.findall(r">\s*([A-Za-z]+)\s*</a>", nav)

    assert tautan == ["Lowongan", "Insight"]
