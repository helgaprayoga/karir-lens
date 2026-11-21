"""Adapter Dealls (PRD-02).

Dealls memakai Next.js: halaman daftar berisi HTML kartu, sedangkan data detail
tersedia sebagai payload JSON di dalam ``__NEXT_DATA__``. Parser di sini murni —
hanya menerima dict/HTML, tidak menyentuh jaringan — sehingga dapat diuji
dengan fixture.

Pola diadaptasi dari ``parse_card``/``parse_listing`` pada
``Praktik Scripting/Pertemuan 9/scraper.py``, dengan penggantian: slug+SQLite
menjadi ``RawJob``+``source_url``, dan klasifikasi baris meta dipertahankan
karena struktur kartu Dealls memang tidak konsisten antar lowongan.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from .base import BaseAdapter, RawJob

WHITESPACE_RE = re.compile(r"\s+")
LOCATION_SEPARATOR = "•"
SALARY_PREFIXES = ("rp", "idr", "negotiable", "gaji")
EXPERIENCE_PREFIX = "pengalaman"
JOB_TYPE_LABELS = {
    "full time", "part time", "kontrak", "magang", "paruh waktu", "penuh waktu",
    "lepas", "freelance", "internship", "contract",
}
# Pemetaan ke nilai enum yang dipakai skema dan tampilan.
EMPLOYMENT_MAP = {
    "full time": "full-time",
    "penuh waktu": "full-time",
    "part time": "part-time",
    "paruh waktu": "part-time",
    "kontrak": "contract",
    "contract": "contract",
    "magang": "internship",
    "internship": "internship",
    "lepas": "freelance",
    "freelance": "freelance",
}
PERIOD_MAP = {"bulan": "month", "tahun": "year", "hari": "day", "jam": "hour"}


def _clean(text) -> str | None:
    """Rapikan spasi; kembalikan None untuk teks kosong (R-02-02)."""
    if not isinstance(text, str):
        return None
    rapi = WHITESPACE_RE.sub(" ", text).strip()
    return rapi or None


def _teks(html_mentah: str | None) -> str | None:
    """Buang tag dan entitas, pertahankan baris per butir sebagai newline."""
    if not isinstance(html_mentah, str) or not html_mentah.strip():
        return None

    import html as html_module

    teks = re.sub(r"(?i)</(li|p|h[1-6]|div)>", "\n", html_mentah)
    teks = re.sub(r"<[^>]+>", " ", teks)
    teks = html_module.unescape(teks)
    baris = [" ".join(b.split()) for b in teks.splitlines()]
    hasil = "\n".join(b for b in baris if b)
    return hasil or None


def parse_salary(teks: str | None) -> tuple[float | None, float | None, str | None, str | None]:
    """Urai teks gaji menjadi (min, max, currency, period).

    Lima kondisi ditangani seperti ``SalaryRange`` di tampilan: rentang penuh,
    hanya minimum, hanya maksimum, tidak disebutkan, dan mata uang non-IDR.
    """
    teks = _clean(teks)
    if not teks:
        return None, None, None, None

    rendah = teks.lower()
    # Awalan boleh didahului kata seperti "mulai"/"sampai", jadi yang diperiksa
    # adalah kehadiran penanda mata uang, bukan posisi awalnya.
    if not any(penanda in rendah for penanda in ("rp", "idr")):
        if not any(rendah.startswith(p) for p in ("negotiable", "gaji")):
            return None, None, None, None

    currency = "IDR" if ("rp" in rendah or "idr" in rendah) else None
    angka = re.findall(r"[\d][\d.,]*", teks)
    nilai = []
    for bagian in angka:
        bersih = bagian.rstrip(".,").replace(".", "").replace(",", "")
        if bersih.isdigit():
            nilai.append(float(bersih))

    period = None
    for kata, nilai_period in PERIOD_MAP.items():
        if kata in rendah:
            period = nilai_period
            break

    if len(nilai) >= 2:
        return nilai[0], nilai[1], currency, period
    if len(nilai) == 1:
        # "Mulai Rp X" vs "Sampai Rp X" — kata penentu menentukan sisi mana.
        if "mulai" in rendah or "minimal" in rendah:
            return nilai[0], None, currency, period
        if "sampai" in rendah or "maksimal" in rendah or "upto" in rendah:
            return None, nilai[0], currency, period
        return nilai[0], None, currency, period
    return None, None, currency, period


def parse_card(card: dict, source: str = "dealls") -> RawJob | None:
    """Urai satu kartu hasil ``fetch``. ``None`` bila bukan lowongan."""
    href = _clean(card.get("href"))
    judul = _clean(card.get("title"))
    if not href or not judul:
        return None

    source_url = href if href.startswith("http") else urljoin("https://dealls.com", href)

    lokasi = None
    tipe = None
    gaji_teks = None
    meta = [_clean(b) for b in (card.get("meta") or [])]
    meta = [b for b in meta if b]

    for i, teks in enumerate(meta):
        rendah = teks.lower()
        # "Penuh waktu" / "Kontrak" / "Magang"
        if tipe is None and rendah in JOB_TYPE_LABELS:
            tipe = EMPLOYMENT_MAP.get(rendah)
        # "Rp 9.000.000 – 14.000.000"; "Tidak Ditampilkan" berarti kosong.
        elif gaji_teks is None and any(rendah.startswith(p) for p in SALARY_PREFIXES):
            gaji_teks = teks

    # Kota: Dealls menggabungkannya dengan mode kerja menjadi satu baris,
    # "On-site • Bogor". Kota adalah bagian setelah pemisah; mode kerja tidak
    # disimpan karena skema `jobs` tidak punya kolomnya.
    if lokasi is None:
        for teks in meta:
            if LOCATION_SEPARATOR in teks:
                kandidat = _clean(teks.split(LOCATION_SEPARATOR, 1)[1])
                if kandidat:
                    lokasi = kandidat
                    break

    smin, smax, mata_uang, periode = parse_salary(gaji_teks)

    return RawJob(
        title=judul,
        source_url=source_url,
        company_name=_clean(card.get("company")),
        location=lokasi,
        employment_type=tipe,
        description=_clean(card.get("description")),
        skills=[s for s in (_clean(x) for x in card.get("skills") or []) if s],
        salary_min=smin,
        salary_max=smax,
        salary_currency=mata_uang,
        salary_period=periode,
        source_job_id=_clean(card.get("slug")),
        posted_at=_clean(card.get("posted_at")),
        source=source,
    )


def parse_listing(html: str, source: str = "dealls") -> list[dict]:
    """Urai HTML halaman daftar menjadi list dict mentah.

    Selector di sini diturunkan dari HTML Dealls yang **sebenarnya**, bukan
    ditebak. Dealls memakai kelas Tailwind sehingga tidak ada kelas semantik
    seperti ``.company``; yang dipakai adalah struktur: judul ada di ``<h2>``
    dalam kartu, perusahaan pada ``div`` pertama setelah judul, dan sisanya
    adalah deretan ``span`` berisi tipe kerja, mode, kota, pengalaman, dan gaji.

    Hasil terdeduplikasi berdasarkan href, urutan kemunculan pertama
    dipertahankan. Murni — tidak menyentuh jaringan.
    """
    if not html:
        return []

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    hasil: list[dict] = []
    dilihat: set[str] = set()

    for kartu in soup.select("a[href*='/loker/']"):
        href = kartu.get("href") or ""
        # Tautan navigasi tidak memuat pemisah "~" (lowongan~perusahaan).
        if "~" not in href or href in dilihat:
            continue

        judul_el = kartu.select_one("h2")
        if judul_el is None:
            continue
        judul = " ".join(judul_el.get_text(" ", strip=True).split())
        if not judul:
            continue

        # Perusahaan: div pertama setelah h2 yang hanya berisi teks pendek.
        perusahaan = None
        berikut = judul_el.find_next("div")
        if berikut is not None:
            teks = " ".join(berikut.get_text(" ", strip=True).split())
            if teks and len(teks) <= 80 and "lalu" not in teks:
                perusahaan = teks

        # Baris meta diklasifikasikan berdasarkan ISI, bukan urutan, karena
        # jumlah dan urutannya berbeda antar lowongan.
        meta: list[str] = []
        for span in kartu.select("span"):
            teks = " ".join(span.get_text(" ", strip=True).split())
            if teks and teks not in meta:
                meta.append(teks)

        dilihat.add(href)
        hasil.append(
            {
                "href": href,
                "title": judul,
                "company": perusahaan,
                "meta": meta,
                "slug": href.split("/loker/", 1)[-1].strip("/"),
            }
        )

    return hasil


class DeallsAdapter(BaseAdapter):
    """Adapter Dealls berbasis HTML halaman daftar."""

    name = "dealls"
    base_url = "https://dealls.com"
    listing_path = "/loker"
    page_param = "page"

    def fetch(self, page: int = 1) -> list[dict]:
        html = self.http.get(self.listing_url(page))
        return parse_listing(html, source=self.name)

    def parse(self, item: dict) -> RawJob | None:
        return parse_card(item, source=self.name)

    def detail_url(self, job: RawJob) -> str | None:
        """Halaman detail Dealls sudah menjadi ``source_url``."""
        return job.source_url or None

    def parse_detail(self, job: RawJob, html: str) -> RawJob:
        """Lengkapi dari ``__NEXT_DATA__`` halaman detail.

        Kartu daftar hanya memuat tanggal relatif ("1h lalu"), sedangkan
        ``publishedAt`` berisi tanggal absolut. Deskripsi penuh dan daftar
        skill (``candidatePreference.skills``) juga hanya ada di sini — sumber
        yang sama dengan proyek referensi.
        """
        payload = extract_job_payload(html)
        if not payload:
            return job

        # Dealls tidak punya satu field `description`: isi lowongan terbagi
        # menjadi `responsibilities` (tugas) dan `requirements` (syarat),
        # keduanya HTML.
        if not job.description:
            bagian = [_teks(payload.get("responsibilities")),
                      _teks(payload.get("requirements"))]
            gabung = "\n\n".join(b for b in bagian if b)
            job.description = gabung or None

        if not job.posted_at:
            job.posted_at = _clean(
                payload.get("publishedAt") or payload.get("createdAt")
            )

        skill = _skill_dari_payload(payload)
        if skill:
            job.skills = skill

        # Gaji dari data mentah lebih andal daripada teks "Tidak Ditampilkan".
        if job.salary_min is None and payload.get("salaryMin"):
            job.salary_min = float(payload["salaryMin"])
        if job.salary_max is None and payload.get("salaryMax"):
            job.salary_max = float(payload["salaryMax"])

        return job


def extract_job_payload(html: str) -> dict | None:
    """Ambil objek lowongan dari ``__NEXT_DATA__`` halaman detail.

    Polanya sama dengan proyek referensi: ``props.pageProps.dehydratedState``
    berisi query, dan salah satunya memuat objek dengan kunci ``role``.
    """
    from ..adapters.kalibrr import extract_next_data

    data = extract_next_data(html)
    if not data:
        return None
    try:
        queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError):
        return None

    for query in queries or []:
        try:
            payload = query["state"]["data"]
        except (KeyError, TypeError):
            continue
        if isinstance(payload, dict) and payload.get("role"):
            return payload
    return None


def _skill_dari_payload(payload: dict) -> list[str]:
    """Daftar skill dari ``candidatePreference.skills``."""
    pref = payload.get("candidatePreference") or {}
    hasil: list[str] = []
    for s in pref.get("skills") or []:
        nama = _clean(s.get("name") if isinstance(s, dict) else s)
        if nama:
            hasil.append(nama)
    return hasil
