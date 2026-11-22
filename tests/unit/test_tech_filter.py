"""Pengujian klasifikasi lowongan IT (pemfokusan produk ke IT).

Semua kasus di sini diambil dari judul yang **benar-benar ada** di database,
bukan dikarang. Klasifikasi murni: tanpa jaringan dan tanpa database.
"""

from __future__ import annotations

import pytest

from core.tech import is_it_job


# --- Positif: lowongan IT nyata ----------------------------------------

@pytest.mark.parametrize(
    "judul",
    [
        "Data Engineer",                                  # Dealls
        "Solutions Architect (AI & Enterprise Solutions)",  # Dealls
        "Sitecore Developer",                             # Kalibrr
        "Backend Software Engineer",                      # Kalibrr
        "Full-Stack Developer",                           # Remotive
        "Senior Back-end Developer",                      # Remotive
        "Senior Data Engineer",                           # Remotive
        "Senior React Full-stack Developer",              # Remotive
        "Tech Lead Full-Stack Rails Engineer",            # Remotive
        "Tier III Service Desk Engineer",                 # Remotive
        "AI Trainer - Video Annotation",                  # Remotive
        # Ditemukan saat mengaudit 144 judul Dealls yang disaring: dua ini
        # terbuang padahal jelas IT.
        "Infrastructure Engineer (L1)",
        "IT Governance, Risk & Compliance Specialist",
        "Quality Assurance (QA) Internship",
    ],
)
def test_real_it_titles_accepted(judul: str) -> None:
    """Judul IT yang ada di database harus diterima."""
    assert is_it_job(title=judul), judul


# --- Negatif: lowongan non-IT nyata ------------------------------------

@pytest.mark.parametrize(
    "judul",
    [
        "Supervisor Outlet",
        "Head Chef",
        "Senior Cook",
        "Medical Representative (Padang)",
        "Community Officer Blora",
        "Admin Finance",
        "Executive Assistant to Director",
        "Student Advisor Cikarang Cifest",
        "Freelance Writer",
        "Content Reviewer - United States",
        "Customer Service Representative",
        "Inside Sales Contractor",
        "OFFLINE ENGLISH TUTOR - CIREBON",
        "Digital Marketing Intern (Social Media Specialist)",
        "[POTENSI PENDAPATAN 30 JUTA++] Personal Trainer - FIT HUB",
    ],
)
def test_real_non_it_titles_rejected(judul: str) -> None:
    """Judul non-IT yang ada di database harus ditolak."""
    assert not is_it_job(title=judul), judul


def test_audit_staff_is_not_it_staff() -> None:
    """``"it staff"`` tidak boleh cocok di dalam **"audit staff"**.

    Tanpa batas kata, "Tax & Audit Staff" lolos sebagai lowongan IT. Kesalahan
    ini nyata: ditemukan saat menguji klasifikasi pada data database.
    """
    assert not is_it_job(title="Tax & Audit Staff")
    assert not is_it_job(title="Audit Staff")
    # Bentuk yang memang menyebut IT tetap diterima.
    assert is_it_job(title="IT Staff")
    assert is_it_job(title="IT Support Officer")


def test_generic_words_alone_are_not_enough() -> None:
    """Kata umum tidak berdiri sendiri sebagai bukti IT.

    "Data Entry" bukan "Data Engineer"; "Product Design Manager" bukan peran
    teknologi walau memuat kata *design*.
    """
    assert not is_it_job(title="Data Entry")
    assert not is_it_job(title="Product Development & Design Manager For TPF Group")
    assert not is_it_job(title="Operational Support (Mandarin Speaker)")


# --- Kategori dari sumber ----------------------------------------------

def test_category_rejects_early() -> None:
    """Kategori non-IT menolak walau judulnya memuat kata teknis.

    Remotive memberi kategori di URL; itu pernyataan platform, lebih kuat
    daripada pembacaan judul.
    """
    assert not is_it_job(title="Engineering Manager", category="writing")
    assert not is_it_job(title="Data Engineer", category="finance")


def test_category_accepts_it_roles() -> None:
    """Kategori IT diterima walau judulnya tidak menyebut teknologi."""
    assert is_it_job(title="Member of Technical Staff", category="software-development")
    assert is_it_job(title="Specialist", category="data")


def test_kalibrr_function_names() -> None:
    """Nama fungsi Kalibrr berbentuk berspasi ("IT and Software")."""
    assert is_it_job(title="Associate", category="IT and Software")
    assert not is_it_job(title="Associate", category="Accounting and Finance")


# --- Skill sebagai bukti terakhir --------------------------------------

def test_technical_skills_can_qualify() -> None:
    """Dua skill teknis cukup bila judulnya tidak menyebut peran IT."""
    assert is_it_job(title="Specialist", skills=["python", "kubernetes"])
    assert is_it_job(title="Associate", skills=["react", "typescript"])


def test_one_technical_skill_is_not_enough() -> None:
    """Satu skill teknis bisa kebetulan; dua baru jadi bukti."""
    assert not is_it_job(title="Marketing Specialist", skills=["sql"])
    assert not is_it_job(title="Sales Associate", skills=["figma"])


def test_no_signal_means_not_it() -> None:
    """Tanpa judul, kategori, maupun skill, jawabannya bukan IT."""
    assert not is_it_job()
    assert not is_it_job(title="", skills=[])
