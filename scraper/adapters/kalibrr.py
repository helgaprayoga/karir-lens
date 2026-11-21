"""Adapter Kalibrr (PRD-02).

Sumber data: **HTML** halaman `/job-board` dan halaman detail lowongan. Setiap
halaman Next.js menanam objek JSON di ``<script id="__NEXT_DATA__">``, dan data
lowongan ada di sana lengkap dengan kualifikasi serta deskripsi — struktur DOM
tidak perlu diparse sama sekali. Pola ini sama dengan ``extract_next_data()``
pada proyek referensi (``Praktik Scripting/Pertemuan 9/scraper.py``).

Kenapa JSON tertanam, bukan DOM: struktur DOM Kalibrr memakai kelas Tailwind dan
berubah kapan saja; data di ``__NEXT_DATA__`` adalah kontrak antara server dan
klien mereka sendiri. Mengambilnya juga menghindari teks terpotong ``…`` yang
hanya ada pada tampilan.

Field skill: **tidak tersedia**. ``jobSdsSkills`` ada di skema tetapi ``null``
pada seluruh lowongan yang diperiksa. Skill diturunkan dari kualifikasi dan
deskripsi pada PRD-03 lewat ``core/skills.py`` — bukan di adapter ini.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape

from .base import BaseAdapter, RawJob

NEXT_DATA_RE = re.compile(
    r'<script[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)
WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")

# `tenure` Kalibrr berbentuk label bebas; dipetakan ke himpunan baku R-03-04.
EMPLOYMENT_MAP = {
    "full time": "full-time", "full-time": "full-time", "penuh waktu": "full-time",
    "part time": "part-time", "part-time": "part-time", "paruh waktu": "part-time",
    "contract": "contract", "kontrak": "contract", "contractor": "contract",
    "internship": "internship", "magang": "internship",
    "freelance": "freelance", "lepas": "freelance",
}
# `salaryInterval` memakai kode angka pada sebagian respons.
INTERVAL_MAP = {
    "1": "hour", "2": "day", "3": "month", "4": "year",
    "hour": "hour", "hourly": "hour", "per hour": "hour",
    "day": "day", "daily": "day", "per day": "day",
    "month": "month", "monthly": "month", "per month": "month",
    "year": "year", "yearly": "year", "annual": "year", "per year": "year",
}
PER_PAGE = 15


def _clean(text) -> str | None:
    if not isinstance(text, str):
        return None
    rapi = WHITESPACE_RE.sub(" ", text).strip()
    return rapi or None


def _teks(html: str | None) -> str | None:
    """Buang tag dan entitas dari HTML; kembalikan teks atau ``None``."""
    if not isinstance(html, str) or not html.strip():
        return None
    return _clean(unescape(TAG_RE.sub(" ", html)))


def _waktu(nilai) -> str | None:
    if nilai in (None, ""):
        return None
    teks = _clean(str(nilai))
    if not teks:
        return None
    try:
        waktu = datetime.fromisoformat(teks.replace("Z", "+00:00"))
    except ValueError:
        return None
    if waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=timezone.utc)
    return waktu.astimezone(timezone.utc).isoformat()


def extract_next_data(html: str) -> dict | None:
    """Ambil isi ``<script id="__NEXT_DATA__">`` sebagai dict.

    Tag script kini membawa atribut lain (``nonce``), jadi pola mencocokkan
    ``id="__NEXT_DATA__"`` di mana pun di dalam tag — bukan mengharapkannya
    tepat setelah nama tag. Kesalahan itu sempat membuat saya menyimpulkan data
    Dealls "sudah tidak ada".
    """
    if not html:
        return None
    cocok = NEXT_DATA_RE.search(html)
    if not cocok:
        return None
    try:
        return json.loads(cocok.group(1))
    except ValueError:
        return None


def _kota(google_location) -> str | None:
    """Ambil kota dan negara dari ``googleLocation``.

    Data dari ``__NEXT_DATA__`` memakai camelCase (``addressComponents``),
    bukan snake_case seperti respons API mentah.
    """
    if not google_location:
        return None
    data = google_location
    if isinstance(google_location, str):
        try:
            data = json.loads(google_location)
        except ValueError:
            return _clean(google_location)
    if not isinstance(data, dict):
        return None

    komponen = data.get("addressComponents") or data.get("address_components") or {}
    if not isinstance(komponen, dict):
        return None
    kota = _clean(komponen.get("city") or komponen.get("region"))
    negara = _clean(komponen.get("country"))
    if kota and negara:
        return f"{kota}, {negara}"
    return kota or negara


def _skills_tertanam(item: dict) -> list[str]:
    """Skill bila sumber menyatakannya. Kalibrr hampir selalu ``null``."""
    mentah = item.get("jobSdsSkills") or item.get("job_sds_skills")
    if isinstance(mentah, str):
        try:
            mentah = json.loads(mentah)
        except ValueError:
            return []
    hasil: list[str] = []
    for bagian in mentah or []:
        nama = _clean(bagian.get("name") if isinstance(bagian, dict) else bagian)
        if nama:
            hasil.append(nama)
    return hasil


def parse_item(item: dict, source: str = "kalibrr") -> RawJob | None:
    """Urai satu objek lowongan Kalibrr. ``None`` bila wajib kosong."""
    if not isinstance(item, dict):
        return None

    judul = _clean(item.get("name"))
    slug = _clean(item.get("slug"))
    identitas = item.get("id")
    if not judul or (identitas in (None, "") and not slug):
        return None

    # Bentuk URL yang sebenarnya: /id-ID/c/<perusahaan>/jobs/<id>/<slug>.
    # `<perusahaan>` dan `<slug>` berbeda, jadi URL detail hanya dapat disusun
    # dari keduanya bila `companyInfo.code` tersedia. Tanpa itu, pakai bentuk
    # yang selalu benar walau kurang spesifik.
    kode = {}
    info = item.get("companyInfo") or item.get("company") or {}
    if isinstance(info, dict):
        kode = {"code": _clean(info.get("code")), "slug": _clean(info.get("slug"))}

    if identitas not in (None, "") and slug:
        if kode.get("code"):
            source_url = (
                f"https://www.kalibrr.com/id-ID/c/{kode['code']}/jobs/{identitas}/{slug}"
            )
        else:
            source_url = f"https://www.kalibrr.com/id-ID/job/{identitas}/{slug}"
    elif slug:
        source_url = f"https://www.kalibrr.com/c/{slug}"
    else:
        source_url = f"https://www.kalibrr.com/id-ID/job/{identitas}"

    tipe = EMPLOYMENT_MAP.get((_clean(item.get("tenure")) or "").lower())
    interval = _clean(str(item.get("salaryInterval") or item.get("salary_interval") or ""))
    periode = INTERVAL_MAP.get((interval or "").lower())

    gaji_min = item.get("baseSalary") or item.get("base_salary")
    gaji_maks = item.get("maximumSalary") or item.get("maximum_salary")

    perusahaan = item.get("company")
    nama_perusahaan = (
        _clean(perusahaan.get("name")) if isinstance(perusahaan, dict) else None
    )

    return RawJob(
        title=judul,
        source_url=source_url,
        company_name=_clean(item.get("companyName")) or nama_perusahaan,
        location=_kota(item.get("googleLocation") or item.get("google_location")),
        employment_type=tipe,
        # Deskripsi dari daftar biasanya terpotong; halaman detail melengkapinya.
        description=_teks(item.get("description")),
        skills=_skills_tertanam(item),
        salary_min=float(gaji_min) if gaji_min not in (None, "", 0) else None,
        salary_max=float(gaji_maks) if gaji_maks not in (None, "", 0) else None,
        salary_currency=_clean(item.get("salaryCurrency") or item.get("salary_currency")),
        salary_period=periode,
        source_job_id=str(identitas) if identitas not in (None, "") else slug,
        posted_at=_waktu(item.get("createdAt") or item.get("created_at")),
        source=source,
    )


def parse_listing(html: str) -> list[dict]:
    """Urai HTML halaman daftar menjadi list objek lowongan dari ``__NEXT_DATA__``."""
    data = extract_next_data(html)
    if not data:
        return []
    try:
        jobs = data["props"]["pageProps"]["jobs"]
    except (KeyError, TypeError):
        return []
    return jobs if isinstance(jobs, list) else []


def parse_detail(html: str) -> dict | None:
    """Urai HTML halaman detail menjadi objek lowongan.

    Halaman detail menyimpan lowongan di ``pageProps.job``, bukan ``jobs``.
    """
    data = extract_next_data(html)
    if not data:
        return None
    try:
        job = data["props"]["pageProps"]["job"]
    except (KeyError, TypeError):
        return None
    return job if isinstance(job, dict) else None


class KalibrrAdapter(BaseAdapter):
    """Adapter Kalibrr berbasis ``__NEXT_DATA__`` pada HTML."""

    name = "kalibrr"
    base_url = "https://www.kalibrr.com"
    listing_path = "/job-board"
    # Nomor halaman diterjemahkan menjadi offset; lihat `listing_url`.
    page_param = "offset"
    per_page = PER_PAGE

    def listing_url(self, page: int = 1) -> str:
        dasar = self.base_url.rstrip("/") + self.listing_path
        offset = max(0, (page - 1) * self.per_page)
        return f"{dasar}?limit={self.per_page}&offset={offset}"

    def fetch(self, page: int = 1) -> list[dict]:
        return parse_listing(self.http.get(self.listing_url(page)))

    def parse(self, item: dict) -> RawJob | None:
        return parse_item(item, source=self.name)

    def detail_url(self, job: RawJob) -> str | None:
        """Halaman detail lowongan.

        ``source_url`` sudah berupa URL detail bila bentuk lengkapnya tersedia
        (ada kode perusahaan). Bila tidak, adapter ini tidak punya cara
        menyusunnya: slug perusahaan dan slug lowongan tidak dapat ditukar.
        """
        if not job.source_url:
            return None
        if "/jobs/" in job.source_url:
            return job.source_url
        return None

    def parse_detail(self, job: RawJob, html: str) -> RawJob:
        """Lengkapi dari halaman detail: deskripsi penuh dan kualifikasi.

        Kualifikasi digabung ke deskripsi karena skema tidak punya kolomnya
        sendiri, dan di situlah daftar syarat skill berada.
        """
        detail = parse_detail(html)
        if not detail:
            return job

        deskripsi = _teks(detail.get("description"))
        kualifikasi = _teks(detail.get("qualifications"))
        bagian = [b for b in (deskripsi, kualifikasi) if b]
        if bagian:
            job.description = "\n\n".join(bagian)

        skill = _skills_tertanam(detail)
        if skill:
            job.skills = skill
        if job.company_name is None:
            job.company_name = _clean(detail.get("companyName"))
        return job
