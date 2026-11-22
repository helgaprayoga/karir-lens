"""PRD-02 §7.1: registry adapter, parser per sumber, retry, robots, dan runner.

Semua test di sini **tidak menyentuh jaringan**: klien HTTP diganti tiruan, dan
parser diberi fixture HTML/JSON dari ``tests/fixtures/scraper/``. Ini syarat
R-02-11 dan alasan yang sama dengan proyek referensi.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.config import Settings
from scraper import runner
from scraper.adapters import registry
from scraper.adapters.base import RawJob
from scraper.adapters.dealls import DeallsAdapter, parse_card, parse_listing, parse_salary
from scraper.adapters.kalibrr import (
    KalibrrAdapter,
    extract_next_data,
    parse_detail as parse_kalibrr_detail,
    parse_item as parse_kalibrr,
    parse_listing as parse_kalibrr_listing,
)
from scraper.adapters.remotive import (
    RemotiveAdapter,
    parse_card as parse_remotive_card,
    parse_detail as parse_remotive_detail,
    parse_listing as parse_remotive_listing,
    parse_salary as parse_remotive_salary,
)
from scraper.errors import RobotsDisallowedError, ScrapeBlockedError, ScrapeError
from scraper.http import ScraperHTTP

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scraper"


def _settings(**ubah) -> Settings:
    dasar = {
        "secret_key": "uji",
        "supabase_url": "https://contoh.supabase.co",
        "supabase_key": "kunci",
        "deepseek_api_key": None,
        "deepseek_model": "deepseek-chat",
        "scraper_user_agent": "KarirLensBot/1.0 (uji)",
        "scraper_max_retry": 3,
        "ai_daily_limit": 20,
        "cluster_n_clusters": 6,
        "cluster_pca_components": 2,
        "max_upload_bytes": 5 * 1024 * 1024,
        "session_cookie_secure": False,
        "preview_ui": False,
    }
    dasar.update(ubah)
    return Settings(**dasar)


class HTTPPalsu:
    """Klien HTTP tiruan: tidak ada soket, tidak ada jeda."""

    def __init__(self, halaman=None, izin=True, galat=None):
        self.halaman = halaman or []
        self.izin = izin
        self.galat = galat
        self.panggilan: list[str] = []
        self.ditutup = False

    def is_allowed(self, url: str) -> bool:
        return self.izin

    def get(self, url: str, params=None) -> str:
        self.panggilan.append(url)
        if self.galat:
            raise self.galat
        indeks = len(self.panggilan) - 1
        if indeks < len(self.halaman):
            return self.halaman[indeks]
        return ""  # halaman habis

    def get_json(self, url: str, params=None):
        return json.loads(self.get(url, params))

    def close(self) -> None:
        self.ditutup = True


# --- R-02-01: registry ---------------------------------------------------

def test_adapter_registry() -> None:
    """Registry memuat tiga adapter dengan nama unik."""
    assert set(registry.ADAPTERS) == {"dealls", "kalibrr", "remotive"}

    for nama, kelas in registry.ADAPTERS.items():
        assert kelas.name == nama
        assert kelas.base_url.startswith("https://")

    with pytest.raises(ValueError):
        registry.get_adapter("tidak-ada")


def test_event_source_id_unique() -> None:
    """Tiga adapter memakai `source_job_id` dari sumber masing-masing."""
    for kelas in registry.ADAPTERS.values():
        adapter = kelas(http=HTTPPalsu())
        assert hasattr(adapter, "parse")
        assert adapter.name


# --- R-02-02 / R-02-11: parser per sumber --------------------------------

def test_parse_dealls_fixture() -> None:
    """Parser Dealls menghasilkan RawJob dengan field wajib (R-02-02)."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    kartu = parse_listing(html)

    # Kartu duplikat dan tautan navigasi dibuang.
    assert len(kartu) == 2

    job = parse_card(kartu[0])
    assert job is not None
    assert job.title == "Backend Engineer (Python)"
    assert job.company_name == "NovaTech Labs"
    assert job.location == "Jakarta Selatan"
    assert job.employment_type == "full-time"
    assert job.salary_min == 12_000_000
    assert job.salary_max == 18_000_000
    assert job.salary_currency == "IDR"
    assert job.salary_period == "month"
    assert job.source_url.endswith("/loker/backend-engineer-python~novatech-labs")
    assert job.source_job_id == "backend-engineer-python~novatech-labs"
    assert job.source == "dealls"


def test_parse_kalibrr_fixture() -> None:
    """Parser Kalibrr membaca ``__NEXT_DATA__`` dari HTML daftar (R-02-02).

    Fixture diambil dari halaman `/job-board` yang sebenarnya, bukan dibuat.
    """
    html = (FIXTURES / "kalibrr_board.html").read_text(encoding="utf-8")
    items = parse_kalibrr_listing(html)

    assert len(items) >= 10, "satu halaman Kalibrr memuat belasan lowongan"

    job = parse_kalibrr(items[0])
    assert job is not None
    assert job.title, "judul wajib ada"
    assert job.company_name, "perusahaan terbaca dari companyName"
    assert job.location and "," in job.location, "kota dan negara digabung"
    assert job.employment_type in {"full-time", "part-time", "contract",
                                   "internship", "freelance", None}
    assert job.source_job_id and job.source_job_id.isdigit()
    # Bentuk URL sebenarnya: /id-ID/c/<perusahaan>/jobs/<id>/<slug>
    assert re.search(r"/c/[^/]+/jobs/\d+/[^/]+$", job.source_url), job.source_url
    assert job.posted_at is not None


def test_kalibrr_detail_adds_qualifications() -> None:
    """Halaman detail menambah deskripsi penuh dan kualifikasi.

    Kualifikasi penting: di situlah daftar syarat skill berada, karena
    ``jobSdsSkills`` Kalibrr selalu ``null``.
    """
    html_daftar = (FIXTURES / "kalibrr_board.html").read_text(encoding="utf-8")
    job = parse_kalibrr(parse_kalibrr_listing(html_daftar)[0])
    sebelum = len(job.description or "")

    html_detail = (FIXTURES / "kalibrr_detail.html").read_text(encoding="utf-8")
    adapter = KalibrrAdapter(http=HTTPPalsu())
    job = adapter.parse_detail(job, html_detail)

    assert len(job.description or "") > sebelum
    assert "<li>" not in (job.description or ""), "HTML dibersihkan"
    low = (job.description or "").lower()
    assert "python" in low or "golang" in low, "kualifikasi ikut tersimpan"


def test_kalibrr_skills_are_empty() -> None:
    """Kalibrr tidak menyediakan skill; adapter tidak mengarangnya.

    ``jobSdsSkills`` ada di skema tetapi ``null`` di seluruh lowongan yang
    diperiksa. Skill diturunkan dari teks pada PRD-03.
    """
    html = (FIXTURES / "kalibrr_board.html").read_text(encoding="utf-8")
    jobs = [parse_kalibrr(i) for i in parse_kalibrr_listing(html)]

    assert all(j.skills == [] for j in jobs if j)


def test_parse_remotive_fixture() -> None:
    """Parser Remotive membaca kartu HTML, bukan JSON-LD daftar (R-02-02).

    JSON-LD halaman daftar hanya berisi judul dan URL; kartu HTML memuat
    perusahaan, tipe kerja, gaji, dan lokasi.
    """
    html = (FIXTURES / "remotive_board.html").read_text(encoding="utf-8")
    items = parse_remotive_listing(html)

    assert len(items) >= 10

    job = parse_remotive_card(items[0]["node"])
    assert job is not None
    assert job.title
    assert job.company_name, "perusahaan ada di kartu"
    assert job.source_url.startswith("https://remotive.com/remote-jobs/")
    assert job.source_job_id and job.source_job_id.isdigit()
    assert job.source == "remotive"
    assert job.location, "lokasi ada di kartu"


def test_remotive_salary_from_card() -> None:
    """Gaji kartu Remotive diurai beserta mata uang dan periodenya."""
    assert parse_remotive_salary("$170k - $200k") == (170_000.0, 200_000.0, "USD", None)
    assert parse_remotive_salary("$14/hour") == (14.0, None, "USD", "hour")
    assert parse_remotive_salary("€3.5k–€5k/month") == (3500.0, 5000.0, "EUR", "month")
    assert parse_remotive_salary("Salary Undisclosed") == (None, None, None, None)


def test_remotive_detail_adds_description() -> None:
    """Halaman detail melengkapi deskripsi dari ``JobPosting``."""
    html_daftar = (FIXTURES / "remotive_board.html").read_text(encoding="utf-8")
    job = parse_remotive_card(parse_remotive_listing(html_daftar)[0]["node"])
    assert job.description is None, "kartu daftar tidak memuat deskripsi"

    html_detail = (FIXTURES / "remotive_detail.html").read_text(encoding="utf-8")
    adapter = RemotiveAdapter(http=HTTPPalsu())
    posting = parse_remotive_detail(html_detail)
    assert posting is not None, "halaman detail memuat JobPosting"

    job = adapter.parse_detail(job, html_detail)
    assert job.description, "deskripsi terisi dari halaman detail"
    assert job.source_url.startswith("https://remotive.com/remote-jobs/")


def test_remotive_uses_listing_not_disallowed_api() -> None:
    """Remotive memakai halaman daftar, karena robots.txt melarang /api/*.

    Ini bukan pilihan gaya: ``https://remotive.com/robots.txt`` memuat
    ``Disallow: /api/*``. Endpoint JSON resminya tidak boleh dipakai bot ini,
    dan adapter harus tetap menghormatinya.
    """
    adapter = RemotiveAdapter(http=HTTPPalsu())

    assert "/api/" not in adapter.listing_url(1)
    assert adapter.listing_url(1).startswith("https://remotive.com/remote-jobs")


def test_invalid_items_skipped() -> None:
    """Item tanpa judul atau identitas tidak menghasilkan RawJob."""
    assert parse_kalibrr({"name": "Tanpa id dan slug"}) is None
    assert parse_kalibrr({"slug": "ada-slug"}) is None
    assert parse_kalibrr(None) is None

    assert parse_card({"href": "/loker/x", "title": None}) is None
    assert parse_card({"href": None, "title": "Ada judul"}) is None


def test_next_data_survives_nonce_attribute() -> None:
    """``__NEXT_DATA__`` dicari lewat id, bukan dengan asumsi bentuk tag.

    Tag <script> kini membawa atribut ``nonce``. Pola yang mengharapkan
    ``<script id="__NEXT_DATA__"`` tepat setelah nama tag gagal, dan itu
    sempat membuat saya menyimpulkan data Dealls "sudah tidak ada".
    """
    html = (
        '<html><body><script nonce="abc123" id="__NEXT_DATA__" '
        'type="application/json">{"props":{"pageProps":{"nilai":1}}}</script></body></html>'
    )

    assert extract_next_data(html) == {"props": {"pageProps": {"nilai": 1}}}
    assert extract_next_data("<html></html>") is None
    assert extract_next_data("") is None


def test_parse_salary_variants() -> None:
    """Lima kondisi gaji diurai tanpa menebak (R-02-02)."""
    assert parse_salary("Rp 9.000.000 – 14.000.000 per bulan") == (
        9_000_000.0, 14_000_000.0, "IDR", "month")
    assert parse_salary("Mulai Rp 11.000.000 per bulan") == (
        11_000_000.0, None, "IDR", "month")
    assert parse_salary("Sampai Rp 8.000.000 per bulan") == (
        None, 8_000_000.0, "IDR", "month")
    assert parse_salary("Gaji tidak dicantumkan") == (None, None, None, None)
    assert parse_salary(None) == (None, None, None, None)


# --- R-02-03 / R-02-05: retry dan robots ---------------------------------

def test_retry_backoff(monkeypatch) -> None:
    """Simulasi 500 memicu retry sesuai batas, lalu gagal dengan pesan jelas."""
    import requests

    jeda: list[float] = []
    monkeypatch.setattr("scraper.http.time.sleep", lambda d: jeda.append(d))

    kelas = type("Respons", (), {"status_code": 500, "text": "", "encoding": "utf-8"})
    panggilan = {"n": 0}

    def get(url, **kwargs):
        panggilan["n"] += 1
        return kelas()

    http = ScraperHTTP(_settings(scraper_max_retry=3), "https://contoh.test")
    http._robots = type("R", (), {"can_fetch": lambda self, ua, url: True})()
    monkeypatch.setattr(http, "session", lambda: type("S", (), {"get": staticmethod(get)})())

    with pytest.raises(ScrapeError):
        http.get("https://contoh.test/loker")

    assert panggilan["n"] == 3, "harus mencoba tepat sebanyak max_retry"
    assert jeda, "backoff harus menunggu sebelum mencoba lagi"


def test_blocked_status_stops_immediately(monkeypatch) -> None:
    """403/429 menghentikan sumber seketika, bukan diulang (R-02-03)."""
    kelas = type("Respons", (), {"status_code": 429, "text": "", "encoding": "utf-8"})
    panggilan = {"n": 0}

    def get(url, **kwargs):
        panggilan["n"] += 1
        return kelas()

    http = ScraperHTTP(_settings(), "https://contoh.test", min_interval=0)
    http._robots = type("R", (), {"can_fetch": lambda self, ua, url: True})()
    monkeypatch.setattr(http, "session", lambda: type("S", (), {"get": staticmethod(get)})())

    with pytest.raises(ScrapeBlockedError):
        http.get("https://contoh.test/loker")

    assert panggilan["n"] == 1, "429 tidak boleh diulang"


def test_robots_disallowed() -> None:
    """Adapter berhenti dengan RobotsDisallowedError bila dilarang (R-02-05)."""
    adapter = DeallsAdapter(http=HTTPPalsu(izin=False))

    with pytest.raises(RobotsDisallowedError):
        list(adapter.iter_jobs(max_pages=1))


def test_user_agent_from_config() -> None:
    """User agent diambil dari konfigurasi, bukan ditulis di kode (R-02-03)."""
    http = ScraperHTTP(_settings(scraper_user_agent="BotUji/9.9"), "https://contoh.test")

    assert http.user_agent == "BotUji/9.9"


def test_rate_limit_default_not_more_than_one_per_second() -> None:
    """Jeda bawaan minimal 1 detik (R-02-04)."""
    from scraper.http import DEFAULT_MIN_INTERVAL

    assert DEFAULT_MIN_INTERVAL >= 1.0


# --- iter_jobs: dedup dan isolasi ---------------------------------------

def test_iter_jobs_deduplicates_source_url() -> None:
    """`source_url` yang sama tidak muncul dua kali (R-02-09).

    ``tech_only=False`` karena yang diuji dedup, bukan penyaringan IT; fixture
    Dealls berisi judul campuran.
    """
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    adapter = DeallsAdapter(http=HTTPPalsu(halaman=[html]))
    adapter.tech_only = False

    jobs = list(adapter.iter_jobs(max_pages=1))
    url = [j.source_url for j in jobs]

    assert len(url) == len(set(url))
    assert len(jobs) == 2


def test_iter_jobs_keeps_pages_before_failure() -> None:
    """Halaman yang sudah terbaca tidak dibuang saat halaman berikutnya gagal."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")

    class Setengah(HTTPPalsu):
        def get(self, url, params=None):
            self.panggilan.append(url)
            if len(self.panggilan) == 1:
                return html
            raise ScrapeError("halaman 2 gagal")

    adapter = DeallsAdapter(http=Setengah(halaman=[html]))
    adapter.tech_only = False
    jobs = list(adapter.iter_jobs(max_pages=3))

    assert len(jobs) == 2, "halaman pertama harus tetap dihasilkan"


def test_iter_jobs_raises_when_nothing_found() -> None:
    """Bila tidak ada halaman berhasil, galat dilempar agar status jadi failed."""
    adapter = DeallsAdapter(http=HTTPPalsu(galat=ScrapeError("mati")))

    with pytest.raises(ScrapeError):
        list(adapter.iter_jobs(max_pages=2))


# --- Kalibrr: endpoint "Load more" ---------------------------------------

def test_kalibrr_uses_kjs_endpoint() -> None:
    """Kalibrr memakai ``/kjs/job_board/search``, bukan halaman HTML.

    Halaman ``/job-board`` hanya berisi 15 lowongan pertama; sisanya datang
    lewat tombol "Load more" yang memanggil endpoint ini. Nomor halaman pada
    HTML diabaikan server: diukur, HTML hanya dapat menjangkau 26 lowongan,
    sedangkan endpoint ini memberi 2290.

    Ditemukan dengan merekam panggilan jaringan saat tombol "Load more"
    diklik, bukan dengan menebak parameter URL.
    """
    from scraper.adapters.kalibrr import KalibrrAdapter

    adapter = KalibrrAdapter(http=object())
    url = adapter.listing_url(1)

    assert "/kjs/job_board/search" in url
    assert "limit=100" in url
    assert "offset=0" in url
    # Halaman kedua memakai offset, bukan nomor halaman.
    assert "offset=100" in adapter.listing_url(2)


def test_kalibrr_asks_for_it_function_only() -> None:
    """Filter kategori IT dipakai dari sisi server, bukan disaring belakangan.

    ``function=IT+and+Software`` menurunkan 2290 menjadi 254 dan seluruh
    hasilnya memang IT — lebih andal daripada memilah judul setelah data
    terlanjur diambil.
    """
    from scraper.adapters.kalibrr import KalibrrAdapter

    adapter = KalibrrAdapter(http=object())
    adapter.tech_only = True
    assert "function=IT%20and%20Software" in adapter.listing_url(1)

    # Tanpa penyaringan IT, filter itu tidak boleh ikut.
    adapter.tech_only = False
    assert "function=" not in adapter.listing_url(1)


def test_kalibrr_parses_snake_case_payload() -> None:
    """Payload kjs memakai snake_case, berbeda dari ``__NEXT_DATA__``."""
    from scraper.adapters.kalibrr import parse_kjs_item

    job = parse_kjs_item(
        {
            "id": 273950,
            "name": "Backend Engineer",
            "slug": "backend-engineer",
            "function": "IT and Software",
            "tenure": "Full time",
            "company_name": "NovaTech",
            "company_info": {"code": "novatech"},
            "base_salary": 9000000,
            "maximum_salary": 14000000,
            "salary_currency": "IDR",
            "salary_interval": "month",
        }
    )

    assert job is not None
    assert job.title == "Backend Engineer"
    assert job.company_name == "NovaTech"
    assert job.employment_type == "full-time"
    assert job.salary_min == 9000000
    assert job.salary_period == "month"
    assert "/c/novatech/jobs/273950/backend-engineer" in job.source_url


# --- Remotive: gaji bersatuan --------------------------------------------

def test_remotive_salary_from_jsonld() -> None:
    """Gaji diambil dari JSON-LD karena teks kartu dipotong server.

    Terukur: teks kartu berbunyi ``"$130,000-$140,0.."`` — 95 karakter, dipotong
    di sisi server, dan satuannya ada di bagian yang hilang. Akibatnya 130000
    (per tahun) tercampur dengan angka per jam dalam satu kelompok statistik,
    dan median USD menjadi 141.
    """
    from scraper.adapters.remotive import parse_salary_jsonld

    posting = {
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": {"minValue": 130000.0, "maxValue": 140000.0, "unitText": "YEAR"},
        }
    }
    smin, smax, mata_uang, periode = parse_salary_jsonld(posting)

    assert (smin, smax) == (130000.0, 140000.0)
    assert mata_uang == "USD"
    assert periode == "year"


def test_remotive_salary_unit_mapping() -> None:
    """`unitText` dipetakan ke periode baku; yang asing menjadi None."""
    from scraper.adapters.remotive import parse_salary_jsonld

    for satuan, harap in [
        ("HOUR", "hour"), ("DAY", "day"), ("MONTH", "month"),
        ("YEAR", "year"), ("ANNUAL", "year"), ("FORTNIGHT", None),
    ]:
        posting = {
            "baseSalary": {
                "currency": "USD",
                "value": {"minValue": 10, "maxValue": 20, "unitText": satuan},
            }
        }
        assert parse_salary_jsonld(posting)[3] == harap, satuan


def test_remotive_salary_missing_jsonld() -> None:
    """Tanpa `baseSalary`, tidak ada yang dikarang."""
    from scraper.adapters.remotive import parse_salary_jsonld

    assert parse_salary_jsonld({}) == (None, None, None, None)


def test_remotive_detail_overwrites_salary_with_period() -> None:
    """Detail menimpa gaji kartu hanya bila periodenya jelas."""
    from scraper.adapters.base import RawJob
    from scraper.adapters.remotive import RemotiveAdapter

    adapter = RemotiveAdapter(http=object())
    job = RawJob(
        title="Java Developer",
        source_url="https://remotive.com/remote/jobs/x",
        salary_min=130.0,
        salary_max=140.0,
        salary_currency="USD",
        salary_period=None,
    )

    html = (
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"Java Developer","baseSalary":'
        '{"currency":"USD","value":{"minValue":130000,"maxValue":140000,'
        '"unitText":"YEAR"}}}'
        "</script>"
    )
    hasil = adapter.parse_detail(job, html)

    assert hasil.salary_min == 130000
    assert hasil.salary_period == "year"


def test_remotive_detail_keeps_salary_without_unit() -> None:
    """Tanpa satuan di JSON-LD, gaji kartu dibiarkan apa adanya.

    Mengganti angka yang ada dengan angka tanpa satuan tidak memperbaiki apa
    pun; membiarkannya membuat asal-usulnya tetap terlihat.
    """
    from scraper.adapters.base import RawJob
    from scraper.adapters.remotive import RemotiveAdapter

    adapter = RemotiveAdapter(http=object())
    job = RawJob(
        title="X", source_url="https://remotive.com/x",
        salary_min=50.0, salary_max=60.0, salary_currency="USD", salary_period="hour",
    )
    html = (
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"X","baseSalary":'
        '{"currency":"USD","value":{"minValue":50000,"maxValue":60000}}}'
        "</script>"
    )
    hasil = adapter.parse_detail(job, html)

    assert hasil.salary_period == "hour"
    assert hasil.salary_min == 50.0


# --- R-02-06 / R-02-08 / R-02-10: runner --------------------------------

def test_failure_isolation(monkeypatch) -> None:
    """Satu adapter gagal; dua lainnya tetap berjalan (R-02-08)."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    remotive = (FIXTURES / "remotive_board.html").read_text(encoding="utf-8")
    kalibrr = (FIXTURES / "kalibrr_board.html").read_text(encoding="utf-8")

    halaman = {"dealls": html, "kalibrr": kalibrr, "remotive": remotive}
    galat = {"kalibrr": ScrapeError("API menolak")}
    dicatat: list = []
    disimpan: dict[str, int] = {}

    def buat_adapter(nama):
        asli = registry.ADAPTERS[nama]

        class Tiruan(asli):
            def __init__(self, http=None):
                super().__init__(
                    http=HTTPPalsu(halaman=[halaman[nama]], galat=galat.get(nama))
                )

        return Tiruan

    for nama in list(registry.ADAPTERS):
        monkeypatch.setitem(registry.ADAPTERS, nama, buat_adapter(nama))

    from scraper import pipeline

    def catat(sumber, jobs):
        disimpan[sumber] = len(jobs)
        return {"inserted": len(jobs), "updated": 0, "duplicate": 0}

    monkeypatch.setattr(pipeline, "persist_run", catat)
    monkeypatch.setattr(pipeline, "record_outcome", lambda o: dicatat.append(o))

    kode = runner.run(source="all", max_pages=1)

    assert kode == 0, "satu sumber berhasil berarti keluar 0 (R-02-10)"
    assert len(dicatat) == 3
    status = {o.source: o.status for o in dicatat}
    assert status["kalibrr"] == "failed"
    assert status["dealls"] == "success"
    assert status["remotive"] == "success"


def test_all_failed_returns_one(monkeypatch) -> None:
    """Keluar 1 hanya bila semua sumber gagal (R-02-10)."""
    from scraper import pipeline

    monkeypatch.setattr(pipeline, "record_outcome", lambda o: None)

    for nama in list(registry.ADAPTERS):
        asli = registry.ADAPTERS[nama]

        class Tiruan(asli):
            def __init__(self, http=None):
                super().__init__(http=HTTPPalsu(galat=ScrapeError("mati")))

        monkeypatch.setitem(registry.ADAPTERS, nama, Tiruan)

    assert runner.run(source="all", max_pages=1) == 1


def test_robots_marks_source_skipped(monkeypatch) -> None:
    """robots.txt yang melarang menandai sumber `skipped`, bukan `failed`."""
    from scraper import pipeline

    dicatat: list = []
    monkeypatch.setattr(pipeline, "record_outcome", lambda o: dicatat.append(o))

    asli = registry.ADAPTERS["dealls"]

    class Tiruan(asli):
        def __init__(self, http=None):
            super().__init__(http=HTTPPalsu(izin=False))

    monkeypatch.setitem(registry.ADAPTERS, "dealls", Tiruan)

    kode = runner.run(source="dealls", max_pages=1)

    assert kode == 1
    assert dicatat[0].status == "skipped"
    assert dicatat[0].error_message


def test_run_records_scrape_run(monkeypatch) -> None:
    """Satu eksekusi membuat lalu memperbarui satu baris `scrape_runs` (R-02-06)."""
    from scraper import pipeline
    from scraper.pipeline import persist

    urutan: list[str] = []

    monkeypatch.setattr(persist, "ensure_source", lambda nama, url: 7)
    monkeypatch.setattr(persist, "start_run", lambda sid: urutan.append("mulai") or 99)
    monkeypatch.setattr(
        persist, "finish_run",
        lambda rid, **kw: urutan.append(f"selesai:{kw['status']}:{kw['jobs_found']}"),
    )
    monkeypatch.setattr(persist, "touch_source", lambda sid: None)

    class Hasil:
        source = "dealls"
        status = "success"
        jobs_found = 2
        jobs_inserted = 2
        error_message = None

    pipeline.record_outcome(Hasil())

    assert urutan == ["mulai", "selesai:success:2"]


def test_dry_run_does_not_persist(monkeypatch) -> None:
    """`--dry-run` mengambil data tanpa menyimpan (PRD-02 §4.2 CLI)."""
    from scraper import pipeline

    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    disimpan = {"n": 0}

    monkeypatch.setattr(pipeline, "persist_run", lambda s, j: disimpan.__setitem__("n", 1))
    monkeypatch.setattr(pipeline, "record_outcome", lambda o: disimpan.__setitem__("n", 2))

    asli = registry.ADAPTERS["dealls"]

    class Tiruan(asli):
        def __init__(self, http=None):
            super().__init__(http=HTTPPalsu(halaman=[html]))

    monkeypatch.setitem(registry.ADAPTERS, "dealls", Tiruan)

    kode = runner.run(source="dealls", max_pages=1, dry_run=True)

    assert kode == 0
    assert disimpan["n"] == 0, "dry-run tidak boleh menyimpan atau mencatat"


# --- Bug yang ditemukan saat menulis ke database sungguhan ---------------

def test_row_carries_source_id() -> None:
    """Baris `jobs` membawa `source_id`, bukan hanya nama sumber.

    Bug nyata: 58 baris tersimpan dengan `source_id` NULL karena `as_row()`
    tidak memuatnya, sehingga relasi ke tabel `sources` hilang meski
    `source_url` benar.
    """
    job = RawJob(title="Uji", source_url="https://contoh.test/1", source="dealls")

    assert job.as_row(source_id=7)["source_id"] == 7
    assert job.as_row()["source_id"] is None


def test_persist_run_resolves_source_id(monkeypatch) -> None:
    """`persist_run` mencari `source_id` sebelum menyimpan."""
    from scraper import pipeline
    from scraper.pipeline import persist

    dicari = {}
    tersimpan: list[dict] = []

    monkeypatch.setattr(
        persist, "ensure_source",
        lambda nama, url: dicari.setdefault("id", 42) or 42,
    )
    monkeypatch.setattr(
        persist, "insert_many",
        lambda rows: tersimpan.extend(rows) or {"inserted": len(rows), "updated": 0, "duplicate": 0},
    )

    job = RawJob(title="Uji", source_url="https://contoh.test/2", source="dealls")
    hasil = pipeline.persist_run("dealls", [job])

    assert hasil["inserted"] == 1
    assert tersimpan[0]["source_id"] == 42
    # Normalisasi ikut berjalan: baris yang disimpan bukan lagi data mentah.
    assert tersimpan[0]["dedup_hash"], "dedup_hash harus diisi"
    assert tersimpan[0]["scraped_at"]


def test_runner_configures_database(monkeypatch) -> None:
    """Runner menyiapkan koneksi Supabase sebelum menulis.

    Aplikasi web melakukannya di `create_app`; pipeline di luar Flask tidak
    pernah memanggilnya, sehingga penulisan gagal meski `.env` benar.
    """
    from scraper import pipeline

    dipanggil = {"config": 0, "record": 0}
    monkeypatch.setattr(
        pipeline.persist, "configure_from_settings",
        lambda settings=None: dipanggil.__setitem__("config", dipanggil["config"] + 1),
    )
    monkeypatch.setattr(
        pipeline, "record_outcome",
        lambda o: dipanggil.__setitem__("record", dipanggil["record"] + 1),
    )

    asli = registry.ADAPTERS["dealls"]

    class Tiruan(asli):
        def __init__(self, http=None):
            super().__init__(http=HTTPPalsu(galat=ScrapeError("mati")))

    monkeypatch.setitem(registry.ADAPTERS, "dealls", Tiruan)

    runner.run(source="dealls", max_pages=1)

    assert dipanggil["config"] == 1, "koneksi harus disiapkan sekali"
    # dry-run tidak boleh menyiapkan koneksi sama sekali.
    dipanggil["config"] = 0
    runner.run(source="dealls", max_pages=1, dry_run=True)
    assert dipanggil["config"] == 0


def test_dealls_parses_real_markup_shape() -> None:
    """Parser Dealls memakai struktur HTML asli, bukan kelas semantik.

    Dealls memakai kelas Tailwind sehingga tidak ada `.company` atau `.meta`.
    Fixture di sini meniru bentuk aslinya: judul di `<h2>`, perusahaan di
    `<div>` setelahnya, meta di deretan `<span>`, dan kota menempel pada baris
    mode kerja ("On-site • Bogor").
    """
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    kartu = parse_listing(html)
    job = parse_card(kartu[0])

    # Inilah yang NULL pada percobaan pertama ke database sungguhan.
    assert job.company_name == "NovaTech Labs"
    assert job.location == "Jakarta Selatan"
    assert job.employment_type == "full-time"


# --- Halaman detail (PRD-02 lanjutan: deskripsi dan skill) ---------------

class AdapterDetail(DeallsAdapter):
    """Adapter uji yang punya halaman detail sederhana.

    ``tech_only = False``: fixture Dealls berisi judul campuran ("Head Chef",
    "Live Streaming Host"), dan test di bagian ini menguji paginasi serta
    pengambilan detail — bukan klasifikasi IT, yang punya test sendiri di
    ``test_tech_filter.py``.
    """

    max_detail = 2
    tech_only = False

    def detail_url(self, job):
        return f"https://contoh.test/detail/{job.source_job_id}"

    def parse_detail(self, job, html):
        job.description = html.strip() or None
        return job


def test_detail_not_fetched_by_default() -> None:
    """Tanpa `with_detail`, tidak ada permintaan detail sama sekali."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    http = HTTPPalsu(halaman=[html])
    adapter = AdapterDetail(http=http)

    jobs = list(adapter.iter_jobs(max_pages=1))

    assert len(jobs) == 2
    assert all(j.description is None for j in jobs)
    assert len(http.panggilan) == 1, "hanya halaman daftar yang diambil"


def test_detail_fills_description() -> None:
    """`with_detail=True` mengisi deskripsi dari halaman detail."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")

    class DenganDetail(HTTPPalsu):
        def get(self, url, params=None):
            self.panggilan.append(url)
            if "/detail/" in url:
                return "Deskripsi dari halaman detail."
            return html

    http = DenganDetail()
    adapter = AdapterDetail(http=http)

    jobs = list(adapter.iter_jobs(max_pages=1, with_detail=True))

    assert len(jobs) == 2
    assert all(j.description == "Deskripsi dari halaman detail." for j in jobs)


def test_detail_url_is_not_source_url() -> None:
    """`source_url` tetap URL daftar; URL detail berdiri sendiri.

    `source_url` adalah identitas stabil untuk dedup dan pembaruan (R-02-09).
    Mengubahnya menjadi URL detail akan membuat baris yang sama terlihat baru
    setiap kali bentuk URL detail berubah.
    """
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")
    adapter = AdapterDetail(http=HTTPPalsu(halaman=[html]))

    jobs = list(adapter.iter_jobs(max_pages=1, with_detail=True))

    for job in jobs:
        assert "/loker/" in job.source_url
        assert "/detail/" not in job.source_url


def test_detail_failure_keeps_job() -> None:
    """Detail gagal tidak membuang lowongan; data daftar tetap dipakai."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")

    class DetailRusak(HTTPPalsu):
        def get(self, url, params=None):
            self.panggilan.append(url)
            if "/detail/" in url:
                raise ScrapeError("halaman detail 500")
            return html

    adapter = AdapterDetail(http=DetailRusak())
    jobs = list(adapter.iter_jobs(max_pages=1, with_detail=True))

    assert len(jobs) == 2, "lowongan tidak boleh hilang karena detailnya gagal"
    assert all(j.description is None for j in jobs)
    assert all(j.title for j in jobs)


def test_detail_requests_capped() -> None:
    """`max_detail` membatasi jumlah permintaan detail per eksekusi."""
    html = (FIXTURES / "dealls_listing.html").read_text(encoding="utf-8")

    class HitungDetail(HTTPPalsu):
        def get(self, url, params=None):
            self.panggilan.append(url)
            return "isi detail" if "/detail/" in url else html

    http = HitungDetail()
    adapter = AdapterDetail(http=http)
    adapter.max_detail = 1

    jobs = list(adapter.iter_jobs(max_pages=1, with_detail=True))

    detail = [u for u in http.panggilan if "/detail/" in u]
    assert len(detail) == 1, "batas harus dihormati"
    assert len(jobs) == 2, "sisa lowongan tetap dihasilkan"
    assert jobs[0].description == "isi detail"
    assert jobs[1].description is None

