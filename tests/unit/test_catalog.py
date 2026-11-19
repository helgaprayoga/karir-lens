"""Pengujian katalog publik (PRD-F02 §7.1, R-F02-01 s.d. R-F02-17).

Halaman dirender lewat blueprint preview dengan fixture, sehingga test berjalan
tanpa database dan tanpa jaringan. Kontraknya sama dengan yang harus dipenuhi
PRD-04, jadi test ini tetap berlaku setelah backend terpasang.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP


def _app_with_preview():
    CONFIG_MAP["preview_catalog"] = type(
        "PreviewCatalog", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True}
    )
    return create_app("preview_catalog")


@pytest.fixture
def catalog():
    return _app_with_preview().test_client()


def _html(resp) -> str:
    return resp.get_data(as_text=True)


# --- R-F02-01: halaman katalog lengkap -----------------------------------

def test_jobs_list_renders_cards(catalog) -> None:
    """/jobs merender satu JobCard per item fixture."""
    body = _html(catalog.get("/preview/jobs"))
    assert body.count('class="job-card"') >= 1
    assert 'class="filters"' in body
    assert "search-field" in body
    assert 'class="pager"' in body


# --- R-F02-02: anatomi kartu --------------------------------------------

def test_job_card_anatomy_order(catalog) -> None:
    """Urutan elemen kartu: perusahaan → judul → meta → deskripsi → tag → gaji."""
    body = _html(catalog.get("/preview/jobs"))
    kartu = body.split('class="job-card"')[1]

    posisi = [
        kartu.index('class="company"'),
        kartu.index('class="source-badge"'),
        kartu.index("<h3>"),
        kartu.index('class="meta"'),
        kartu.index('class="desc"'),
        kartu.index('class="tags"'),
        kartu.index('class="pay"'),
    ]
    assert posisi == sorted(posisi), f"Anatomi kartu tidak berurutan: {posisi}"


# --- R-F02-04: badge sumber sesuai token --------------------------------

@pytest.mark.parametrize("sumber", ["dealls", "kalibrr", "remotive"])
def test_source_badge_per_source(catalog, sumber) -> None:
    """Tiga sumber menghasilkan titik warna token yang benar.

    Halaman 1 hanya memuat sebagian item, jadi halaman 2 ikut diperiksa —
    Remotive ada di sana.
    """
    body = _html(catalog.get("/preview/jobs")) + _html(catalog.get("/preview/jobs?page=2"))
    assert f'data-source="{sumber}"' in body


def test_source_colors_use_tokens() -> None:
    """Titik sumber memakai custom property, bukan nilai hex (R-F01-01)."""
    css = open("static/css/components.css", encoding="utf-8").read()
    for sumber in ("dealls", "kalibrr", "remotive"):
        blok = css.split(f'.source-badge[data-source="{sumber}"]')[1].split("}")[0]
        assert f"var(--source-{sumber})" in blok
        assert not re.search(r"#[0-9a-fA-F]{3,6}", blok)


# --- R-F02-05: varian gaji ---------------------------------------------

def test_salary_range_variants(catalog) -> None:
    """Empat varian gaji terender benar.

    Fixture disusun agar keempat varian tersebar di dua halaman: rentang dan
    "Mulai" di halaman 1, "Sampai" dan "tidak dicantumkan" di halaman 2.
    """
    halaman_1 = _html(catalog.get("/preview/jobs"))
    halaman_2 = _html(catalog.get("/preview/jobs?page=2"))
    semua = halaman_1 + halaman_2

    assert "–" in semua, "rentang min–max tidak ditemukan"
    assert "Mulai" in semua, "varian 'hanya min' tidak ditemukan"
    assert "Sampai" in semua, "varian 'hanya max' tidak ditemukan"
    assert "Gaji tidak dicantumkan" in semua, "varian 'tanpa gaji' tidak ditemukan"


# --- R-F02-03: deskripsi dua baris -------------------------------------

def test_description_clamped(catalog) -> None:
    """Kelas deskripsi dua baris diterapkan pada kartu."""
    body = _html(catalog.get("/preview/jobs"))
    assert 'class="desc"' in body
    css = open("static/css/components.css", encoding="utf-8").read()
    blok = css.split(".job-card .desc {")[1].split("}")[0]
    assert "-webkit-line-clamp: 2" in blok


# --- R-F02-08 / R-F02-09: state kosong dan loading ----------------------

def test_empty_state_rendered(catalog) -> None:
    """Fixture kosong memicu EmptyState, bukan area kosong."""
    body = _html(catalog.get("/preview/jobs?empty=1"))
    assert 'class="empty"' in body
    assert "Hapus semua filter" in body
    assert 'class="job-card"' not in body


def test_skeleton_state(catalog) -> None:
    """`is_loading` memicu SkeletonCard tanpa teks palsu."""
    body = _html(catalog.get("/preview/jobs?loading=1"))
    assert "skeleton-card" in body
    assert 'class="job-card"' not in body
    # Skeleton tidak boleh menampilkan judul lowongan.
    assert 'class="company"' not in body


# --- R-F02-07: pagination ----------------------------------------------

def test_pagination_meta(catalog) -> None:
    """Rentang dan tombol sesuai meta."""
    body = _html(catalog.get("/preview/jobs"))
    assert re.search(r"Menampilkan 1–4 dari 6 lowongan", body)
    assert "Halaman berikutnya" in body
    assert 'aria-current="page"' in body


# --- R-F02-06: chip filter aktif ---------------------------------------

def test_filter_chips_active(catalog) -> None:
    """Chip aktif menandai aria-pressed="true" dan punya tombol hapus."""
    body = _html(catalog.get("/preview/jobs?city=Bandung"))
    assert 'aria-pressed="true"' in body
    aktif = body.split('aria-pressed="true"')[1]
    assert 'class="remove"' in aktif


def test_filter_removes_itself(catalog) -> None:
    """Chip aktif menautkan ke URL tanpa filter itu (toggle)."""
    body = _html(catalog.get("/preview/jobs?city=Bandung"))
    assert 'href="/preview/jobs"' in body, "tautan penghapus filter tidak ada"


def test_chip_has_no_lying_caret(catalog) -> None:
    """Chip tidak menampilkan caret ▾ yang menjanjikan dropdown (§2 prinsip 2).

    Panel pilihan belum ada, sehingga caret akan menjadi state yang menipu.
    Hanya chip yang benar-benar terapan yang boleh menampilkan ikon ×.
    """
    body = _html(catalog.get("/preview/jobs"))
    assert 'class="caret"' not in body

    # Batasi pemeriksaan ke elemen chip: tombol simpan juga memakai
    # aria-pressed dan akan mengacaukan hitungan bila tidak dipisah.
    chips = re.findall(r'<a class="chip"[^>]*aria-pressed="(true|false)"', body)
    assert chips, "chip filter tidak ditemukan"
    assert chips.count("true") == 0, "tanpa filter aktif tidak boleh ada chip terapan"

    aktif = _html(catalog.get("/preview/jobs?city=Bandung"))
    chips_aktif = re.findall(r'<a class="chip"[^>]*aria-pressed="(true|false)"', aktif)
    assert chips_aktif.count("true") == 1
    assert aktif.count('class="remove"') == 1


def test_search_and_filter_narrow_results(catalog) -> None:
    """Pencarian dan filter benar-benar mengubah jumlah hasil."""
    penuh = _html(catalog.get("/preview/jobs"))
    sempit = _html(catalog.get("/preview/jobs?q=python"))
    assert penuh.count('class="job-card"') > sempit.count('class="job-card"')


# --- R-F02-11 / R-F02-12: detail lowongan ------------------------------

def test_job_detail_renders(catalog) -> None:
    """Detail merender seluruh field dan tautan asli."""
    body = _html(catalog.get("/preview/jobs/1"))
    for penanda in ('class="source-badge"', 'class="tags"', 'class="pay"',
                    "Deskripsi pekerjaan", "Buka di"):
        assert penanda in body, f"Detail tidak memuat {penanda}"
    assert "https://dealls.com/loker/" in body, "tautan sumber asli tidak ada"


def test_job_detail_has_similar(catalog) -> None:
    """Detail menampilkan lowongan serupa, maksimum 6."""
    body = _html(catalog.get("/preview/jobs/6"))
    assert "Lowongan serupa" in body
    assert body.count('class="job-card"') <= 6


def test_job_detail_not_found(catalog) -> None:
    assert catalog.get("/preview/jobs/9999").status_code == 404


# --- R-F02-13 / R-F02-14: halaman perusahaan ---------------------------

def test_company_page_no_external_profile(catalog) -> None:
    """Tidak ada logo, rating, jumlah karyawan, atau alamat di markup."""
    body = _html(catalog.get("/preview/companies/novatech-labs")).lower()
    for dilarang in ("logo", "rating", "jumlah karyawan", "karyawan", "alamat"):
        assert dilarang not in body, f"Halaman perusahaan memuat data eksternal: {dilarang}"


def test_company_page_from_jobs_only(catalog) -> None:
    """Halaman perusahaan menampilkan ringkasan dan daftar lowongan."""
    body = _html(catalog.get("/preview/companies/novatech-labs"))
    assert "NovaTech Labs" in body
    assert "Lowongan tersedia" in body
    assert "Skill yang sering muncul" in body
    assert 'class="job-card"' in body


def test_company_not_found(catalog) -> None:
    assert catalog.get("/preview/companies/tidak-ada-xyz").status_code == 404


# --- R-F02-16: publik tanpa login -------------------------------------

@pytest.mark.parametrize(
    "path",
    ["/preview/home", "/preview/jobs", "/preview/jobs/1", "/preview/companies/novatech-labs"],
)
def test_public_pages_no_auth(catalog, path) -> None:
    """Semua route katalog 200 tanpa login."""
    resp = catalog.get(path)
    assert resp.status_code == 200


# --- Beranda katalog ---------------------------------------------------

def test_home_renders_stats_and_latest(catalog) -> None:
    """/preview/home menampilkan hero, statistik, lowongan terbaru, kategori."""
    body = _html(catalog.get("/preview/home"))
    assert "1.842" in body, "statistik jumlah lowongan memakai filter angka"
    assert "Lowongan terbaru" in body
    assert "Pintasan kategori" in body
    assert 'class="category-card"' in body


# --- R-F02-17: MatchBadge tidak pernah berdiri sendiri ----------------

def test_match_badge_never_alone() -> None:
    """Tanpa alasan, MatchBadge tidak dirender (§4.5, R-07-10)."""
    app = _app_with_preview()
    with app.test_request_context("/"):
        macro = app.jinja_env.get_template(
            "components/match_badge.html"
        ).module.__dict__["match_badge"]
        assert macro(82, []).strip() == ""
        assert macro(82, ["python"]).strip() != ""
