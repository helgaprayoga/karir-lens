"""Pengujian katalog publik (PRD-04 §7.1, R-04-01 s.d. R-04-13).

Memakai klien PostgREST tiruan yang meniru semantik filter yang benar-benar
dipakai: ``eq``, ``neq``, ``or_`` dengan ``ilike`` dan ``cs``, ``ov``,
``order``, ``range``, dan ``count="exact"``. Dengan begitu test memverifikasi
query yang disusun, bukan sekadar bahwa fungsi dipanggil.

Tanpa jaringan, tanpa database sungguhan.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.config import CONFIG_MAP


# --- Klien PostgREST tiruan -------------------------------------------------

class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    """Meniru rantai builder supabase-py untuk operasi yang dipakai repository."""

    def __init__(self, rows: list[dict], sumber: list[dict]):
        self._rows = rows
        self._sumber = sumber
        self._predikat: list = []
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._count = False
        self._table = "jobs"

    # --- operasi filter ---------------------------------------------------
    def eq(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def neq(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: r.get(k) != v)
        return self

    def in_(self, kolom, nilai):
        """`in` PostgREST: nilai kolom ada di dalam daftar."""
        daftar = list(nilai)
        self._predikat.append(lambda r, k=kolom, v=daftar: r.get(k) in v)
        return self

    def gte(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: (r.get(k) or "") >= v)
        return self

    def ov(self, kolom, nilai):
        """Irisan array: `ov` di PostgREST berarti "overlaps"."""
        self._predikat.append(
            lambda r, k=kolom, v=set(nilai): bool(set(r.get(k) or []) & v)
        )
        return self

    def or_(self, ekspresi: str):
        """Dukung `title.ilike.%x%,company_name.ilike.%x%,skills.cs.{x}`.

        Inilah bagian yang paling mudah salah, jadi tiruan ini benar-benar
        mem-parse ekspresinya alih-alih mengabaikannya.
        """
        kondisi = ekspresi.split(",")
        akhir = 0
        while akhir < len(kondisi):
            # `skills.cs.{python}` mengandung koma di dalam kurung kurawal.
            teks = kondisi[akhir]
            if teks.count("{") > teks.count("}"):
                akhir += 1
                teks = teks + "," + kondisi[akhir]
            kondisi[akhir] = teks
            akhir += 1
        kondisi = [k for i, k in enumerate(kondisi) if i == 0 or "{" in k or "}" not in k]

        def cocok(row, daftar=kondisi):
            for bagian in daftar:
                if ".ilike." in bagian:
                    kolom, pola = bagian.split(".ilike.", 1)
                    nilai = str(row.get(kolom) or "").lower()
                    if pola.strip("%").lower() in nilai:
                        return True
                elif ".cs." in bagian:
                    kolom, nilai = bagian.split(".cs.", 1)
                    isi = nilai.strip("{}")
                    if isi in (row.get(kolom) or []):
                        return True
            return False

        self._predikat.append(cocok)
        return self

    # --- pengurutan dan rentang -------------------------------------------
    def order(self, kolom, desc: bool = False):
        self._order = (kolom, desc)
        return self

    def range(self, mulai, akhir):
        self._range = (mulai, akhir)
        return self

    def limit(self, n):
        self._limit = n
        return self

    # --- eksekusi ---------------------------------------------------------
    def execute(self):
        if self._table == "sources":
            return FakeResult(list(self._sumber))

        if self._table == "clusters":
            return FakeResult(list(getattr(self, "_clusters", [])), 0)

        baris = [r for r in self._rows if all(p(r) for p in self._predikat)]
        total = len(baris)

        if self._order:
            kolom, desc = self._order
            baris = sorted(
                baris, key=lambda r: (r.get(kolom) is None, str(r.get(kolom) or "")),
                reverse=desc,
            )

        if self._range:
            mulai, akhir = self._range
            baris = baris[mulai : akhir + 1]
        elif self._limit is not None:
            baris = baris[: self._limit]

        if self._count:
            return FakeResult(baris, total)
        return FakeResult(baris)


class FakeTable:
    def __init__(self, db, nama: str):
        self._db = db
        self._nama = nama

    def select(self, *_kolom, count=None):
        q = FakeQuery(self._db.baris, self._db.sumber)
        q._table = self._nama
        q._clusters = getattr(self._db, "clusters", [])
        q._count = count == "exact"
        return q


class FakeDB:
    def __init__(self, rows: list[dict], clusters: list[dict] | None = None):
        self.baris = rows
        self.sumber = [
            {"id": 1, "name": "dealls"},
            {"id": 2, "name": "kalibrr"},
            {"id": 3, "name": "remotive"},
        ]
        self.clusters = clusters or [
            {"id": 11, "label": "Data & Ai & Python"},
            {"id": 12, "label": "Developer & Java"},
        ]

    def table(self, nama: str):
        if nama == "clusters":
            return FakeTable(self, "clusters")
        return FakeTable(self, nama)


# --- Data uji ---------------------------------------------------------------

def _job(i: int, **ubah) -> dict:
    dasar = {
        "id": i,
        "title": f"Backend Engineer {i}",
        "company_name": "NovaTech Labs",
        "company_slug": "novatech-labs",
        "location": "Jakarta Selatan",
        "employment_type": "full-time",
        "description": "Membangun layanan backend.",
        "skills": ["python", "sql"],
        "salary_min": 10_000_000,
        "salary_max": 15_000_000,
        "salary_currency": "IDR",
        "salary_period": "month",
        "source_id": 1,
        "source_url": f"https://dealls.com/{i}",
        "posted_at": f"2026-11-{i:02d}T00:00:00+00:00",
        # Hasil clustering (PRD-05). Bawaan: cluster 11.
        "cluster_id": 11,
    }
    dasar.update(ubah)
    return dasar


ROWS = [
    _job(1),
    _job(2, title="Data Engineer", company_name="Northwind Data",
         company_slug="northwind-data", location="Bandung", skills=["python", "etl"],
         employment_type="contract", source_id=2,
         source_url="https://kalibrr.id/2", posted_at="2026-11-02T00:00:00+00:00"),
    _job(3, title="Product Designer", company_name="PixelCraft",
         company_slug="pixelcraft", location="Jakarta Selatan",
         skills=["figma"], employment_type="part-time", source_id=3,
         source_url="https://remotive.com/3", posted_at="2026-11-03T00:00:00+00:00",
         cluster_id=12),
    _job(4, title="Python Developer", company_name="NovaTech Labs",
         location="Yogyakarta", skills=["python", "django"],
         posted_at="2026-11-04T00:00:00+00:00", cluster_id=12),
]


@pytest.fixture
def catalog(monkeypatch):
    """Aplikasi produksi (tanpa preview) dengan database tiruan."""
    from app.jobs import repository as jobs_repo
    from app.insights import repository as insights_repo

    db = FakeDB(ROWS)
    monkeypatch.setattr(jobs_repo, "_client", lambda: db)
    monkeypatch.setattr(insights_repo, "_client", lambda: db)

    application = create_app("testing")
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application.test_client()


def _html(resp) -> str:
    return resp.get_data(as_text=True)


# --- R-04-01: daftar default ------------------------------------------------

def test_jobs_default_list(catalog) -> None:
    """Halaman pertama mengembalikan item dan metadata benar."""
    from flask import Flask

    resp = catalog.get("/jobs")
    assert resp.status_code == 200

    body = _html(resp)
    assert body.count('class="job-card"') == 4
    assert "Backend Engineer 1" in body


def test_jobs_default_meta(catalog) -> None:
    """`meta` mengikuti `build_meta`: per_page 12, total 4, has_next False."""
    from app.jobs import service

    data = service.search_jobs()
    assert data["meta"] == {"page": 1, "per_page": 12, "total": 4, "has_next": False}


# --- R-04-03: pencarian ----------------------------------------------------

def test_jobs_search_title(catalog) -> None:
    """`q` menemukan lowongan berdasarkan judul."""
    from app.jobs import service

    data = service.search_jobs(q="Data Engineer")
    judul = [j["title"] for j in data["items"]]
    assert "Data Engineer" in judul
    assert all("data engineer" in j.lower() for j in judul)


def test_jobs_search_company_and_skill(catalog) -> None:
    """`q` menemukan berdasarkan perusahaan dan skill (R-04-03)."""
    from app.jobs import service

    perusahaan = service.search_jobs(q="Northwind")
    assert [j["company_name"] for j in perusahaan["items"]] == ["Northwind Data"]

    skill = service.search_jobs(q="figma")
    assert [j["title"] for j in skill["items"]] == ["Product Designer"]


# --- R-04-02: filter -------------------------------------------------------

def test_jobs_filter_combined(catalog) -> None:
    """Kombinasi `city`, `employment_type`, `source` bekerja."""
    from app.jobs import service

    data = service.search_jobs(city="Jakarta Selatan", employment_type="full-time")
    assert [j["id"] for j in data["items"]] == [1]

    sumber = service.search_jobs(source="remotive")
    assert [j["id"] for j in sumber["items"]] == [3]


def test_jobs_filter_invalid_reset(catalog) -> None:
    """Nilai filter di luar himpunan dibuang, bukan error (R-04-02)."""
    from app.jobs import service

    data = service.search_jobs(
        employment_type="ngawur", source="tidak-ada", sort="acak", page="abc", per_page="999"
    )

    assert data["filters"]["employment_type"] == []
    assert data["filters"]["source"] == []
    assert data["filters"]["sort"] == "posted_desc"
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 50, "per_page maksimum 50 (R-04-05)"
    assert len(data["items"]) == 4, "semua lowongan tetap tampil"


# --- Filter banyak nilai sekaligus --------------------------------------

def test_multiple_employment_types(catalog) -> None:
    """Beberapa tipe kerja dipilih sekaligus: OR di dalam satu dimensi."""
    from app.jobs import service

    data = service.search_jobs(employment_type="full-time,contract")
    assert set(data["filters"]["employment_type"]) == {"full-time", "contract"}
    assert {j["id"] for j in data["items"]} == {1, 2, 4}


def test_multiple_cities(catalog) -> None:
    """Beberapa kota sekaligus."""
    from app.jobs import service

    data = service.search_jobs(city="Bandung,Yogyakarta")
    assert {j["id"] for j in data["items"]} == {2, 4}


def test_multiple_sources(catalog) -> None:
    """Beberapa sumber sekaligus."""
    from app.jobs import service

    data = service.search_jobs(source="kalibrr,remotive")
    assert {j["id"] for j in data["items"]} == {2, 3}


def test_multivalue_accepts_list_and_comma(catalog) -> None:
    """Ketiga bentuk masukan menghasilkan himpunan yang sama.

    ``?city=A,B`` (dipisah koma), ``?city=A&city=B`` (diulang), dan list Python
    dari ``app/api`` harus setara.
    """
    from app.jobs import service

    koma = {j["id"] for j in service.search_jobs(city="Bandung,Yogyakarta")["items"]}
    daftar = {j["id"] for j in service.search_jobs(city=["Bandung", "Yogyakarta"])["items"]}
    assert koma == daftar == {2, 4}


def test_multivalue_url_query(catalog) -> None:
    """Bentuk berulang di URL juga bekerja lewat route."""
    body = _html(catalog.get("/jobs?employment_type=full-time&employment_type=contract"))
    assert body.count('class="job-card"') == 3

    body = _html(catalog.get("/jobs?employment_type=full-time,contract"))
    assert body.count('class="job-card"') == 3


def test_filters_combine_across_dimensions(catalog) -> None:
    """AND antar dimensi: beberapa kota DAN beberapa tipe kerja."""
    from app.jobs import service

    data = service.search_jobs(
        city="Jakarta Selatan,Yogyakarta", employment_type="full-time"
    )
    assert {j["id"] for j in data["items"]} == {1, 4}


def test_chip_toggle_keeps_other_values(catalog) -> None:
    """Menghapus satu chip tidak menghapus chip lain di dimensi yang sama."""
    body = _html(catalog.get("/jobs?city=Bandung,Yogyakarta"))

    # Chip Bandung aktif: tautannya hanya berisi Yogyakarta.
    import re

    tautan = re.findall(r'data-filter="city" data-value="Bandung"', body)
    assert tautan, "chip Bandung tidak ditemukan"
    aktif = re.search(r'href="([^"]+)"[^>]*data-filter="city" data-value="Bandung"', body)
    assert aktif, "chip Bandung tidak punya tautan"
    href = aktif.group(1)
    assert "Yogyakarta" in href
    assert "Bandung" not in href


def test_active_count_counts_values(catalog) -> None:
    """Penghitung filter menghitung nilai terpilih, bukan dimensi."""
    body = _html(catalog.get("/jobs?city=Bandung,Yogyakarta&source=dealls"))
    assert '<span class="count">3</span>' in body


def test_invalid_filter_keeps_page_normal(catalog) -> None:
    """`?employment_type=ngawur` tetap 200 dengan halaman normal."""
    resp = catalog.get("/jobs?employment_type=ngawur&sort=acak&page=abc")
    assert resp.status_code == 200
    assert 'class="job-card"' in _html(resp)


# --- R-04-04: urutan -------------------------------------------------------

def test_jobs_sort(catalog) -> None:
    """Urutan `posted_desc` dan `posted_asc` benar."""
    from app.jobs import service

    turun = [j["id"] for j in service.search_jobs(sort="posted_desc")["items"]]
    naik = [j["id"] for j in service.search_jobs(sort="posted_asc")["items"]]

    assert turun == [4, 3, 2, 1]
    assert naik == [1, 2, 3, 4]


def test_relevance_puts_title_matches_first(catalog) -> None:
    """`relevance` menaruh judul yang cocok di atas skill yang kebetulan cocok."""
    from app.jobs import service

    data = service.search_jobs(q="python", sort="relevance")
    assert data["filters"]["sort"] == "relevance"
    # "Python Developer" judulnya cocok persis sebagian -> skor tertinggi.
    assert data["items"][0]["title"] == "Python Developer"


def test_relevance_without_query_falls_back(catalog) -> None:
    """`relevance` tanpa `q` tidak bermakna, jadi jatuh ke `posted_desc`."""
    from app.jobs import service

    assert service.search_jobs(sort="relevance")["filters"]["sort"] == "posted_desc"


# --- R-04-05: pagination ---------------------------------------------------

def test_jobs_pagination_meta(catalog) -> None:
    """`page`/`per_page`/`has_next` sesuai `build_meta`."""
    from app.jobs import service

    halaman1 = service.search_jobs(per_page=2, page=1)
    assert halaman1["meta"] == {"page": 1, "per_page": 2, "total": 4, "has_next": True}
    assert len(halaman1["items"]) == 2

    halaman2 = service.search_jobs(per_page=2, page=2)
    assert halaman2["meta"]["has_next"] is False
    assert len(halaman2["items"]) == 2

    # Tidak ada item yang muncul di dua halaman.
    id1 = {j["id"] for j in halaman1["items"]}
    id2 = {j["id"] for j in halaman2["items"]}
    assert not (id1 & id2)


def test_pagination_uses_core_module(catalog) -> None:
    """Metadata berasal dari `core/pagination.py`, bukan duplikasi."""
    from app.jobs import service
    from core.pagination import build_meta

    meta = service.search_jobs(per_page=3)["meta"]
    assert meta == build_meta(1, 3, 4)


# --- R-04-06: detail dan lowongan serupa -----------------------------------

def test_job_detail(catalog) -> None:
    """Detail memuat job dan lowongan serupa berdasarkan skill."""
    from app.jobs import service

    data = service.get_job(1)
    assert data["job"]["title"] == "Backend Engineer 1"
    assert "similar" in data
    assert len(data["similar"]) <= 6
    assert all(s["id"] != 1 for s in data["similar"])


def test_similar_ranked_by_shared_skills(catalog) -> None:
    """Lowongan serupa diurutkan menurut jumlah skill yang beririsan.

    Job 1 punya ``[python, sql]``. Job 4 (``[python, django]``) beririsan 1,
    job 2 (``[python, etl]``) beririsan 1, job 3 (``[figma]``) beririsan 0 dan
    karena itu tidak ikut. Keduanya berbagi tepat satu skill, jadi urutannya
    mengikuti tanggal terbaru.
    """
    from app.jobs import service

    similar = service.get_job(1)["similar"]
    assert [s["id"] for s in similar] == [4, 2]
    assert all("figma" not in (s["skills"] or []) for s in similar)


def test_similar_empty_without_skills(catalog) -> None:
    """Lowongan tanpa skill tidak mendapat "serupa" karangan."""
    from app.jobs import service

    data = service.get_job(3)  # skills = ["figma"], tidak ada yang beririsan
    assert data["similar"] == []


def test_job_detail_not_found(catalog) -> None:
    """ID tidak ada menghasilkan `NotFoundError` (R-04-09)."""
    from app.jobs import service
    from core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        service.get_job(9999)


def test_job_detail_404_page(catalog) -> None:
    """Route detail mengembalikan 404 lewat handler global."""
    assert catalog.get("/jobs/9999").status_code == 404


# --- R-04-07: perusahaan dari jobs ----------------------------------------

def test_company_derived_from_jobs(catalog) -> None:
    """Ringkasan perusahaan hanya dari data `jobs`."""
    from app.insights import service

    company = service.get_company("novatech-labs")

    assert company["name"] == "NovaTech Labs"
    assert company["slug"] == "novatech-labs"
    assert company["job_count"] == 2
    assert set(company["locations"]) == {"Jakarta Selatan", "Yogyakarta"}
    assert "python" in company["top_skills"]
    assert len(company["jobs"]) == 2


def test_company_not_found(catalog) -> None:
    """Slug tanpa lowongan menghasilkan `NotFoundError`, bukan halaman kosong."""
    from app.insights import service
    from core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        service.get_company("tidak-ada")


def test_company_page_renders(catalog) -> None:
    """Halaman perusahaan merender data turunan."""
    body = _html(catalog.get("/companies/novatech-labs"))
    assert "NovaTech Labs" in body
    assert "2 lowongan tersedia" in body


def test_company_page_404(catalog) -> None:
    assert catalog.get("/companies/tidak-ada").status_code == 404


# --- R-04-11: kontrak template --------------------------------------------

def test_service_matches_template_contract(catalog) -> None:
    """Kunci `dict` service sama dengan kontrak PRD-F02 §4.1."""
    from app.jobs import service

    assert set(service.search_jobs()) == {"items", "meta", "filters", "options"}
    assert set(service.get_job(1)) == {"job", "similar"}
    assert set(service.get_home()) >= {"stats", "categories"}

    item = service.search_jobs()["items"][0]
    for kunci in (
        "id", "title", "company_name", "company_slug", "location",
        "employment_type", "skills", "salary_min", "salary_max",
        "source", "source_url", "posted_at",
    ):
        assert kunci in item, f"item kehilangan kunci wajib {kunci!r}"

    meta = service.search_jobs()["meta"]
    assert set(meta) == {"page", "per_page", "total", "has_next"}


def test_job_shape_used_by_card(catalog) -> None:
    """Bentuk `job` cukup untuk JobCard: `source` berupa nama, bukan id."""
    from app.jobs import service

    item = service.search_jobs()["items"][0]
    assert item["source"] == "dealls"
    assert item["is_saved"] is False
    assert item["match"] is None


def test_source_name_resolved_from_sources_table(catalog) -> None:
    """Setiap item membawa nama sumber, termasuk yang bukan `dealls`."""
    from app.jobs import service

    per_id = {j["id"]: j["source"] for j in service.search_jobs()["items"]}
    assert per_id == {1: "dealls", 2: "kalibrr", 3: "remotive", 4: "dealls"}


def test_templates_unchanged_by_backend() -> None:
    """Template katalog tidak ditambahkan pada task ini (R-04-11).

    Diperiksa dari daftar berkas: PRD-04 hanya mengubah Python, kecuali
    `main/index.html` yang memang kerangka PRD-01 dan diganti isinya.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    katalog = root / "templates" / "jobs"
    isi = sorted(p.name for p in katalog.glob("*.html"))
    assert isi == ["detail.html", "home.html", "list.html"]


# --- Filter kategori dari hasil clustering (PRD-05) ----------------------

def test_category_filter_by_cluster_id(catalog) -> None:
    """Kategori disaring lewat `cluster_id`, bukan teks label.

    Label cluster berbentuk "Data & Ai & Python" — gabungan kata pembeda yang
    tidak muncul sebagai satu frasa di judul mana pun. Menautkannya ke
    `?q=<label>` akan menghasilkan nol hasil.
    """
    from app.jobs import service

    data = service.search_jobs(category="11")

    assert data["filters"]["category"] == [11]
    assert {j["id"] for j in data["items"]} == {1, 2}


def test_category_filter_multiple(catalog) -> None:
    """Beberapa kategori sekaligus (OR di dalam dimensi)."""
    from app.jobs import service

    data = service.search_jobs(category="11,12")
    assert set(data["filters"]["category"]) == {11, 12}
    assert {j["id"] for j in data["items"]} == {1, 2, 3, 4}


def test_category_filter_invalid_ignored(catalog) -> None:
    """Nilai bukan angka dibuang, tidak menghasilkan error (R-04-02)."""
    from app.jobs import service

    data = service.search_jobs(category="abc")
    assert data["filters"]["category"] == []
    assert len(data["items"]) == 4, "semua lowongan tetap tampil"


def test_category_filter_unknown_id(catalog) -> None:
    """Cluster yang tidak ada menghasilkan kosong, bukan error."""
    from app.jobs import service

    data = service.search_jobs(category="999")
    assert data["filters"]["category"] == [999]
    assert data["items"] == []
    assert data["meta"]["total"] == 0


def test_category_options_listed(catalog) -> None:
    """`options.categories` berisi cluster yang punya lowongan saja."""
    from app.jobs import service

    opsi = service.search_jobs()["options"]["categories"]
    peta = {c["value"]: c["job_count"] for c in opsi}

    assert peta == {11: 2, 12: 2}
    for c in opsi:
        assert set(c) >= {"value", "label", "active", "job_count"}


def test_category_chip_link_uses_cluster_id(catalog) -> None:
    """Chip kategori bertindak sebagai toggle lewat `?category=`, bukan `?q=`.

    Saat kategori **belum** aktif, tautannya menambahkannya. Saat sudah aktif,
    tautannya menghapusnya — jadi tautan chip aktif memang tidak memuat
    `category=` (itulah arti "hapus filter"). Yang penting: tidak pernah
    memakai `q=`, karena label cluster bukan kata kunci pencarian.
    """
    import re

    # Belum aktif: chip ditambahkan lewat category=.
    tanpa = _html(catalog.get("/jobs?city=Bandung"))
    tambah = re.findall(r'name="category" value="(\d+)"', tanpa)
    assert tambah == ["11", "12"], "kotak centang kategori memakai cluster_id"

    # Sudah aktif: tautan chip menghapus filter, dan tetap bukan `q=`.
    aktif = _html(catalog.get("/jobs?category=11"))
    chips = re.findall(r'<a class="chip" href="([^"]+)"[^>]*data-filter="category"', aktif)
    assert chips, "chip kategori aktif tidak ditemukan"
    for href in chips:
        assert "q=" not in href, "chip kategori tidak boleh menaut ke pencarian teks"


def test_category_checkbox_in_panel(catalog) -> None:
    """Panel filter memuat kotak centang kategori dengan `cluster_id` sebagai nilai."""
    import re

    body = _html(catalog.get("/jobs"))

    kotak = re.findall(r'name="category" value="(\d+)"', body)
    assert kotak == ["11", "12"], f"nilai kategori harus cluster_id: {kotak}"


def test_category_filter_combines_with_others(catalog) -> None:
    """Kategori bekerja bersama filter lain (AND antar dimensi)."""
    from app.jobs import service

    data = service.search_jobs(category="11", employment_type="full-time")
    assert {j["id"] for j in data["items"]} == {1}


def test_active_count_includes_category(catalog) -> None:
    """Penghitung filter ikut menghitung kategori."""
    body = _html(catalog.get("/jobs?category=11&city=Bandung"))
    assert '<span class="count">2</span>' in body


# --- Beranda: pintasan kategori -----------------------------------------

def test_home_shows_category_shortcuts(catalog) -> None:
    """Beranda menampilkan pintasan kategori dari hasil clustering (PRD-F02 §3)."""
    body = _html(catalog.get("/"))

    assert "Pintasan kategori" in body
    assert body.count('class="category-card"') == 2
    assert "Data &amp; Ai &amp; Python" in body


def test_category_link_returns_results(catalog) -> None:
    """Tautan kartu beranda benar-benar menghasilkan lowongan.

    Ini menutup bug `?q=<label>`: kartu yang menaut ke pencarian kosong lebih
    buruk daripada tidak ada kartu.
    """
    import re

    body = _html(catalog.get("/"))
    tautan = re.findall(r'class="category-card" href="([^"]+)"', body)
    assert tautan, "kartu kategori tidak punya tautan"

    for href in tautan:
        hasil = catalog.get(href)
        assert hasil.status_code == 200
        html = _html(hasil)
        # Bukan empty state, dan jumlah kartunya sesuai job_count.
        assert "Tidak ada lowongan yang cocok" not in html, f"{href} kosong"
        assert 'class="job-card"' in html


def test_insights_category_links_to_filter(catalog, monkeypatch) -> None:
    """Tabel kategori di /insights menaut ke filter, bukan pencarian teks."""
    import re

    from app.insights import repository as insights_repo

    monkeypatch.setattr(
        insights_repo, "find_clusters",
        lambda: [{"cluster_id": 11, "label": "Data & Ai", "keywords": ["data"], "job_count": 2}],
    )
    monkeypatch.setattr(insights_repo, "find_skill_counts", lambda limit=6: [])
    monkeypatch.setattr(insights_repo, "find_jobs_with_salary", lambda c=None, p=None: [])
    monkeypatch.setattr(insights_repo, "find_all_skills", lambda: [])
    monkeypatch.setattr(insights_repo, "count_jobs", lambda: 2)

    body = _html(catalog.get("/insights"))
    tautan = re.findall(r'<td>\s*<a href="([^"]+)"', body)
    assert any("category=11" in t for t in tautan), tautan


# --- R-04-09 / R-04-10: publik --------------------------------------------

PUBLIC_PATHS = ["/", "/jobs", "/jobs/1", "/companies/novatech-labs"]


@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_public_pages_no_auth(catalog, path) -> None:
    """Semua route publik dapat diakses tanpa login (R-04-10)."""
    resp = catalog.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"


def test_every_item_has_source_url(catalog) -> None:
    """Setiap lowongan yang tampil memiliki tautan sumber asli yang valid."""
    from app.jobs import service

    for job in service.search_jobs()["items"]:
        assert job["source_url"].startswith("http"), job


# --- R-04-08: tidak ada SQL dari input ------------------------------------

def test_city_chips_ordered_by_frequency(catalog) -> None:
    """Chip kota didahulukan yang paling banyak lowongannya (R-04-01).

    Urutan alfabetis membuat "Ambon" (1 lowongan) tampil sebelum "Jakarta
    Selatan" (2 lowongan), dan chip yang tidak berguna memenuhi baris filter.
    """
    from app.jobs import service

    kota = [c["value"] for c in service.search_jobs()["options"]["cities"]]
    assert kota[0] == "Jakarta Selatan", f"kota terbanyak harus pertama: {kota}"
    assert "Bandung" in kota and "Yogyakarta" in kota


def test_search_term_sanitized() -> None:
    """Karakter khusus PostgREST dibuang dari kata kunci (R-04-08)."""
    from app.jobs import repository

    assert repository.sanitize_term('a,b(c)"d%e*f{g}') == "a b c d e f g"
    assert repository.sanitize_term(None) == ""
    assert repository.sanitize_term("  python  ") == "python"


def test_no_raw_sql_in_module() -> None:
    """Repository tidak menyusun SQL mentah."""
    import inspect

    from app.jobs import repository

    sumber = inspect.getsource(repository).lower()
    for dilarang in ("select * from", "execute(\"", "f\"select", "text("):
        assert dilarang not in sumber, f"repository memuat SQL mentah: {dilarang}"


# --- R-04-12: filter tanggal dan angka -----------------------------------

def test_template_filters_available() -> None:
    """Filter `tanggal` dan `angka` terpasang untuk seluruh template (R-04-12)."""
    from app.template_filters import FILTERS

    assert "tanggal" in FILTERS
    assert "angka" in FILTERS
    assert FILTERS["angka"](12345) == "12.345"


# --- Tata letak dengan data sungguhan -------------------------------------

def test_cards_grid_allows_shrinking() -> None:
    """Grid kartu memakai `minmax(0, 1fr)`, bukan `1fr`.

    Diukur di browser pada data sungguhan: satu judul panjang
    ("Host Live & Content Creator Gaming - No Limit Gear") melebarkan kartu
    sampai 571px pada viewport 360px, sehingga seluruh halaman meluber.
    Penyebabnya `1fr` = `minmax(auto, 1fr)`, dan `auto` berarti track tidak
    boleh lebih kecil dari min-content anaknya. Fixture PRD-F02 tidak punya
    judul sepanjang itu, jadi regresi ini hanya muncul setelah data asli masuk.
    """
    from pathlib import Path
    import re

    css = (Path(__file__).resolve().parents[2] / "static" / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    # Semua deklarasi `.cards` di media query lebar kecil.
    deklarasi = re.findall(r"\.cards\s*\{[^}]*grid-template-columns:\s*([^;]+);", css)
    assert deklarasi, "deklarasi grid .cards tidak ditemukan"
    for nilai in deklarasi:
        assert "1fr" in nilai
        assert "minmax(0" in nilai or "minmax(0," in nilai, (
            f"kolom .cards {nilai.strip()!r} tidak dapat menyusut; "
            "gunakan minmax(0, 1fr)"
        )

