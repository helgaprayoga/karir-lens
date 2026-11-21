"""Adapter Remotive (PRD-02).

**Kenapa bukan API.** ``https://remotive.com/robots.txt`` memuat
``Disallow: /api/*``. Endpoint JSON resmi Remotive karena itu **tidak boleh**
dipakai bot ini. Jalur yang diizinkan adalah halaman HTML ``/remote-jobs`` dan
halaman detailnya.

**Kenapa DOM, bukan JSON-LD.** Halaman daftar memang menanam ``ItemList``
schema.org, tetapi isinya hanya judul dan URL — tanpa perusahaan, tipe kerja,
gaji, atau lokasi. Kartu HTML-nya justru memuat semuanya:

    <li data-joburl="...">
      <span class="remotive-bold">Judul</span> • <span>TELUS DIGITAL</span>
      <div class="tw-text-sm">Writing part-time $14/hour USA</div>

Jadi template ini membaca DOM, bukan JSON-LD. Satu-satunya JSON-LD yang dipakai
adalah ``JobPosting`` di halaman detail, untuk deskripsi.

**Skill.** Tidak tersedia sebagai field. Diturunkan dari deskripsi pada PRD-03;
perhatikan bahwa deskripsi memuat bagian promosi "NOT YOUR TECH STACK?" yang
harus dipangkas lebih dahulu — lihat ``core/skills.trim_sections``.
"""

from __future__ import annotations

import json
import re

from .base import BaseAdapter, RawJob

WHITESPACE_RE = re.compile(r"\s+")
LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)
# Slug lowongan berakhir dengan nomor id: "senior-data-engineer-2091137".
ID_AKHIR_RE = re.compile(r"-(\d+)$")

# `employmentType` schema.org -> himpunan baku. JSON-LD memakai FULL_TIME.
EMPLOYMENT_MAP = {
    "full_time": "full-time", "full-time": "full-time", "full time": "full-time",
    "part_time": "part-time", "part-time": "part-time", "part time": "part-time",
    "contractor": "contract", "contract": "contract",
    "intern": "internship", "internship": "internship",
    "temporary": "contract", "other": None,
}
# Tautan filter tipe kerja pada kartu: /remote-jobs/et-part-time
EMPLOYMENT_PREFIX = "/remote-jobs/et-"
# Level karier: /remote-jobs/cl-senior — bukan employment type, tapi berguna.
LEVEL_PREFIX = "/remote-jobs/cl-"


def _clean(text) -> str | None:
    if not isinstance(text, str):
        return None
    rapi = WHITESPACE_RE.sub(" ", text).strip()
    return rapi or None


def _url_absolut(href: str | None) -> str | None:
    href = _clean(href)
    if not href:
        return None
    if href.startswith("http"):
        return href
    return "https://remotive.com" + (href if href.startswith("/") else "/" + href)


def parse_salary(teks: str | None) -> tuple[float | None, float | None, str | None, str | None]:
    """Urai teks gaji Remotive: "$170k - $200k", "$14/hour", "$3.5k–$5k/month".

    Notasi ``k`` berarti ribuan. Mata uang dari simbol ($ = USD). Periode dari
    kata setelah garis miring; tanpa periode, gaji Remotive dianggap per tahun
    (kebiasaan platformnya), tetapi itu TIDAK ditebak di sini — dikembalikan
    ``None`` dan dibiarkan PRD-03 yang memutuskan.
    """
    teks = _clean(teks)
    if not teks:
        return None, None, None, None

    simbol = teks.lstrip()[:1]
    mata_uang = {"$": "USD", "€": "EUR", "£": "GBP"}.get(simbol)

    angka = re.findall(r"(\d+(?:[.,]\d+)?)\s*([kK])?", teks)
    nilai: list[float] = []
    for mentah, ribu in angka:
        try:
            n = float(mentah.replace(",", "."))
        except ValueError:
            continue
        if ribu:
            n *= 1000
        nilai.append(n)

    periode = None
    rendah = teks.lower()
    for kata, satuan in (("hour", "hour"), ("month", "month"), ("year", "year"), ("day", "day")):
        if f"/{kata}" in rendah or f"per {kata}" in rendah:
            periode = satuan
            break

    if not nilai:
        return None, None, mata_uang, periode
    if len(nilai) >= 2:
        return nilai[0], nilai[1], mata_uang, periode
    if "/hour" in rendah or "per hour" in rendah:
        return nilai[0], None, mata_uang, periode
    return nilai[0], None, mata_uang, periode


def parse_card(li, source: str = "remotive") -> RawJob | None:
    """Urai satu ``<li data-joburl>`` dari halaman daftar."""
    url = _url_absolut(li.get("data-joburl"))
    if not url:
        return None

    judul_el = li.select_one(".job-tile-title span.remotive-bold")
    judul = _clean(judul_el.get_text(" ", strip=True) if judul_el else None)
    if not judul:
        return None

    # Perusahaan: span kedua setelah pemisah "•". Di layar kecil ada salinan
    # kedua tanpa kelas md:tw-block, jadi ambil yang pertama saja.
    perusahaan = None
    spans = li.select(".job-tile-title span.remotive-bold")
    for s in spans[1:]:
        teks = _clean(s.get_text(" ", strip=True))
        if teks and teks != "•":
            perusahaan = teks
            break

    # Baris meta: tipe kerja, level, gaji, lokasi — semuanya tautan/div.
    tipe = None
    for a in li.select("a[href*='/remote-jobs/et-']"):
        slug = (_clean(a.get("href")) or "").split(EMPLOYMENT_PREFIX, 1)[-1]
        tipe = EMPLOYMENT_MAP.get(slug.lower().replace("-", "_")) or EMPLOYMENT_MAP.get(slug.lower())
        if tipe:
            break

    gaji_teks = None
    for s in li.select("span.tag-small, div.tag-small"):
        teks = _clean(s.get_text(" ", strip=True))
        if teks and (teks.startswith("$") or teks.startswith("€") or teks.startswith("£")):
            gaji_teks = teks
            break
    smin, smax, mata_uang, periode = parse_salary(gaji_teks)

    lokasi = []
    for d in li.select("div.tag-small"):
        teks = _clean(d.get_text(" ", strip=True))
        if teks and not teks.startswith(("$", "€", "£")) and len(teks) <= 40:
            lokasi.append(teks)

    cocok = ID_AKHIR_RE.search(url)

    return RawJob(
        title=judul,
        source_url=url,
        company_name=perusahaan,
        location=", ".join(lokasi) if lokasi else None,
        employment_type=tipe,
        description=None,
        skills=[],
        salary_min=smin,
        salary_max=smax,
        salary_currency=mata_uang,
        salary_period=periode,
        source_job_id=cocok.group(1) if cocok else None,
        posted_at=None,
        source=source,
    )


def parse_listing(html: str) -> list[dict]:
    """Urai HTML halaman daftar menjadi list objek mentah.

    Mengembalikan dict ringkas berisi ``html`` kartu agar ``parse_card`` dapat
    bekerja tanpa perlu BeautifulSoup di dua tempat.
    """
    if not html:
        return []
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    hasil = []
    dilihat: set[str] = set()
    for li in soup.select("li[data-joburl]"):
        url = _url_absolut(li.get("data-joburl"))
        if not url or url in dilihat:
            continue
        dilihat.add(url)
        hasil.append({"url": url, "node": li})
    return hasil


def parse_detail(html: str) -> dict | None:
    """Ambil ``JobPosting`` JSON-LD dari halaman detail."""
    if not html:
        return None
    for blok in LD_JSON_RE.findall(html):
        try:
            data = json.loads(blok)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return data
    return None


def _teks(html_mentah: str | None) -> str | None:
    """Buang tag dan entitas; rapikan baris kosong berlebih.

    Deskripsi JSON-LD Remotive berupa HTML penuh (``<p>``, ``<ul>``, ``&amp;``).
    Tanpa dibersihkan, kolom ``jobs.description`` berisi markup — bertentangan
    dengan R-03-05 dan akan tampil sebagai tag di antarmuka.
    """
    if not isinstance(html_mentah, str) or not html_mentah.strip():
        return None

    import html as html_module

    teks = re.sub(r"(?i)<br\s*/?>", "\n", html_mentah)
    teks = re.sub(r"(?i)</(p|li|h[1-6]|div)>", "\n", teks)
    teks = re.sub(r"<[^>]+>", " ", teks)
    teks = html_module.unescape(teks)
    baris = [" ".join(b.split()) for b in teks.splitlines()]
    hasil = "\n".join(b for b in baris if b)
    return hasil or None


class RemotiveAdapter(BaseAdapter):
    """Adapter Remotive berbasis HTML (API dilarang robots.txt)."""

    name = "remotive"
    base_url = "https://remotive.com"
    listing_path = "/remote-jobs"
    # Halaman daftar Remotive tidak memakai nomor halaman pada URL yang
    # diizinkan; satu permintaan sudah memuat puluhan lowongan teratas.
    page_param = None

    def fetch(self, page: int = 1) -> list[dict]:
        if page > 1:
            return []
        return parse_listing(self.http.get(self.listing_url(1)))

    def parse(self, item: dict) -> RawJob | None:
        node = item.get("node")
        if node is None:
            return None
        return parse_card(node, source=self.name)

    def detail_url(self, job: RawJob) -> str | None:
        """Halaman detail sudah menjadi ``source_url``; jangan diambil dua kali."""
        return job.source_url if job.source_url else None

    def parse_detail(self, job: RawJob, html: str) -> RawJob:
        """Lengkapi deskripsi dan lokasi dari ``JobPosting`` halaman detail."""
        posting = parse_detail(html)
        if not posting:
            return job

        deskripsi = _teks(posting.get("description"))
        if deskripsi:
            job.description = deskripsi

        tipe = _clean(posting.get("employmentType"))
        if tipe and not job.employment_type:
            job.employment_type = EMPLOYMENT_MAP.get(tipe.lower().replace("-", "_"))

        negeri = []
        for negara in posting.get("applicantLocationRequirements") or []:
            nama = _clean(negara.get("name")) if isinstance(negara, dict) else None
            if nama:
                negeri.append(nama)
        if negeri and not job.location:
            job.location = ", ".join(negeri)

        waktu = _clean(posting.get("datePosted"))
        if waktu and not job.posted_at:
            job.posted_at = waktu
        return job
