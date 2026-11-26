"""PRD-F05 §7.1: insight, grafik, statistik gaji, dan panel admin.

Track A memakai fixture, jadi halaman hidup di blueprint ``preview``. Test tetap
memeriksa template produksi yang sama.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP


@pytest.fixture(scope="module")
def ui():
    CONFIG_MAP["f05_preview"] = type(
        "F05Preview", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True, "WTF_CSRF_ENABLED": False}
    )
    application = create_app("f05_preview")
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def uiClient(ui):
    return ui.test_client()


def _html(response) -> str:
    return response.get_data(as_text=True)


# --- R-F05-01 / R-F05-06: isi insight ------------------------------------

def test_insights_renders_sections(uiClient) -> None:
    """Tiga bagian insight terender dari fixture (R-F05-01)."""
    body = _html(uiClient.get("/preview/insights"))

    for judul in ("Lowongan per kategori", "Skill paling sering diminta", "Statistik gaji"):
        assert judul in body, f"bagian '{judul}' tidak ada"
    assert 'class="stat-tile"' in body
    assert "<canvas" in body


def test_chart_has_text_alternative(uiClient) -> None:
    """Setiap grafik punya ringkasan tabel yang dapat dibuka (R-F05-06)."""
    body = _html(uiClient.get("/preview/insights"))

    kanvas = body.count("<canvas")
    alternatif = body.count('class="chart-alt"')
    assert kanvas > 0
    assert alternatif == kanvas, f"{kanvas} kanvas tapi {alternatif} tabel alternatif"

    # Alternatif memakai <details> agar angka tetap dapat dibaca pembaca layar.
    for blok in re.findall(r'<details class="chart-alt">(.*?)</details>', body, re.S):
        assert "<table" in blok
        assert "<caption" in blok


def test_chart_colors_from_tokens() -> None:
    """Warna grafik dibaca dari token CSS, bukan hex di JavaScript (§9)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    tpl = (root / "templates" / "insights" / "index.html").read_text(encoding="utf-8")
    tokens = (root / "static" / "css" / "tokens.css").read_text(encoding="utf-8")

    assert "getPropertyValue" in tpl
    for nama in ("--chart-bar", "--chart-grid", "--chart-label"):
        assert nama in tpl, f"grafik tidak memakai token {nama}"
        assert nama in tokens, f"token {nama} tidak didefinisikan"


def test_chart_registry_destroys_old(uiClient) -> None:
    """Grafik lama dihancurkan sebelum yang baru dibuat (§9)."""
    body = _html(uiClient.get("/preview/insights"))

    assert "destroyChart" in body
    assert ".destroy()" in body


def test_chart_horizontal_for_long_labels() -> None:
    """Kedua grafik memakai bar horizontal agar label tidak bertumpuk di 360px.

    Diuji di sisi konfigurasi karena tabrakan label adalah perilaku render
    Chart.js, bukan markup.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    tpl = (root / "templates" / "insights" / "index.html").read_text(encoding="utf-8")

    assert 'indexAxis: "y"' in tpl
    assert 'horizontalChart("chart-categories"' in tpl
    assert 'horizontalChart("chart-skills"' in tpl


# --- R-F05-02 / R-F05-03 / R-F05-04: statistik gaji ---------------------

def test_salary_shows_quartiles(uiClient) -> None:
    """Median, P25, P75, dan jumlah sampel tampil (R-F05-02)."""
    body = _html(uiClient.get("/preview/insights"))

    for label in ("Median", "P25", "P75"):
        assert label in body
    assert "42 sampel" in body
    assert "9.000.000" in body
    assert "7.000.000" in body
    assert "12.000.000" in body


def test_insufficient_sample_message(uiClient) -> None:
    """Sampel kurang memunculkan banner data terbatas (R-F05-03)."""
    body = _html(uiClient.get("/preview/insights?sample=low"))

    assert "banner banner-warning" in body
    assert "Data gaji belum dapat ditampilkan" in body
    assert "minimal 5" in body


def test_no_chart_when_insufficient(uiClient) -> None:
    """Saat sampel kurang, tidak ada kartu gaji dan tidak ada angka nol."""
    body = _html(uiClient.get("/preview/insights?sample=low"))

    assert 'class="salary-card"' not in body
    assert "salary-stats" not in body
    # Angka nol akan menjadi klaim palsu tentang gaji.
    assert ">0<" not in body.split("Statistik gaji")[1]


def test_currency_not_mixed(uiClient) -> None:
    """Setiap kartu gaji hanya memuat satu mata uang (R-F05-04)."""
    body = _html(uiClient.get("/preview/insights"))
    kartu = re.findall(r'<section class="panel salary-card">(.*?)</section>', body, re.S)

    assert len(kartu) >= 2, "fixture memuat IDR dan USD"
    for blok in kartu:
        mata_uang = set(re.findall(r"\b(IDR|USD|EUR|SGD)\b", blok))
        assert len(mata_uang) == 1, f"satu kartu memuat beberapa mata uang: {mata_uang}"


def test_salary_period_not_raw_enum(uiClient) -> None:
    """Periode ditampilkan sebagai kata, bukan nilai enum mentah.

    "Gaji Month · IDR" adalah nilai database dan dilarang (§2 butir 4).
    """
    body = _html(uiClient.get("/preview/insights"))

    assert "Gaji bulanan" in body
    assert "Gaji Month" not in body


# --- R-F05-07: larangan prediksi ----------------------------------------

def test_no_prediction_fields(uiClient) -> None:
    """Tidak ada angka atau label prediksi (R-F05-07)."""
    for path in ("/preview/insights", "/preview/admin"):
        body = _html(uiClient.get(path)).lower()
        for dilarang in ("prediksi gaji", "perkiraan gaji", "estimasi gaji",
                         "forecast", "diprediksi", "proyeksi"):
            assert dilarang not in body, f"{path} memuat {dilarang}"


# --- R-F05-08 s.d. R-F05-12: admin -------------------------------------

def test_admin_summary_tiles(uiClient) -> None:
    """Kartu ringkasan admin sesuai fixture (R-F05-08)."""
    body = _html(uiClient.get("/preview/admin"))

    assert body.count('class="stat-tile"') == 4
    assert "1.842" in body
    assert "Lowongan tersimpan" in body
    assert "Pengguna aktif" in body


def test_admin_users_no_password(uiClient) -> None:
    """Markup pengguna tidak memuat password atau hash (R-F05-10)."""
    body = _html(uiClient.get("/preview/admin/users")).lower()

    assert "password" not in body
    assert "password_hash" not in body
    # Nama kolom yang ditampilkan adalah data aman.
    assert "email" in body
    assert "peran" in body


def test_admin_runs_status_pills(uiClient) -> None:
    """Setiap status run memakai StatusPill berbahasa Indonesia (R-F05-11)."""
    body = _html(uiClient.get("/preview/admin/runs"))

    assert "status-pill" in body
    # Nilai enum mentah tidak boleh tampil.
    for mentah in (">success<", ">partial<", ">failed<", ">running<", ">skipped<"):
        assert mentah not in body, f"enum mentah tampil: {mentah}"

    assert "Berhasil" in body
    assert "Sebagian berhasil" in body
    assert "Gagal" in body


def test_admin_runs_error_message(uiClient) -> None:
    """Pesan galat run ditampilkan (R-F05-11)."""
    body = _html(uiClient.get("/preview/admin/runs"))

    assert "Server menolak akses" in body
    assert "robots.txt melarang" in body
    # Run yang masih berjalan tidak menampilkan pesan galat palsu.
    assert "Belum selesai" in body


def test_admin_clusters_table(uiClient) -> None:
    """Label, kata kunci, dan jumlah tampil per cluster (R-F05-12)."""
    body = _html(uiClient.get("/preview/admin/clusters"))

    assert "Backend &amp; Data" in body or "Backend & Data" in body
    assert "python" in body
    assert "120" in body


def test_admin_no_cv_links(uiClient) -> None:
    """Tidak ada akses CV di dalam panel admin (R-F05-13, R-09-09).

    Yang diperiksa adalah ISI panel (``<main>``), bukan header global. Nav
    aplikasi memang memuat tautan "CV" menuju halaman CV milik pengguna sendiri
    di semua halaman; itu bukan akses admin ke data CV siapa pun. Menghapusnya
    dari satu halaman saja justru membuat navigasi tidak konsisten.
    """
    halaman = ["/preview/admin", "/preview/admin/jobs", "/preview/admin/users",
               "/preview/admin/runs", "/preview/admin/clusters"]

    for path in halaman:
        body = _html(uiClient.get(path))
        isi = body.split("<main")[1].split("</main>")[0].lower()
        for dilarang in ("/preview/cv", "berkas cv", "unggah cv", "teks cv", "isi cv"):
            assert dilarang not in isi, f"{path} memuat {dilarang} di panel"


def test_admin_users_show_no_cv_content(uiClient) -> None:
    """Tabel pengguna tidak menampilkan isi skill atau CV (R-F05-10)."""
    body = _html(uiClient.get("/preview/admin/users"))
    tabel = body.split('<table class="data-table"')[1].split("</table>")[0]

    # Hanya JUMLAH skill yang boleh tampil, bukan daftar skillnya.
    assert "Skill" in tabel
    for isi in ("python", "sql", "figma", "docker"):
        assert isi not in tabel, f"tabel pengguna membocorkan isi skill: {isi}"


# --- R-F05-09 / R-F05-14 / R-F05-15: tabel dan dialog -------------------

def test_admin_jobs_search_and_pagination(uiClient) -> None:
    """Pencarian menyaring hasil dan pagination tersedia (R-F05-09)."""
    semua = _html(uiClient.get("/preview/admin/jobs"))
    assert semua.count("<tr data-row-id") == 5

    cari = _html(uiClient.get("/preview/admin/jobs?q=python"))
    assert "Backend Engineer (Python)" in cari
    assert "Product Designer" not in cari


def test_delete_requires_confirmation(uiClient) -> None:
    """Hapus memakai dialog konfirmasi, bukan aksi langsung (R-F05-15)."""
    body = _html(uiClient.get("/preview/admin/jobs"))

    assert "<dialog" in body
    assert 'class="confirm"' in body
    # Tombol hapus bertipe button — tidak mengirim form dan tidak langsung jalan.
    assert re.search(r'<button[^>]*class="btn btn-ghost btn-sm js-hapus"[^>]*type="button"|'
                     r'<button[^>]*type="button"[^>]*class="btn btn-ghost btn-sm js-hapus"', body)
    assert 'value="batal"' in body
    assert 'value="hapus"' in body


def test_datatable_keyboard(uiClient) -> None:
    """Tabel dapat difokus dan baris menandai id-nya (R-F05-14)."""
    for path in ("/preview/admin/jobs", "/preview/admin/users",
                 "/preview/admin/runs", "/preview/admin/clusters"):
        body = _html(uiClient.get(path))
        tabel = re.search(r'<table class="data-table"[^>]*>', body)
        assert tabel, f"{path} tidak punya data-table"
        assert 'tabindex="0"' in tabel.group(0), f"{path} tabel tidak dapat difokus"
        assert "aria-label" in tabel.group(0)
        assert "data-row-id" in body, f"{path} baris tidak menandai id"


def test_data_table_has_caption(uiClient) -> None:
    """Setiap tabel punya caption untuk pembaca layar (§5)."""
    for path in ("/preview/admin/jobs", "/preview/admin/users",
                 "/preview/admin/runs", "/preview/admin/clusters"):
        body = _html(uiClient.get(path))
        assert "<caption" in body, f"{path} tabel tanpa caption"


def test_admin_routes_are_production_since_prd09() -> None:
    """Halaman admin kini punya route produksi (PRD-09).

    Sebelum PRD-09 test ini memastikan ``/admin*`` **tidak** terdaftar di
    produksi, karena datanya belum ada. Sekarang route-nya ada; yang harus
    dijaga adalah bahwa tamu tetap tidak bisa memakainya — itu diuji di
    ``tests/unit/test_admin.py``.
    """
    jalur = {rule.rule for rule in create_app("testing").url_map.iter_rules()}

    for path in ("/admin", "/admin/jobs", "/admin/runs", "/admin/users", "/admin/clusters"):
        assert path in jalur, f"{path} belum terdaftar di produksi"

    assert "/insights" in jalur


def test_nav_marks_one_active_for_new_pages(ui, monkeypatch) -> None:
    """Insight dan seluruh halaman admin menyorot tepat satu menu.

    Halaman-halaman ini hanya muncul di nav setelah pengguna masuk, jadi
    kliennya harus login lebih dulu — tamu tidak melihatnya sama sekali.
    """
    from app.auth import repository

    store: dict[str, dict] = {}
    state = {"id": 1}

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
        row = {"id": state["id"], "email": email, "password_hash": password_hash, "name": name}
        state["id"] += 1
        store[email] = row
        return {"id": row["id"], "email": row["email"], "name": row["name"]}

    # monkeypatch: tanpa ini repository global berubah untuk test berikutnya.
    monkeypatch.setattr(repository, "find_by_email", find_by_email)
    monkeypatch.setattr(repository, "find_by_id", find_by_id)
    monkeypatch.setattr(repository, "create", create)

    client = ui.test_client()
    client.post("/auth/register",
                data={"email": "nav@example.com", "password": "rahasia123", "name": "Nav"})

    harapan = {
        "/preview/insights": "Insight",
        "/preview/admin": "Admin",
        "/preview/admin/jobs": "Admin",
        "/preview/admin/users": "Admin",
        "/preview/admin/runs": "Admin",
        "/preview/admin/clusters": "Admin",
    }
    for path, menu in harapan.items():
        body = _html(client.get(path))
        nav = re.search(r'<ul class="nav-pill">(.*?)</ul>', body, re.S).group(1)
        aktif = re.findall(r'<a[^>]*aria-current="page"[^>]*>\s*([A-Za-z]+)\s*</a>', nav)
        assert aktif == [menu], f"{path} menyorot {aktif}, seharusnya {[menu]}"


def test_admin_tabs_mark_one_active(uiClient) -> None:
    """Tab admin menyorot tepat satu bagian."""
    for path, menu in {
        "/preview/admin": "Ringkasan",
        "/preview/admin/jobs": "Lowongan",
        "/preview/admin/users": "Pengguna",
        "/preview/admin/runs": "Proses",
        "/preview/admin/clusters": "Kategori",
    }.items():
        body = _html(uiClient.get(path))
        tab = body.split('class="admin-tabs"')[1].split("</nav>")[0]
        aktif = re.findall(r'<a[^>]*aria-current="page"[^>]*>\s*([A-Za-z]+)\s*</a>', tab)
        assert aktif == [menu], f"{path} tab aktif {aktif}, seharusnya {[menu]}"
