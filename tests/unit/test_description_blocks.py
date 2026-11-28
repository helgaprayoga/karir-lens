"""PRD-F02 R-F02-11: deskripsi detail mengikuti bentuk tiap sumber.

Ketiga sumber menulis deskripsi dengan cara berbeda, dan meratakannya menjadi
satu paragraf membuang struktur yang sudah ada di data. Filter
``description_blocks`` memecahnya menjadi blok berjudul + butir, dikenali dari
bentuk teksnya — bukan dari nama sumbernya.
"""

from __future__ import annotations

from app.template_filters import description_blocks


def test_kalibrr_subheadings_become_sections() -> None:
    """Kalibrr: "About this Position" dan "Responsibilities" jadi subjudul."""
    teks = (
        "About Astro ASTRO is Indonesia's quick commerce company.\n"
        "About this Position\n"
        "We're looking for a Product Designer with strong visual taste.\n"
        "Responsibilities\n"
        "Own the end-to-end product design process.\n"
        "Conduct user research and usability testing."
    )
    blok = description_blocks(teks)

    judul = [b["title"] for b in blok if b["title"]]
    assert "About this Position" in judul
    assert "Responsibilities" in judul


def test_remotive_subheadings_with_paragraphs() -> None:
    """Remotive: subjudul diikuti paragraf, bukan butir."""
    teks = (
        "Role Description\n"
        "Megaport is building a serverless edge compute platform that runs customer workloads.\n"
        "Qualifications\n"
        "Strong Go, with services you have built and run in production for years."
    )
    blok = description_blocks(teks)

    assert [b["title"] for b in blok] == ["Role Description", "Qualifications"]
    assert all(not b["butir"] for b in blok), "Remotive memakai paragraf, bukan butir"


def test_dealls_numbered_sections() -> None:
    """Dealls: penomoran "1. Planning" menjadi judul bagian.

    Baris prosa sesudahnya menjadi paragraf, bukan butir: Dealls menulis
    kalimat lengkap, bukan daftar berpenanda.
    """
    teks = (
        "1. Planning\n"
        "Collaborate with Product Owners to understand features.\n"
        "Estimate story points and contribute to capacity planning.\n"
        "2. Development & Testing\n"
        "Write clean, maintainable, and scalable code."
    )
    blok = description_blocks(teks)

    judul = [b["title"] for b in blok]
    assert judul == ["1. Planning", "2. Development & Testing"]
    assert "Product Owners" in blok[0]["text"]


def test_key_value_line_is_not_a_heading() -> None:
    """Baris "Auslastung: Vollzeit" adalah data, bukan judul bagian.

    Regresi dari data nyata: kolom kunci-nilai pada iklan berbahasa Jerman
    terbaca sebagai subjudul dan memecah paragraf di tengah.
    """
    teks = (
        "Role Description\n"
        "Fur unser Projekt suchen wir folgenden Spezialisten.\n"
        "Auslastung: Vollzeit\n"
        "Ortlichkeit: remote\n"
        "Qualifications\n"
        "Erfahrung von mindestens 2 Jahren."
    )
    blok = description_blocks(teks)

    judul = [b["title"] for b in blok if b["title"]]
    assert "Auslastung: Vollzeit" not in judul
    assert "Ortlichkeit: remote" not in judul


def test_bullet_markers_become_list_items() -> None:
    """Butir berpenanda menjadi ``butir``, bukan paragraf panjang."""
    teks = (
        "Requirements\n"
        "- Minimal 3 tahun pengalaman\n"
        "- Menguasai Python\n"
        "- Bersedia remote"
    )
    blok = description_blocks(teks)

    assert blok[0]["title"] == "Requirements"
    assert blok[0]["butir"] == [
        "Minimal 3 tahun pengalaman",
        "Menguasai Python",
        "Bersedia remote",
    ]


def test_flat_text_without_newlines_is_split_on_known_headings() -> None:
    """Data lama yang kehilangan semua baris tetap terpecah pada subjudul.

    Kalibrr sebelum perbaikan adapter menyimpan deskripsi tanpa satu pun
    newline. Tanpa pemecahan ini seluruh lowongan tampil sebagai satu
    paragraf raksasa.
    """
    teks = (
        "About Astro ASTRO is Indonesia's quick commerce company. "
        "About this Position We're looking for a Product Designer. "
        "Responsibilities Own the end-to-end design process."
    )
    blok = description_blocks(teks)

    judul = [b["title"] for b in blok if b["title"]]
    assert "About this Position" in judul
    assert "Responsibilities" in judul


def test_empty_description() -> None:
    """Tanpa deskripsi, kembalian kosong — template menampilkan pesan sendiri."""
    assert description_blocks(None) == []
    assert description_blocks("") == []
    assert description_blocks("   ") == []


def test_plain_paragraph_stays_one_block() -> None:
    """Teks biasa tanpa subjudul tidak dipecah menjadi beberapa bagian."""
    blok = description_blocks("Kami mencari iOS Developer yang berpengalaman.")

    assert len(blok) == 1
    assert blok[0]["title"] is None
    assert blok[0]["butir"] == []
    assert "iOS Developer" in blok[0]["text"]
