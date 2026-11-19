"""Filter Jinja untuk format tanggal dan angka Indonesia.

Filter ini mengikuti pola proyek referensi Bot Rekap Lowongan Dealls
(``app.py`` — ``@app.template_filter("tanggal")`` dan ``"angka"``), yang
dipakai PRD-F01 sebagai acuan. Semua format berbahasa Indonesia agar
konsisten dengan R-F01-10.

Modul ini hanya memformat; tidak membaca konfigurasi aplikasi maupun data.
"""

from __future__ import annotations

from datetime import datetime, timezone

BULAN_PENDEK = (
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
)


def _parse(value) -> datetime | None:
    """Ubah string ISO atau objek datetime menjadi ``datetime`` UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    teks = value.strip().replace("Z", "+00:00")
    try:
        hasil = datetime.fromisoformat(teks)
    except ValueError:
        return None
    return hasil if hasil.tzinfo else hasil.replace(tzinfo=timezone.utc)


def tanggal(value, format: str = "%d %b %Y, %H:%M") -> str:
    """``2026-11-18T09:00:00Z`` -> ``18 Nov 2026, 09:00``."""
    waktu = _parse(value)
    if waktu is None:
        return "-" if value is None else str(value)
    lama = waktu.strftime(format)
    for i, singkat in enumerate(BULAN_PENDEK, start=1):
        lama = lama.replace(
            ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[i - 1],
            singkat,
        )
    return lama


def tanggal_relatif(value) -> str:
    """Waktu relatif berbahasa Indonesia: "2 jam lalu", "3 hari lalu"."""
    waktu = _parse(value)
    if waktu is None:
        return ""

    sekarang = datetime.now(timezone.utc)
    selisih = (sekarang - waktu).total_seconds()
    if selisih < 0:
        return "baru saja"

    menit = int(selisih // 60)
    if menit < 1:
        return "baru saja"
    if menit < 60:
        return f"{menit} menit lalu"

    jam = menit // 60
    if jam < 24:
        return f"{jam} jam lalu"

    hari = jam // 24
    if hari < 30:
        return f"{hari} hari lalu"

    bulan = hari // 30
    if bulan < 12:
        return f"{bulan} bulan lalu"

    return f"{bulan // 12} tahun lalu"


def angka(value) -> str:
    """``12345`` -> ``12.345`` (pemisah ribuan gaya Indonesia, R-04-11)."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def persen(value) -> str:
    """``0.615`` -> ``61,5%`` atau ``61`` -> ``61%``."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    if n <= 1:
        n *= 100
    teks = f"{n:.1f}".rstrip("0").rstrip(".")
    return teks.replace(".", ",") + "%"


FILTERS = {
    "tanggal": tanggal,
    "tanggal_relatif": tanggal_relatif,
    "angka": angka,
    "persen": persen,
}
