"""Pencarian: tombol Cari, pintasan Ctrl K, dan kepala kartu gaji.

Tiga hal yang sebelumnya hanya tampilan:

- `kbd>Ctrl K` di kolom pencarian adalah teks dekorasi; tidak ada handler yang
  memfokuskannya.
- Halaman katalog tidak punya tombol submit eksplisit, sehingga pengguna ponsel
  harus menekan Enter pada papan ketik.
- Kepala kartu gaji menaruh sampel di kanan judul, sehingga posisinya bergeser
  mengikuti panjang label kategori dan kartu tidak identik.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP


@pytest.fixture(scope="module")
def ui():
    CONFIG_MAP["search_test"] = type(
        "SearchTest", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True, "WTF_CSRF_ENABLED": False}
    )
    app = create_app("search_test")
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def klien(ui):
    return ui.test_client()


def _html(respons) -> str:
    return respons.get_data(as_text=True)


# --- Tombol Cari ---------------------------------------------------------

def test_catalog_has_search_submit_button(klien) -> None:
    """Halaman katalog punya tombol "Cari" di dalam form pencarian."""
    body = _html(klien.get("/jobs"))

    form = re.search(r'<form class="search-field".*?</form>', body, re.S)
    assert form, "form pencarian tidak ditemukan"
    assert 'class="btn btn-primary btn-sm search-submit"' in form.group(0)
    assert ">Cari<" in form.group(0)


def test_submit_button_is_type_submit(klien) -> None:
    """Tombol harus men-submit form, bukan tombol mati tanpa aksi."""
    body = _html(klien.get("/jobs"))
    tombol = re.search(r"<button[^>]*search-submit[^>]*>", body)

    assert tombol and 'type="submit"' in tombol.group(0)


def test_input_carries_shortcut_hook(klien) -> None:
    """Input punya `data-search-input` agar pintasan dapat menemukannya."""
    body = _html(klien.get("/jobs"))

    assert "data-search-input" in body


# --- Pintasan Ctrl K ----------------------------------------------------

def test_ctrl_k_handler_exists(ui) -> None:
    """Ada handler keydown untuk Ctrl K di layout dasar.

    Diperiksa dari sumber skrip: tanpa handler, `kbd>Ctrl K` hanya janji palsu
    — dan itu persis keadaan sebelum perbaikan ini.
    """
    body = _html(ui.test_client().get("/jobs"))

    assert "ctrlKey" in body and "metaKey" in body, "pintasan ⌘K/Ctrl K tidak ditangani"
    assert "data-search-input" in body
    # Handler harus memfokuskan input, bukan sekadar mencegah bawaan peramban.
    assert ".focus()" in body


def test_shortcut_ignores_slash_while_typing(ui) -> None:
    """`/` tidak mencuri fokus saat pengguna sedang mengetik di kolom lain."""
    body = _html(ui.test_client().get("/jobs"))

    assert "isContentEditable" in body, "penjaga kolom input tidak ada"


# --- Kepala kartu gaji --------------------------------------------------

def test_salary_card_head_is_three_stacked_lines(klien) -> None:
    """Kategori, mata uang, dan sampel tersusun bertumpuk, bukan satu baris."""
    body = _html(klien.get("/preview/insights"))

    kartu = re.findall(r'<section class="panel salary-card">(.*?)</section>', body, re.S)
    assert kartu, "tidak ada kartu gaji untuk diperiksa"

    for isi in kartu:
        kepala = re.search(r'<div class="salary-head">(.*?)</div>', isi, re.S)
        assert kepala, "kepala kartu gaji tidak memakai .salary-head"
        blok = kepala.group(1)
        assert 'class="salary-category"' in blok
        assert 'class="salary-currency"' in blok
        assert 'class="salary-sample"' in blok

        # Urutan tetap: kategori, lalu mata uang, lalu sampel.
        posisi = [
            blok.index("salary-category"),
            blok.index("salary-currency"),
            blok.index("salary-sample"),
        ]
        assert posisi == sorted(posisi), "urutan kepala kartu tidak konsisten"


def test_salary_sample_not_beside_title(klien) -> None:
    """Sampel tidak lagi menempel di kanan judul (posisinya jadi bergeser)."""
    body = _html(klien.get("/preview/insights"))

    for isi in re.findall(r'<section class="panel salary-card">(.*?)</section>', body, re.S):
        kepala = re.search(r'<div class="salary-head">(.*?)</div>', isi, re.S)
        assert kepala
        # `panel-head` adalah baris flex lama yang menaruh sub di kanan judul.
        assert "panel-head" not in kepala.group(1)
