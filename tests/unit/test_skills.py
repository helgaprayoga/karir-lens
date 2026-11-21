"""Test kamus skill dan pencocokan berbasis aturan (PRD-03 R-03-06, PRD-07 R-07-04).

Semua test memakai berkas dan teks nyata — tidak ada jaringan, tidak ada AI
(R-03-14). Fixture HTML berasal dari halaman yang benar-benar diambil, bukan
dikarang.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core import skills

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scraper"


# --- Kamus ---------------------------------------------------------------

def test_dictionary_has_skills() -> None:
    """Kamus terisi dan setiap alias menunjuk skill yang dikenal."""
    data = skills.load_dictionary()
    baku = data["skills"]

    assert len(baku) >= 100, "kamus terlalu kecil untuk berguna"
    assert len(set(baku)) == len(baku), "ada skill duplikat"

    for alias, target in (data["aliases"] or {}).items():
        assert isinstance(target, str), f"alias {alias!r} tidak menunjuk string"
        assert target in set(baku), f"alias {alias!r} -> {target!r} tidak terdaftar"


def test_aliases_point_to_canonical() -> None:
    """Istilah yang umum ditulis berbeda dipetakan ke bentuk baku."""
    peta = skills._aliases()

    assert peta["nodejs"] == "node.js"
    assert peta["reactjs"] == "react"
    assert peta["golang"] == "go"
    assert peta["postgres"] == "postgresql"
    assert peta["k8s"] == "kubernetes"


# --- Pencocokan ----------------------------------------------------------

def test_match_skills_basic() -> None:
    """Skill teknis yang jelas disebut dikenali."""
    assert skills.match_skills("Kuasai Python dan SQL") == ["python", "sql"]
    assert skills.match_skills("Django and Flask") == ["django", "flask"]


def test_match_skills_word_boundary() -> None:
    """Batas kata mencegah kecocokan palsu di dalam kata lain.

    ``go`` harus tidak cocok di dalam "Golang" (itu alias terpisah) maupun
    "Django"; ``c`` dibuang karena terlalu mudah cocok.
    """
    assert "go" not in skills.match_skills("Django")
    assert skills.match_skills("Django") == ["django"]
    assert "c" not in skills.match_skills("React and Vue")


def test_match_skills_longest_wins() -> None:
    """Entri terpanjang menang; satu frasa tidak menghasilkan dua skill.

    Tanpa aturan ini, "React Native" menghasilkan ``react`` + ``react native``,
    dan "Node.js" menghasilkan ``node.js`` + ``js``.
    """
    assert skills.match_skills("React Native") == ["react native"]
    assert skills.match_skills("Node.js") == ["node.js"]


def test_match_skills_no_false_positive() -> None:
    """Teks tanpa skill teknis tidak menghasilkan apa pun."""
    assert skills.match_skills("Good communication skills") == []
    assert skills.match_skills("Tidak butuh skill apa pun") == []
    assert skills.match_skills(None, "", None) == []


def test_match_skills_multiple_texts() -> None:
    """Semua argumen dicari sekaligus, tanpa duplikat."""
    hasil = skills.match_skills("Butuh Python", "Juga SQL dan Python lagi")

    assert hasil == ["python", "sql"]


# --- Pemangkasan bagian promosi -----------------------------------------

def test_trim_sections_removes_promo_list() -> None:
    """Bagian promosi/kategori di bawah deskripsi tidak dihitung sebagai skill.

    Deskripsi Remotive memuat "NOT YOUR TECH STACK?" berisi daftar kategori
    platform. Tanpa dipangkas, satu lowongan menghasilkan 26 skill padahal
    hanya 5 yang benar (diukur pada fixture asli).
    """
    teks = (
        "Kami butuh React dan Python. "
        "NOT YOUR TECH STACK? Kami juga menempatkan Golang, Java, Ruby, PHP."
    )

    penuh = skills.match_skills(teks)
    dipangkas = skills.match_skills(skills.trim_sections(teks))

    assert dipangkas == ["python", "react"]
    assert "go" not in dipangkas and "java" not in dipangkas


def test_preprocess_strips_html_and_entities() -> None:
    """HTML dibuang dan entitas di-decode."""
    assert skills.preprocess("<p>Kuasai <b>Python</b> &amp; SQL</p>") == "Kuasai Python & SQL"


# --- Skill deklaratif dari platform --------------------------------------

def test_normalize_skills_keeps_declared_soft_skills() -> None:
    """Skill deklaratif dipertahankan, termasuk soft skill di luar kamus.

    Dealls menyatakan skill seperti "Leadership" dan "Public Speaking". Itu
    pernyataan sumber, bukan tebakan kamus kita, jadi tidak boleh dibuang.
    """
    hasil = skills.normalize_skills([
        {"name": "Public Speaking"},
        {"name": "Leadership"},
        {"name": "Quality Control (QC)"},
    ])

    assert hasil == ["leadership", "public speaking", "quality control (qc)"]


def test_normalize_skills_maps_aliases() -> None:
    """Alias dipetakan ke bentuk baku dan duplikat dibuang."""
    hasil = skills.normalize_skills(["NodeJS", "node.js", "React", "ReactJS"])

    assert hasil == ["node.js", "react"]


def test_normalize_skills_drops_empty() -> None:
    """Nama kosong atau terlalu pendek dibuang."""
    assert skills.normalize_skills(["", " ", "a", None, {"name": ""}]) == []


# --- Ambiguitas ----------------------------------------------------------

def test_ambiguous_abbreviations() -> None:
    """Singkatan yang bisa berarti beberapa hal ditandai ambigu."""
    assert skills.is_ambiguous("RPC")
    assert skills.is_ambiguous("REST")
    assert skills.is_ambiguous("QC")


def test_unambiguous_known_skills() -> None:
    """Skill nyata tidak ambigu, termasuk singkatan yang jelas di iklan kerja."""
    for nama in ("python", "kubernetes", "sql", "api", "postgresql"):
        assert not skills.is_ambiguous(nama), f"{nama} seharusnya tidak ambigu"


def test_unknown_non_abbreviation_not_ambiguous() -> None:
    """Istilah panjang yang tidak dikenal bukan singkatan, jadi tidak ambigu."""
    assert not skills.is_ambiguous("COBOL")
    assert not skills.is_ambiguous("Fortran")


# --- Pencocokan pada HTML asli -------------------------------------------

def test_match_real_kalibrr_text() -> None:
    """Teks Kalibrr asli menghasilkan skill yang benar.

    Kalibrr tidak punya field skill, jadi skill diturunkan dari kualifikasi.
    Berkas ini diambil langsung dari halaman lowongan.
    """
    html = (FIXTURES / "kalibrr_detail.html").read_text(encoding="utf-8")
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    job = json.loads(m.group(1))["props"]["pageProps"]["job"]

    hasil = skills.match_skills(job.get("qualifications"), job.get("description"))

    assert set(hasil) >= {"python", "sql"}, f"skill tidak terbaca: {hasil}"
    # Teksnya menyebut Golang, C++, C, Python.
    assert "go" in hasil or "golang" in hasil


def test_match_real_remotive_text() -> None:
    """Teks Remotive asli menghasilkan skill yang benar setelah dipangkas.

    Tanpa pemangkasan bagian "NOT YOUR TECH STACK?", hasilnya 26 skill palsu.
    """
    html = (FIXTURES / "remotive_detail.html").read_text(encoding="utf-8")
    blok = re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    posting = next(json.loads(b) for b in blok if json.loads(b).get("@type") == "JobPosting")

    hasil = skills.match_skills(posting.get("title"), posting.get("description"))

    assert "react" in hasil, "judul menyebut React"
    assert len(hasil) <= 8, f"terlalu banyak skill ({len(hasil)}), pangkas gagal: {hasil}"
