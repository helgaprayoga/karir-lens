"""PRD-05 §7.1: statistik gaji.

Fixture kecil dan deterministik, tanpa database dan tanpa jaringan. Angka yang
diuji dipilih agar kuartil dapat diperiksa dengan tangan.
"""

from __future__ import annotations

import pytest

from app.insights import salary


def _job(smin=None, smax=None, currency="IDR", period="month", **ubah):
    dasar = {
        "salary_min": smin,
        "salary_max": smax,
        "salary_currency": currency,
        "salary_period": period,
    }
    dasar.update(ubah)
    return dasar


# --- Titik tengah --------------------------------------------------------

def test_midpoint_uses_range_center() -> None:
    """Rentang penuh memakai titik tengah, bukan batas bawah.

    Memakai `salary_min` saja akan menurunkan median secara sistematis pada
    lowongan yang punya batas atas.
    """
    assert salary.midpoint(_job(8_000_000, 12_000_000)) == 10_000_000


def test_midpoint_keeps_partial_salary() -> None:
    """Gaji parsial tetap fakta: sisi yang ada dipakai apa adanya."""
    assert salary.midpoint(_job(9_000_000, None)) == 9_000_000
    assert salary.midpoint(_job(None, 15_000_000)) == 15_000_000


def test_midpoint_rejects_missing() -> None:
    """Nol, negatif, dan kosong bukan gaji."""
    assert salary.midpoint(_job(None, None)) is None
    assert salary.midpoint(_job(0, 0)) is None
    assert salary.midpoint(_job(-5, None)) is None
    assert salary.midpoint(_job("abc", None)) is None
    assert salary.midpoint({}) is None


# --- R-05-08: sampel minimum --------------------------------------------

def test_salary_min_sample_rule() -> None:
    """Kelompok dengan sampel < 5 tidak dikembalikan."""
    empat = [_job(10_000_000) for _ in range(4)]
    assert salary.group_salaries(empat) == []

    lima = [_job(10_000_000) for _ in range(5)]
    grup = salary.group_salaries(lima)
    assert len(grup) == 1
    assert grup[0]["sample"] == 5


def test_salary_stats_flag_false_when_insufficient() -> None:
    """`sample_sufficient` False saat tidak ada kelompok memenuhi syarat."""
    hasil = salary.salary_stats([_job(10_000_000) for _ in range(3)])

    assert hasil["sample_sufficient"] is False
    assert hasil["groups"] == []
    assert hasil["minimum_sample"] == 5


def test_ungroupable_rows_do_not_count() -> None:
    """Lowongan tanpa gaji tidak menambah sampel kelompok mana pun."""
    rows = [_job(10_000_000) for _ in range(4)] + [_job(None, None) for _ in range(10)]
    assert salary.group_salaries(rows) == []


# --- R-05-09: pemisahan -------------------------------------------------

def test_salary_currency_separation() -> None:
    """Mata uang tidak dicampur dalam satu kelompok statistik."""
    rows = [_job(10_000_000, currency="IDR") for _ in range(5)]
    rows += [_job(4_000, currency="USD") for _ in range(5)]

    grup = {g["currency"]: g for g in salary.group_salaries(rows)}

    assert set(grup) == {"IDR", "USD"}
    assert grup["IDR"]["median"] == 10_000_000
    assert grup["USD"]["median"] == 4_000


def test_salary_period_separation() -> None:
    """Periode berbeda tidak dicampur.

    Rp 9.000.000/bulan dan Rp 108.000.000/tahun setara, tetapi menggabungkan
    keduanya dalam satu median menghasilkan angka yang tidak bermakna.
    """
    rows = [_job(9_000_000, period="month") for _ in range(5)]
    rows += [_job(108_000_000, period="year") for _ in range(5)]

    grup = {(g["currency"], g["period"]): g for g in salary.group_salaries(rows)}

    assert ("IDR", "month") in grup
    assert ("IDR", "year") in grup
    assert grup[("IDR", "month")]["median"] == 9_000_000
    assert grup[("IDR", "year")]["median"] == 108_000_000


def test_unknown_period_is_not_assumed_monthly() -> None:
    """Periode yang tidak disebut sumbernya TIDAK dilabeli "bulanan".

    Terukur pada data nyata: 6 lowongan USD dan 5 IDR punya sampel cukup
    tetapi tanpa periode. Dulu template menampilkan keduanya sebagai
    "bulanan" — klaim yang tidak dimiliki data. Sekarang periodenya `None`
    dan template memilih kata yang tidak mengarang.
    """
    rows = [_job(4_000, currency="USD", period=None) for _ in range(6)]
    grup = salary.group_salaries(rows)

    assert len(grup) == 1
    assert grup[0]["period"] is None
    assert grup[0]["sample"] == 6


def test_invalid_period_treated_as_unknown() -> None:
    """Periode di luar himpunan baku diperlakukan sebagai tidak diketahui."""
    rows = [_job(1_000, period="mingguan") for _ in range(5)]
    assert salary.group_salaries(rows)[0]["period"] is None


# --- R-05-09: kuartil ---------------------------------------------------

def test_salary_quartiles() -> None:
    """Median, P25, P75 dihitung benar pada fixture yang mudah diperiksa.

    Nilai 10,20,30,40,50 juta: median 30, P25 20, P75 40.
    """
    rows = [_job(n) for n in (10_000_000, 20_000_000, 30_000_000, 40_000_000, 50_000_000)]
    grup = salary.group_salaries(rows)[0]

    assert grup["sample"] == 5
    assert grup["median"] == 30_000_000
    assert grup["p25"] == 20_000_000
    assert grup["p75"] == 40_000_000


def test_quartiles_interpolate() -> None:
    """Persentil memakai interpolasi linear, sama dengan numpy.

    Enam nilai 1..6: median 3,5; P25 2,25; P75 4,75.
    """
    from app.insights.salary import _persentil

    nilai = [1, 2, 3, 4, 5, 6]
    assert _persentil(nilai, 0.5) == 3.5
    assert _persentil(nilai, 0.25) == 2.25
    assert _persentil(nilai, 0.75) == 4.75


def test_p25_below_median_below_p75() -> None:
    """Urutan kuartil selalu benar, termasuk pada sebaran tidak rata."""
    rows = [_job(n) for n in (5_000_000, 5_000_000, 6_000_000, 30_000_000, 90_000_000)]
    grup = salary.group_salaries(rows)[0]

    assert grup["p25"] <= grup["median"] <= grup["p75"]


# --- R-05-10: tanpa prediksi -------------------------------------------

def test_no_prediction_output() -> None:
    """Tidak ada field prediksi pada keluaran mana pun (R-05-10)."""
    rows = [_job(10_000_000) for _ in range(6)]
    hasil = salary.salary_stats(rows)

    terlarang = ("predict", "prediction", "estimate", "estimate_", "forecast", "expected")
    teks = repr(hasil).lower()
    for kata in terlarang:
        assert kata not in teks, f"keluaran memuat {kata!r}"

    assert set(hasil) == {"sample_sufficient", "minimum_sample", "groups"}
    assert set(hasil["groups"][0]) == {"currency", "period", "sample", "median", "p25", "p75"}


# --- Kontrak template ---------------------------------------------------

def test_contract_shape() -> None:
    """Bentuk keluaran sesuai kontrak PRD-F05 §4.1."""
    rows = [_job(9_000_000) for _ in range(5)]
    hasil = salary.salary_stats(rows)

    assert isinstance(hasil["sample_sufficient"], bool)
    assert isinstance(hasil["minimum_sample"], int)
    assert isinstance(hasil["groups"], list)
    assert all(isinstance(g, dict) for g in hasil["groups"])


def test_groups_sorted_by_sample() -> None:
    """Kelompok dengan sampel terbanyak tampil lebih dulu."""
    rows = [_job(10_000_000, currency="IDR") for _ in range(9)]
    rows += [_job(4_000, currency="USD") for _ in range(5)]

    grup = salary.group_salaries(rows)
    assert grup[0]["currency"] == "IDR"
    assert grup[0]["sample"] == 9


def test_empty_input() -> None:
    """Data kosong menghasilkan flag False, bukan error."""
    hasil = salary.salary_stats([])
    assert hasil == {"sample_sufficient": False, "minimum_sample": 5, "groups": []}
