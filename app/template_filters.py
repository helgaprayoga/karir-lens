"""Filter Jinja untuk format tanggal dan angka Indonesia.

Filter ini mengikuti pola proyek referensi Bot Rekap Lowongan Dealls
(``app.py`` — ``@app.template_filter("tanggal")`` dan ``"angka"``), yang
dipakai PRD-F01 sebagai acuan. Semua format berbahasa Indonesia agar
konsisten dengan R-F01-10.

Modul ini hanya memformat; tidak membaca konfigurasi aplikasi maupun data.
"""

from __future__ import annotations

import re
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


def description_blocks(value) -> list[dict]:
    """Teks deskripsi -> blok berjudul, dikenali dari **bentuk** teksnya.

    Tiga sumber KarirLens menulis deskripsi dengan cara berbeda:

    - Kalibrr: subjudul menempel ("About this Position", "Responsibilities")
      dan butir dipisah baris.
    - Remotive: subjudul frasa pendek ("Role Description", "Qualifications").
    - Dealls: penomoran ("1. Planning") atau paragraf biasa.

    Baris dianggap judul bila pendek, tanpa tanda baca akhir, tidak diawali
    penanda butir, **dan tidak berbentuk "kunci: nilai"**. Pengenalan lewat
    bentuk — bukan nama sumber — supaya sumber baru tidak menuntut kode
    tambahan.

    Kembalian: ``[{"title": str|None, "butir": [str], "text": str}]``. Kunci
    bernama ``butir``, bukan ``items``: di Jinja, ``blok.items`` menunjuk method
    ``dict.items`` dan itulah yang terpanggil, bukan daftar butirnya. Blok
    dengan ``butir`` terisi dirender sebagai daftar, selain itu paragraf.
    """
    teks = str(value or "").strip()
    if not teks:
        return []

    # Penanda butir yang umum di ketiga sumber. Penomoran ("1. Planning")
    # SENGAJA tidak termasuk: Dealls memakainya sebagai judul bagian, dan
    # memperlakukannya sebagai butir membuat seluruh strukturnya hilang.
    butir_re = re.compile(r"^\s*(?:[-•*·–—])\s+")
    # "Auslastung: Vollzeit" adalah pasangan kunci-nilai, bukan judul bagian.
    kunci_nilai_re = re.compile(r"^[^:]{1,40}:\s+\S")

    def adalah_judul(baris: str) -> bool:
        bersih = baris.strip()
        if not bersih or len(bersih) > 60:
            return False
        # Baris berakhiran ":" adalah pengantar bagian ("...include:").
        if bersih.endswith(":"):
            return True
        if butir_re.match(bersih):
            return False
        if kunci_nilai_re.match(bersih):
            return False
        # Judul tidak berakhir dengan tanda baca kalimat.
        if bersih[-1] in ".:;,!?":
            return False
        # Harus sedikit kata: judul bukan kalimat.
        return len(bersih.split()) <= 6

    def gelar_kata(baris: str) -> str:
        """Rapikan judul: buang titik dua di ujung, jaga kapitalisasi aslinya."""
        return baris.strip().rstrip(":").strip()

    blok: list[dict] = []
    judul: str | None = None
    butir: list[str] = []
    paragraf: list[str] = []

    def tutup() -> None:
        nonlocal butir, paragraf
        if butir:
            blok.append({"title": judul, "butir": butir, "text": ""})
            butir = []
        elif paragraf:
            blok.append({"title": judul, "butir": [], "text": " ".join(paragraf)})
            paragraf = []

    for baris in teks.splitlines():
        bersih = " ".join(baris.split())
        if not bersih:
            continue
        if adalah_judul(bersih) and not paragraf and not butir:
            # Judul langsung setelah judul sebelumnya: blok kosong, abaikan.
            judul = gelar_kata(bersih)
            continue
        if adalah_judul(bersih) and (paragraf or butir):
            tutup()
            judul = gelar_kata(bersih)
            continue

        cocok = butir_re.match(bersih)
        if cocok:
            butir.append(bersih[cocok.end():].strip())
        elif butir:
            # Baris tanpa penanda setelah butir: lanjutan butir terakhir.
            butir[-1] = (butir[-1] + " " + bersih).strip()
        else:
            paragraf.append(bersih)

    tutup()

    # Satu paragraf utuh: deskripsi Kalibrr yang tersimpan sebelum adapter
    # memperbaiki pembersihnya (PRD-02) kehilangan semua baris. Coba pecah pada
    # subjudul yang dikenal; hasilnya dipakai hanya bila benar-benar terpecah.
    # Datanya sendiri baru benar setelah pengambilan ulang.
    if len(blok) == 1 and not blok[0]["butir"]:
        pecah = _pecah_judul_inline(blok[0]["text"])
        if len(pecah) > 1:
            return pecah

    return blok


# Subjudul yang lazim muncul di tengah teks yang kehilangan baris. Dimulai
# dengan huruf kapital dan didahului akhir kalimat, supaya kata yang sama di
# tengah kalimat tidak ikut terpecah.
_JUDUL_INLINE = re.compile(
    r"(?<=[.!?:])\s+"
    r"(About (?:us|this Position|the Role|the Company|Astro)"
    r"|Job Description|Role Description|Responsibilities"
    r"|Qualifications|Requirements|Benefits"
    r"|What You(?:'|’)?ll (?:Do|Be Doing)|Nice to Have|Your Application)"
)


def _pecah_judul_inline(teks: str) -> list[dict]:
    """Pecah satu paragraf panjang pada subjudul yang dikenal.

    Jalan terakhir untuk data lama yang barisnya sudah hilang. Judulnya adalah
    frasa yang cocok **persis** — bukan kalimat sesudahnya.

    Kalau tidak ada subjudul yang cocok, kembalikan satu blok utuh: menebak
    batas kalimat akan memotong teks di tengah.
    """
    bagian = _JUDUL_INLINE.split(teks)
    if len(bagian) < 2:
        return [{"title": None, "butir": [], "text": teks}]

    hasil: list[dict] = []
    pembuka = bagian[0].strip()
    if pembuka:
        hasil.append({"title": None, "butir": [], "text": pembuka})

    # `split` dengan grup tangkap menyisipkan judul dan isinya bergantian.
    for i in range(1, len(bagian), 2):
        judul = bagian[i].strip()
        isi = bagian[i + 1].strip() if i + 1 < len(bagian) else ""
        hasil.append({"title": judul, "butir": [], "text": isi})
    return hasil


FILTERS = {
    "tanggal": tanggal,
    "tanggal_relatif": tanggal_relatif,
    "angka": angka,
    "persen": persen,
    "description_blocks": description_blocks,
}
