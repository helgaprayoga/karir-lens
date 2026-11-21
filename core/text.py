"""Normalisasi teks yang dipakai bersama pipeline data dan ekstraksi CV.

PRD-03 memakai modul ini untuk menormalkan field lowongan; PRD-07 memakai
aturan yang sama untuk skill CV (R-07-04), sehingga implementasinya hanya satu.

Semua fungsi di sini murni: tidak menyentuh database, jaringan, atau waktu.
"""

from __future__ import annotations

import html as html_module
import re
import unicodedata

# `+`, `#`, dan `.` dipertahankan agar `c++`, `c#`, dan `node.js` tidak rusak.
_NON_WORD = re.compile(r"[^a-z0-9\s+#.]")
_WHITESPACE = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")

# Baris kosong berlebih: tiga newline atau lebih menjadi dua.
_BLANK_LINES = re.compile(r"\n\s*\n\s*\n+")


def decode_entities(value: str | None) -> str:
    """Decode ``&amp;``, ``&nbsp;``, dan sejenisnya."""
    if not value:
        return ""
    return html_module.unescape(str(value))


def strip_html(value: str | None) -> str:
    """Buang tag HTML; pertahankan batas baris pada akhir blok dan butir.

    Tanpa ``</li>``/``</p>`` -> newline, deskripsi berbutir menempel menjadi
    satu paragraf panjang dan tidak terbaca.
    """
    if not value:
        return ""
    teks = re.sub(r"(?i)<br\s*/?>", "\n", str(value))
    teks = re.sub(r"(?i)</(li|p|h[1-6]|div|tr)>", "\n", teks)
    teks = _TAG.sub(" ", teks)
    return decode_entities(teks)


def collapse(value: str | None) -> str:
    """Rapikan spasi ganda dan baris kosong berlebih, lalu trim."""
    if not value:
        return ""
    rapi = _WHITESPACE.sub(" ", str(value)).strip()
    return rapi


def clean_text(value: str | None) -> str:
    """Teks tampilan bersih: entity di-decode, tag dibuang, spasi dirapikan.

    Dipakai untuk ``title`` dan ``company_name`` (R-03-02). Kapitalisasi asli
    dipertahankan karena "PT" dan "pt" bisa berbeda arti bagi pembaca.
    """
    if not value:
        return ""
    return collapse(strip_html(value))


def clean_multiline(value: str | None, max_length: int | None = None) -> str:
    """Teks panjang: tag dibuang, baris dirapikan, panjangnya dibatasi.

    Dipakai untuk ``description`` (R-03-05). Pemotongan dilakukan pada batas
    kata bila mungkin, dan penanda ``…`` ditambahkan agar jelas terpotong —
    lebih baik daripada kalimat yang berhenti di tengah kata tanpa keterangan.
    """
    if not value:
        return ""

    teks = strip_html(value)
    baris = [collapse(b) for b in teks.splitlines()]
    teks = "\n".join(b for b in baris if b)
    teks = _BLANK_LINES.sub("\n\n", teks).strip()

    if max_length and len(teks) > max_length:
        potong = teks[: max_length - 1]
        spasi = potong.rfind(" ")
        if spasi > max_length * 0.8:
            potong = potong[:spasi]
        teks = potong.rstrip() + "…"
    return teks


def normalize_text(value: str | None) -> str:
    """Huruf kecil, buang aksen dan tanda baca, rapikan spasi.

    ``+``, ``#``, dan ``.`` dipertahankan agar ``c++``, ``c#``, dan ``node.js``
    tidak rusak menjadi token yang salah.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower()
    cleaned = _NON_WORD.sub(" ", lowered)
    return _WHITESPACE.sub(" ", cleaned).strip()


def slugify(value: str | None) -> str:
    """Slug stabil untuk ``company_slug`` dan URL halaman perusahaan (R-03-03).

    Aturannya: lowercase, ``[^a-z0-9]+`` menjadi ``-``, tanpa ``-`` di ujung.
    Berbeda dari :func:`normalize_text` yang sengaja mempertahankan ``.``/``#``/
    ``+`` untuk nama skill: pada slug, "PT. Digivana" harus menjadi
    ``pt-digivana``, bukan ``pt.-digivana``.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    tanpa_aksen = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", tanpa_aksen.lower())
    return slug.strip("-")


def tokenize(value: str | None) -> list[str]:
    """Token teks yang sudah dinormalkan."""
    normalized = normalize_text(value)
    return normalized.split() if normalized else []


def split_location(value: str | None) -> tuple[str | None, str | None]:
    """Pisahkan lokasi menjadi ``(kota, negara)`` bila bentuknya mendukung.

    Sumber memakai dua gaya: "South Jakarta, Indonesia" (kota, negara) dan
    "USA, Canada, USA timezones" (daftar negara). Yang kedua bukan pasangan
    kota-negara, jadi tidak dipecah — memecahnya akan menghasilkan "kota"
    bernama "USA" dan "negara" bernama "Canada", keduanya salah.
    """
    teks = clean_text(value)
    if not teks:
        return None, None

    bagian = [b.strip() for b in teks.split(",") if b.strip()]
    if len(bagian) != 2:
        return None, None

    kota, negara = bagian
    # Penanda daftar negara: dua huruf besar semua, atau ada "+N more".
    if len(kota) <= 3 and kota.isupper():
        return None, None
    if "more" in negara.lower():
        return None, None
    return kota, negara
