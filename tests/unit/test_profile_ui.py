"""PRD-F03 §7.1: auth accessibility, profil, tersimpan, toast, dan larangan.

Track A memakai fixture, jadi halaman profil dan tersimpan hidup di blueprint
``preview``. Test tetap memeriksa template produksi yang sama.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP


@pytest.fixture(scope="module")
def ui():
    """App dengan PREVIEW_UI aktif, dibuat dari kelas config sejak awal."""
    CONFIG_MAP["f03_preview"] = type(
        "F03Preview", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True, "WTF_CSRF_ENABLED": False}
    )
    application = create_app("f03_preview")
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def uiClient(ui):
    return ui.test_client()


def _html(response) -> str:
    return response.get_data(as_text=True)


# --- R-F03-01 / R-F03-02: form auth ---------------------------------------

def test_register_shows_field_errors(client) -> None:
    """Kirim form kosong: setiap field yang salah punya pesan di dekatnya."""
    body = _html(client.post("/auth/register", data={"email": "", "password": ""}))

    assert 'class="field-error"' in body
    assert "Email wajib diisi." in body
    assert "Password wajib diisi." in body
    # Pesan berada di dalam .field yang sama dengan inputnya, bukan banner jauh.
    for blok in re.findall(r'<div class="field">(.*?)</div>\s*</div>', body, re.S):
        if "field-error" in blok:
            assert "input" in blok


def test_field_aria_attributes(client) -> None:
    """`aria-invalid` dan `aria-describedby` menunjuk id pesan yang benar-benar ada."""
    body = _html(client.post("/auth/register", data={"email": "bukan-email", "password": "pendek"}))

    assert 'aria-invalid="true"' in body
    pasangan = re.findall(r'aria-describedby="([a-z]+-error)"', body)
    assert pasangan, "tidak ada aria-describedby yang menunjuk pesan error"

    for target in pasangan:
        assert f'id="{target}"' in body, f"aria-describedby menunjuk #{target} yang tidak ada"


def test_field_aria_clean_when_valid(client) -> None:
    """Form yang belum dikirim tidak menandai field sebagai tidak valid."""
    body = _html(client.get("/auth/login"))
    assert 'aria-invalid="true"' not in body


def test_password_hint_only_without_error(client) -> None:
    """Petunjuk dan pesan error tidak tampil bersamaan untuk field yang sama."""
    bersih = _html(client.get("/auth/register"))
    assert "Minimal 8 karakter." in bersih

    salah = _html(client.post("/auth/register", data={"email": "a@b.com", "password": "pendek"}))
    blok = salah.split('name="password"')[1]
    assert "Password minimal 8 karakter." in blok
    # Petunjuk tidak diduplikasi saat error tampil.
    assert "Minimal 8 karakter.</p>" not in blok


# --- R-F03-03: state tombol submit ---------------------------------------

def test_submit_button_states(client) -> None:
    """Tombol submit punya label loading dan aria-busy dipasang oleh skrip."""
    body = _html(client.get("/auth/login"))

    assert 'data-loading-label="Memeriksa…"' in body
    assert 'type="submit"' in body
    # State loading tidak boleh ditulis di HTML awal: pengiriman belum terjadi.
    assert 'aria-busy="true"' not in body


def test_loading_state_scripted() -> None:
    """base.html memasang aria-busy + disabled saat submit (R-F03-03)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")

    assert 'setAttribute("aria-busy", "true")' in base
    assert ".disabled = true" in base
    assert "data-loading-label" in base


# --- R-F03-04 / R-F03-05 / R-F03-11: profil ------------------------------

def test_profile_renders_skills(uiClient) -> None:
    """Skill terkonfirmasi tampil beserta sumbernya (R-F03-05)."""
    body = _html(uiClient.get("/preview/profile"))

    assert 'class="skill-row"' in body
    assert "python" in body and "sql" in body
    assert "Dari CV" in body
    assert "Ditambahkan manual" in body


def test_profile_shows_source_per_skill(uiClient) -> None:
    """Setiap baris skill punya penanda sumber, bukan hanya sebagian."""
    body = _html(uiClient.get("/preview/profile"))
    baris = re.findall(r'<li class="skill-row"[^>]*>(.*?)</li>', body, re.S)

    assert baris, "tidak ada baris skill"
    for blok in baris:
        assert 'class="skill-source"' in blok, f"baris tanpa sumber: {blok[:80]}"


def test_profile_has_remove_button(uiClient) -> None:
    """Setiap skill punya tombol hapus dengan label yang menyebut skillnya."""
    body = _html(uiClient.get("/preview/profile"))
    assert 'data-remove-skill=' in body
    assert 'aria-label="Hapus skill python"' in body


def test_profile_only_confirmed_skills(uiClient) -> None:
    """Skill yang belum dikonfirmasi tidak dihitung sebagai milik pengguna."""
    body = _html(uiClient.get("/preview/profile"))
    # `docker` ada di fixture dengan is_confirmed=false.
    assert "docker" not in body


def test_profile_summary_counts(uiClient) -> None:
    """Ringkasan sesuai fixture: 5 skill, 3 tersimpan."""
    body = _html(uiClient.get("/preview/profile"))

    assert "Skill terkonfirmasi" in body
    assert "Lowongan tersimpan" in body
    assert re.search(r'<span>5</span></div>\s*<div class="cap">Skill terkonfirmasi', body)
    assert re.search(r'<span>3</span></div>\s*<div class="cap">Lowongan tersimpan', body)


def test_no_profile_completeness_metric(uiClient) -> None:
    """Tidak ada persentase kelengkapan profil (R-F03-11)."""
    body = _html(uiClient.get("/preview/profile")).lower()

    for dilarang in ("kelengkapan profil", "profil lengkap", "completeness", "%"):
        assert dilarang not in body, f"Profil memuat metrik karangan: {dilarang}"


# --- R-F03-06 / R-F03-07: tersimpan --------------------------------------

def test_saved_uses_job_card(uiClient) -> None:
    """`/saved` memakai partial kartu yang sama dengan katalog (R-F03-06)."""
    saved = _html(uiClient.get("/preview/saved"))
    catalog = _html(uiClient.get("/preview/jobs"))

    assert 'class="job-card"' in saved
    # Anatomi identik: penanda yang sama harus ada di kedua halaman.
    for penanda in ('class="company"', 'class="source-badge"', 'class="tags"',
                    'class="pay"', 'class="card-link"'):
        assert penanda in saved, f"/saved tidak memuat {penanda}"
        assert penanda in catalog, f"/preview/jobs tidak memuat {penanda}"


def test_saved_cards_link_to_detail(uiClient) -> None:
    """Kartu tersimpan menuju detail, sama seperti katalog."""
    body = _html(uiClient.get("/preview/saved"))
    assert 'href="/preview/jobs/' in body


def test_saved_empty_state(uiClient) -> None:
    """Keadaan kosong memakai EmptyState dengan ajakan menjelajahi lowongan."""
    body = _html(uiClient.get("/preview/saved?empty=1"))

    assert 'class="empty"' in body
    assert "Belum ada lowongan tersimpan" in body
    assert "Jelajahi lowongan" in body
    assert 'class="job-card"' not in body


# --- R-F03-08 / R-F03-09: toast dan state simpan -------------------------

def test_toast_has_live_region(client) -> None:
    """Toast memakai role=status dan aria-live=polite, ada di semua halaman."""
    for path in ("/", "/auth/login"):
        body = _html(client.get(path))
        blok = body.split('class="toast"')[1].split("</div>")[0]
        assert 'role="status"' in blok
        assert 'aria-live="polite"' in blok


def test_save_button_reflects_state(uiClient) -> None:
    """Tombol simpan menandai state aktif dengan aria-pressed (R-F03-09)."""
    body = _html(uiClient.get("/preview/saved"))
    # Semua kartu di /saved memang tersimpan.
    assert 'aria-pressed="true"' in body
    # Ikon terisi saat aktif.
    assert 'fill="currentColor"' in body


def test_save_feedback_scripted() -> None:
    """Klik simpan memberi toast, bukan diam (R-F03-08)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")

    assert "Lowongan disimpan" in base
    assert "Dihapus dari tersimpan" in base
    assert "showToast" in base


# --- R-F03-10 / R-F03-12: larangan ---------------------------------------

def test_no_application_tracker_ui(uiClient) -> None:
    """Tidak ada status lamaran atau tahapan seleksi (R-F03-12)."""
    for path in ("/preview/profile", "/preview/saved"):
        body = _html(uiClient.get(path)).lower()
        for dilarang in ("status lamaran", "tahapan seleksi", "under review",
                         "shortlisted", "wawancara", "interview"):
            assert dilarang not in body, f"{path} memuat {dilarang}"


def test_personal_pages_have_nav_links(uiClient) -> None:
    """Navigasi menampilkan tautan pratinjau agar halaman dapat ditemukan."""
    body = _html(uiClient.get("/preview/profile"))
    assert 'href="/preview/saved"' in body


def test_nav_marks_exactly_one_active(uiClient) -> None:
    """Setiap halaman menyorot tepat satu menu, termasuk halaman anak.

    Profil tidak lagi punya menu di navpill — ia halaman akun dan tinggal di
    menu pengguna pojok kanan atas — sehingga halaman profil tidak menyorot
    menu penjelajahan mana pun.
    """
    harapan = {
        "/preview/jobs": "Lowongan",
        "/preview/jobs/1": "Lowongan",
        "/preview/companies/novatech-labs": "Lowongan",
    }
    for path, menu in harapan.items():
        body = _html(uiClient.get(path))
        nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
        aktif = re.findall(r'<a[^>]*aria-current="page"[^>]*>\s*([A-Za-z]+)\s*</a>', nav)
        assert aktif == [menu], f"{path} menyorot {aktif}, seharusnya {[menu]}"

    # Halaman profil tidak menyorot menu penjelajahan apa pun.
    body = _html(uiClient.get("/preview/profile"))
    nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
    assert 'aria-current="page"' not in nav


def test_guest_sees_only_public_nav(uiClient) -> None:
    """Tamu hanya melihat menu penjelajahan, tanpa Tersimpan/CV/Admin."""
    body = _html(uiClient.get("/preview/jobs"))
    nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
    tautan = re.findall(r">\s*([A-Za-z]+)\s*</a>", nav)

    assert tautan == ["Lowongan", "Insight"]
    assert "Masuk" in body and "Daftar" in body
    assert 'class="user-menu"' not in body


def test_production_nav_hides_preview_links() -> None:
    """Saat preview mati, tautan pratinjau tidak muncul sama sekali."""
    body = _html(create_app("testing").test_client().get("/"))
    nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)

    for dilarang in ("/preview/", "Tersimpan"):
        assert dilarang not in nav
