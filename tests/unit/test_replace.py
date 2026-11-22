"""PRD-02 §7.1 (lanjutan): mode ``--replace`` dan pengamannya.

Operasi paling berbahaya di pipeline: ia menghapus baris. Test di sini menjaga
dua hal sekaligus — penghapusan berjalan saat memang seharusnya, dan **tidak**
berjalan saat pengambilan hanya berhasil sebagian.
"""

from __future__ import annotations

import pytest

from scraper import pipeline, runner
from scraper.adapters.base import RawJob


def _hasil(source: str, jumlah: int, status: str = "success"):
    """``SourceOutcome`` dengan ``jumlah`` lowongan."""
    return runner.SourceOutcome(
        source=source,
        status=status,
        jobs_found=jumlah,
        jobs=[RawJob(title=f"{source} {i}", source_url=f"https://{source}.test/{i}")
              for i in range(jumlah)],
    )


@pytest.fixture
def dihapus(monkeypatch):
    """Rekam panggilan penghapusan tanpa menyentuh database."""
    catatan: list[set[str]] = []

    monkeypatch.setattr(
        pipeline, "persist_hapus_di_luar",
        lambda url, abaikan_sumber=None: catatan.append(set(url)) or 0,
    )
    return catatan


@pytest.fixture
def tersimpan(monkeypatch):
    """Tetapkan jumlah baris yang ada di database."""
    def atur(n: int):
        monkeypatch.setattr(pipeline, "persist_hitung_tersimpan", lambda: n)
    return atur


# --- jalur normal -------------------------------------------------------

def test_replace_removes_when_similar_size(dihapus, tersimpan) -> None:
    """Hasil hari ini sebanding dengan isi database: penghapusan berjalan."""
    tersimpan(100)
    hasil = [_hasil("dealls", 95)]

    runner._replace_if_successful(hasil, hasil)

    assert len(dihapus) == 1
    assert len(dihapus[0]) == 95


def test_replace_works_when_database_grows(dihapus, tersimpan) -> None:
    """Database bertumbuh: tidak ada yang perlu diblokir."""
    tersimpan(50)
    hasil = [_hasil("dealls", 120)]

    runner._replace_if_successful(hasil, hasil)

    assert len(dihapus[0]) == 120


# --- pengaman -----------------------------------------------------------

def test_replace_blocked_when_result_drops_sharply(dihapus, tersimpan) -> None:
    """Hasil turun drastis: penghapusan DIBATALKAN.

    Penyebabnya hampir selalu pengambilan setengah berhasil — situs membatasi
    halaman, atau strukturnya berubah di tengah jalan. Menghapus ratusan baris
    karena satu kegagalan sementara jauh lebih mahal daripada mempertahankan
    data yang belum segar sehari lagi.
    """
    tersimpan(360)
    hasil = [_hasil("kalibrr", 30)]  # 8% dari isi database

    runner._replace_if_successful(hasil, hasil)

    assert dihapus == [], "penghapusan harus dibatalkan"


def test_replace_blocked_below_threshold(dihapus, tersimpan) -> None:
    """Ambangnya 60%: 59% dibatalkan, 61% dijalankan."""
    tersimpan(100)

    runner._replace_if_successful([_hasil("dealls", 59)], [_hasil("dealls", 59)])
    assert dihapus == []

    runner._replace_if_successful([_hasil("dealls", 61)], [_hasil("dealls", 61)])
    assert len(dihapus) == 1


def test_replace_runs_on_empty_database(dihapus, tersimpan) -> None:
    """Database kosong: tidak ada rasio untuk dibandingkan, jadi berjalan."""
    tersimpan(0)
    hasil = [_hasil("dealls", 20)]

    runner._replace_if_successful(hasil, hasil)

    assert len(dihapus) == 1


def test_replace_skipped_without_results(dihapus, tersimpan) -> None:
    """Tanpa satu pun lowongan: tidak menghapus apa pun."""
    tersimpan(360)

    runner._replace_if_successful([_hasil("dealls", 0, status="failed")], [])

    assert dihapus == []


def test_failed_source_is_spared(dihapus, tersimpan) -> None:
    """Sumber yang gagal tidak ikut dihapus.

    Kita tidak punya dasar untuk menyatakan lowongan itu sudah tidak tersedia;
    tanpa penjagaan ini, satu kegagalan jaringan menghapus seluruh isi sumber
    tersebut.
    """
    tersimpan(100)
    hasil = [_hasil("dealls", 90), _hasil("remotive", 0, status="failed")]

    runner._replace_if_successful(hasil, [hasil[0]])

    assert dihapus, "penghapusan masih harus berjalan untuk sumber yang berhasil"
    # `abaikan_sumber` diteruskan ke persist; nilai baliknya rekaman URL saja,
    # jadi yang diperiksa di sini adalah bahwa penghapusan tidak dibatalkan.
    assert len(dihapus[0]) == 90


def test_partial_status_counts_as_success(dihapus, tersimpan) -> None:
    """Status `partial` tetap dianggap berhasil — sebagian datanya ada."""
    tersimpan(100)
    hasil = [_hasil("dealls", 80, status="partial")]

    runner._replace_if_successful(hasil, hasil)

    assert len(dihapus) == 1
