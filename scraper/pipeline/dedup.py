"""Deduplikasi lintas sumber (PRD-03).

Menghasilkan ``dedup_hash`` dari judul, perusahaan, dan lokasi yang sudah
dinormalkan, serta menandai lowongan yang sama dari sumber berbeda.

Kenapa SHA-256, bukan ``hash()`` bawaan Python: ``hash()`` untuk string
diacak per proses sejak Python 3.3 (PYTHONHASHSEED). Hash yang berubah setiap
proses akan membuat seluruh baris terlihat baru pada setiap eksekusi — tepat
masalah yang ingin dicegah R-03-12.

Yang TIDAK dilakukan di sini: menggabungkan entitas perusahaan secara agresif.
"PT Sinar Mitra" dan "Sinar Mitra Finance" adalah dua entitas berbeda sampai
ada bukti sebaliknya (§9 PRD).
"""

from __future__ import annotations

import hashlib

from core import text as core_text

# Dipakai sebagai pemisah antar-field agar "AB" + "C" tidak sama dengan "A" + "BC".
SEPARATOR = "\x1f"


def _norm(value: str | None) -> str:
    return core_text.normalize_text(value)


def compute_hash(job: dict) -> str:
    """Hash stabil untuk mendeteksi duplikat lintas sumber (R-03-08).

    Bahan: ``title|company_name|location`` yang sudah dinormalkan. Field lain
    sengaja tidak dipakai: gaji dan deskripsi sering berbeda antar platform
    untuk lowongan yang sama, sementara judul, perusahaan, dan lokasi biasanya
    sama.
    """
    if not isinstance(job, dict):
        raise TypeError(f"compute_hash() menerima dict, bukan {type(job)!r}")

    bahan = SEPARATOR.join((
        _norm(job.get("title")),
        _norm(job.get("company_name")),
        _norm(job.get("location")),
    ))
    return hashlib.sha256(bahan.encode("utf-8")).hexdigest()


def is_duplicate(job: dict, lain: dict) -> bool:
    """True bila dua lowongan dianggap sama.

    Sengaja **tidak** menyaring per sumber. Remotive terbukti memuat lowongan
    kembar dari satu sumber: dua ID berbeda dengan judul dan perusahaan
    identik ("Content Reviewer - United States" 2091166 dan 2091177). Menyaring
    per sumber akan meloloskan duplikat semacam itu.
    """
    if job.get("source_url") and job.get("source_url") == lain.get("source_url"):
        return False  # baris yang sama, bukan duplikat
    return compute_hash(job) == compute_hash(lain)


def group_by_hash(jobs: list[dict]) -> dict[str, list[dict]]:
    """Kelompokkan lowongan menurut ``dedup_hash``.

    Dipakai PRD-04/PRD-05 untuk menyembunyikan duplikat dari tampilan tanpa
    menghapus barisnya (R-03-10).
    """
    hasil: dict[str, list[dict]] = {}
    for job in jobs or []:
        hasil.setdefault(compute_hash(job), []).append(job)
    return hasil
