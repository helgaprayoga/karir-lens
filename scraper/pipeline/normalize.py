"""Normalisasi field lowongan (PRD-03).

Memakai ``core/text.py`` dan ``core/skills.py`` agar aturan yang sama berlaku
untuk skill lowongan dan skill CV (R-07-04).

Fungsi di sini **murni** (R-03-01): tidak menyentuh database, jaringan, jam
sistem, atau AI (R-03-14). Semua dapat diuji tanpa fixture eksternal.

Aturan diturunkan dari data nyata di database, bukan dikarang. Lihat §4.1 PRD
dan contoh di docstring masing-masing fungsi.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core import text as core_text
from core.skills import normalize_skills

# Panjang maksimum deskripsi (R-03-05). Dealls memuat 7.220 karakter pada
# lowongan terpanjangnya, jadi batas ini tidak memotong data yang wajar.
MAX_DESCRIPTION = 20_000

# Himpunan baku tipe kerja (R-03-04). `unknown` dipakai bila tidak jelas, bukan
# `None`, agar tampilan dapat membedakan "tidak disebutkan" dari "belum dicoba".
EMPLOYMENT_TYPES = frozenset({
    "full-time", "part-time", "contract", "internship", "freelance", "unknown",
})

# Varian penulisan yang benar-benar muncul di ketiga sumber.
EMPLOYMENT_ALIASES = {
    "full time": "full-time", "full-time": "full-time", "fulltime": "full-time",
    "penuh waktu": "full-time", "permanent": "full-time",
    "part time": "part-time", "part-time": "part-time", "parttime": "part-time",
    "paruh waktu": "part-time",
    "contract": "contract", "kontrak": "contract", "contractor": "contract",
    "temporary": "contract", "fixed term": "contract",
    "internship": "internship", "intern": "internship", "magang": "internship",
    "freelance": "freelance", "lepas": "freelance", "freelancer": "freelance",
    "other": "unknown", "": "unknown",
}

# Himpunan periode gaji (R-03-07).
SALARY_PERIODS = frozenset({"month", "year", "hour", "day", "project"})

# Mata uang yang dikenali. Yang tidak ada di sini dibiarkan apa adanya bila
# berbentuk tiga huruf besar, dan dikosongkan bila tidak.
KNOWN_CURRENCIES = frozenset({
    "IDR", "USD", "EUR", "GBP", "SGD", "MYR", "AUD", "JPY", "INR", "PHP", "THB",
})


def _none_if_empty(value: str | None) -> str | None:
    """String kosong menjadi ``None``, bukan ``""`` (R-03-11)."""
    teks = (value or "").strip()
    return teks or None


def normalize_employment_type(value: str | None) -> str:
    """Petakan varian tipe kerja ke himpunan baku (R-03-04).

    Nilai tak dikenal menjadi ``unknown``. Data nyata memuat ``full-time`` 36,
    ``contract`` 9, ``part-time`` 2, ``freelance`` 1, ``internship`` 1 — semuanya
    sudah baku karena adapter memetakannya lebih dulu; fungsi ini menjaga bila
    sumber mengirim varian baru.
    """
    if not value:
        return "unknown"
    kunci = core_text.collapse(str(value)).lower().replace("_", " ").replace("-", " ")
    kunci = core_text.collapse(kunci)
    # `full time` dan `full-time` sama-sama sampai di sini sebagai `full time`.
    peta = {k.replace("-", " "): v for k, v in EMPLOYMENT_ALIASES.items()}
    return peta.get(kunci, "unknown")


def normalize_salary(
    salary_min, salary_max, salary_currency=None, salary_period=None
) -> dict:
    """Normalisasi gaji (R-03-07).

    - Nilai negatif atau nol dibuang: ``0`` bukan gaji, ia ketiadaan data.
    - ``min > max`` ditukar, bukan dibuang: kemungkinan besar urutannya
      tertukar di sumber, dan datanya tetap berguna.
    - Gaji parsial disimpan apa adanya; sisi yang kosong tetap ``None``.
    - Mata uang hanya dipertahankan bila tiga huruf; periode hanya bila dikenal.
    """
    def _angka(nilai) -> float | None:
        if nilai in (None, ""):
            return None
        try:
            n = float(nilai)
        except (TypeError, ValueError):
            return None
        return n if n > 0 else None

    minimum, maksimum = _angka(salary_min), _angka(salary_max)
    if minimum is not None and maksimum is not None and minimum > maksimum:
        minimum, maksimum = maksimum, minimum

    mata_uang = core_text.collapse(str(salary_currency or "")).upper() or None
    if mata_uang and (len(mata_uang) != 3 or not mata_uang.isalpha()):
        mata_uang = None

    periode = core_text.collapse(str(salary_period or "")).lower() or None
    if periode and periode not in SALARY_PERIODS:
        periode = None

    return {
        "salary_min": minimum,
        "salary_max": maksimum,
        "salary_currency": mata_uang,
        "salary_period": periode,
    }


def normalize_posted_at(value) -> str | None:
    """ISO-8601 UTC, atau ``None`` bila tak terbaca (R-03-07 tabel).

    Menerima string ISO dan ``datetime``. Waktu tanpa zona dianggap UTC, karena
    seluruh sumber menyajikan waktu dalam UTC.
    """
    if value in (None, ""):
        return None
    waktu = value
    if not isinstance(waktu, datetime):
        teks = core_text.collapse(str(value))
        if not teks:
            return None
        try:
            waktu = datetime.fromisoformat(teks.replace("Z", "+00:00"))
        except ValueError:
            return None
    if waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=timezone.utc)
    return waktu.astimezone(timezone.utc).isoformat()


def normalize(raw_job) -> dict:
    """``RawJob`` -> dict siap disimpan dengan format seragam.

    Menerima ``RawJob`` (dataclass) maupun ``dict`` agar dapat dipakai ulang
    oleh PRD-07 yang membaca baris database.
    """
    if hasattr(raw_job, "as_row"):
        data = raw_job.as_row()
    elif isinstance(raw_job, dict):
        data = dict(raw_job)
    else:
        raise TypeError(f"normalize() menerima RawJob atau dict, bukan {type(raw_job)!r}")

    judul = core_text.clean_text(data.get("title"))
    perusahaan = core_text.clean_text(data.get("company_name"))
    deskripsi = core_text.clean_multiline(data.get("description"), MAX_DESCRIPTION)
    lokasi = core_text.clean_text(data.get("location"))

    return {
        "title": judul,
        "company_name": _none_if_empty(perusahaan),
        "company_slug": core_text.slugify(perusahaan) or None,
        "location": _none_if_empty(lokasi),
        "employment_type": normalize_employment_type(data.get("employment_type")),
        "description": _none_if_empty(deskripsi),
        "skills": normalize_skills(data.get("skills") or []),
        **normalize_salary(
            data.get("salary_min"),
            data.get("salary_max"),
            data.get("salary_currency"),
            data.get("salary_period"),
        ),
        "source_url": core_text.collapse(data.get("source_url")),
        "source_job_id": _none_if_empty(data.get("source_job_id")),
        "posted_at": normalize_posted_at(data.get("posted_at")),
        "source_id": data.get("source_id"),
    }
