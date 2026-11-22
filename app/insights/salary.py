"""Statistik gaji faktual: median, P25, P75, jumlah sampel (PRD-05).

Aturan yang tinggal di sini, semuanya dari §4.1 PRD:

- Hanya lowongan yang mencantumkan gaji.
- Statistik disembunyikan bila sampel < 5 (R-05-08).
- Mata uang tidak dicampur (R-05-09).
- Tidak ada field prediksi (R-05-10).

Modul ini murni: menerima daftar baris, mengembalikan dict. Tidak menyentuh
database maupun jaringan, sehingga aturan sampel dan kuartil dapat diuji dengan
fixture kecil yang deterministik (§7.1).
"""

from __future__ import annotations

import math

MIN_SALARY_SAMPLE = 5

# Periode yang diakui. Nilai di luar ini tidak digabung ke "bulanan": periode
# yang tidak disebutkan sumbernya bukan bulanan, dan menampilkannya sebagai
# bulanan adalah klaim yang tidak dimiliki data.
PERIODS = ("month", "year", "hour", "day", "project")

# Urutan tampil: periode terpendek dulu agar kartu bulanan muncul sebelum
# tahunan, dan "tidak diketahui" paling akhir.
_PERIOD_ORDER = {p: i for i, p in enumerate(PERIODS)}


def midpoint(row: dict) -> float | None:
    """Nilai gaji satu lowongan, atau ``None`` bila tidak layak dihitung.

    Memakai titik tengah rentang, karena ``salary_min`` saja akan menurunkan
    median secara sistematis pada lowongan yang punya batas atas. Bila hanya
    satu sisi yang ada, sisi itu dipakai apa adanya — gaji parsial tetap fakta.

    Nol dan negatif dibuang: itu ketiadaan data, bukan gaji.
    """
    if not isinstance(row, dict):
        return None

    def _angka(nilai) -> float | None:
        try:
            n = float(nilai)
        except (TypeError, ValueError):
            return None
        return n if n > 0 and math.isfinite(n) else None

    bawah = _angka(row.get("salary_min"))
    atas = _angka(row.get("salary_max"))

    if bawah is not None and atas is not None:
        return (bawah + atas) / 2
    return bawah if bawah is not None else atas


def _persentil(nilai: list[float], p: float) -> float:
    """Persentil dengan interpolasi linear (metode yang sama dengan numpy).

    Dihitung sendiri agar modul ini tidak menambah dependensi untuk satu
    operasi aritmetika, dan agar hasilnya dapat diuji tanpa numpy.
    """
    urut = sorted(nilai)
    if not urut:
        return 0.0
    if len(urut) == 1:
        return urut[0]

    posisi = (len(urut) - 1) * p
    bawah = math.floor(posisi)
    atas = math.ceil(posisi)
    if bawah == atas:
        return urut[int(posisi)]

    bobot = posisi - bawah
    return urut[bawah] * (1 - bobot) + urut[atas] * bobot


def group_salaries(rows: list[dict]) -> list[dict]:
    """Kelompokkan gaji per ``(currency, period)``, buang kelompok kecil.

    Pemisahan **per mata uang dan per periode** sekaligus: Rp 9.000.000/bulan
    dan USD 4.200/bulan tidak sebanding, dan Rp 108.000.000/tahun bukan angka
    yang sama dengan Rp 9.000.000/bulan walau setara. Menggabungkannya akan
    menghasilkan median yang tidak bermakna apa pun.
    """
    kelompok: dict[tuple[str | None, str | None], list[float]] = {}

    for row in rows or []:
        nilai = midpoint(row)
        if nilai is None:
            continue

        mata_uang = (row.get("salary_currency") or "").strip().upper() or None
        periode = (row.get("salary_period") or "").strip().lower() or None
        if periode not in PERIODS:
            periode = None

        kelompok.setdefault((mata_uang, periode), []).append(nilai)

    hasil = []
    for (mata_uang, periode), nilai in kelompok.items():
        if len(nilai) < MIN_SALARY_SAMPLE:
            continue

        hasil.append(
            {
                "currency": mata_uang,
                "period": periode,
                "sample": len(nilai),
                "median": round(_persentil(nilai, 0.5)),
                "p25": round(_persentil(nilai, 0.25)),
                "p75": round(_persentil(nilai, 0.75)),
            }
        )

    # Urutan stabil: sampel terbanyak dulu, lalu mata uang, lalu periode.
    hasil.sort(
        key=lambda g: (
            -g["sample"],
            g["currency"] or "zzz",
            _PERIOD_ORDER.get(g["period"], len(PERIODS)),
        )
    )
    return hasil


def salary_stats(rows: list[dict]) -> dict:
    """Bentuk ``salary`` pada kontrak PRD-F05 §4.1.

    ``sample_sufficient`` bernilai ``False`` bila tidak ada satu kelompok pun
    yang memenuhi syarat — template memakainya untuk menampilkan pesan data
    terbatas alih-alih grafik kosong (R-05-11).

    Tidak ada kunci ``prediction``, ``estimate``, atau sejenisnya di mana pun
    (R-05-10); angka yang keluar selalu hasil hitung dari baris yang ada.
    """
    grup = group_salaries(rows)
    return {
        "sample_sufficient": bool(grup),
        "minimum_sample": MIN_SALARY_SAMPLE,
        "groups": grup,
    }
