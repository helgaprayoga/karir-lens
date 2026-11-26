"""PRD-05 §7.1: service insight terhadap kontrak template.

Memakai klien PostgREST tiruan yang meniru agregasi nyata, sehingga test
memeriksa angka yang keluar — bukan sekadar bahwa fungsi dipanggil.
"""

from __future__ import annotations

import pytest

from app import create_app
from core.errors import NotFoundError


# --- Klien tiruan -------------------------------------------------------

class FakeResult:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class FakeQuery:
    def __init__(self, rows, sumber, nama):
        self._rows = rows
        self._sumber = sumber
        self._nama = nama
        self._predikat = []
        self._count = False

    def select(self, *_kolom, count=None):
        self._count = count == "exact"
        return self

    def eq(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        if self._nama == "clusters":
            return FakeResult(list(self._rows))
        if self._nama == "sources":
            return FakeResult(list(self._sumber))
        baris = [r for r in self._rows if all(p(r) for p in self._predikat)]
        return FakeResult(baris, len(baris))


class FakeDB:
    def __init__(self, jobs, clusters, sumber):
        self._jobs = jobs
        self._clusters = clusters
        self._sumber = sumber

    def table(self, nama):
        if nama == "clusters":
            return FakeQuery(self._clusters, self._sumber, "clusters")
        if nama == "sources":
            return FakeQuery([], self._sumber, "sources")
        return FakeQuery(self._jobs, self._sumber, "jobs")


def _job(i, **ubah):
    dasar = {
        "id": i,
        "title": f"Backend Engineer {i}",
        "company_name": "NovaTech Labs",
        "company_slug": "novatech-labs",
        "location": "Jakarta Pusat",
        "employment_type": "full-time",
        "description": "Deskripsi.",
        "skills": ["python", "sql"],
        "salary_min": 8_000_000,
        "salary_max": 12_000_000,
        "salary_currency": "IDR",
        "salary_period": "month",
        "source_id": 1,
        "source_url": f"https://dealls.com/{i}",
        "posted_at": "2026-11-01T00:00:00+00:00",
        "cluster_id": 1,
    }
    dasar.update(ubah)
    return dasar


SUMBER = [{"id": 1, "name": "dealls"}, {"id": 2, "name": "kalibrr"}]


@pytest.fixture
def insights(monkeypatch):
    from app.insights import repository

    jobs = [_job(i) for i in range(1, 11)]
    clusters = [
        {"id": 1, "label": "Backend", "keywords": ["python", "sql"]},
        {"id": 2, "label": "Frontend", "keywords": ["react"]},
    ]
    jobs[8]["cluster_id"] = 2
    jobs[9]["cluster_id"] = 2

    monkeypatch.setattr(repository, "_client", lambda: FakeDB(jobs, clusters, SUMBER))

    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app.test_client()


# --- R-05-06: kategori --------------------------------------------------

def test_categories_shape(insights) -> None:
    """`get_categories` mengembalikan kunci kontrak PRD-F05 §4.1."""
    from app.insights import service

    kategori = service.get_categories()

    assert kategori, "kategori tidak boleh kosong saat cluster ada"
    for k in kategori:
        assert set(k) == {"cluster_id", "label", "keywords", "job_count"}


def test_category_counts_match_jobs(insights) -> None:
    """Jumlah per kategori dihitung dari `jobs`, bukan kolom tersimpan.

    Kolom `clusters.job_count` ditulis saat clustering berjalan; bila ada
    lowongan yang dihapus sesudahnya angkanya basi. Halaman harus menampilkan
    angka yang sama dengan isi database saat dibuka.
    """
    from app.insights import service

    kategori = {k["cluster_id"]: k for k in service.get_categories()}

    assert kategori[1]["job_count"] == 8
    assert kategori[2]["job_count"] == 2


def test_empty_cluster_hidden(insights, monkeypatch) -> None:
    """Cluster tanpa lowongan tidak ditampilkan."""
    from app.insights import repository

    jobs = [_job(i) for i in range(1, 4)]
    clusters = [
        {"id": 1, "label": "Backend", "keywords": ["python"]},
        {"id": 99, "label": "Kosong", "keywords": []},
    ]
    monkeypatch.setattr(repository, "_client", lambda: FakeDB(jobs, clusters, SUMBER))

    from app.insights import service

    kategori = service.get_categories()
    assert [k["cluster_id"] for k in kategori] == [1]


# --- R-05-07: skill -----------------------------------------------------

def test_top_skills(insights) -> None:
    """`get_top_skills` mengembalikan skill dan jumlah lowongan."""
    from app.insights import service

    skills = service.get_top_skills()
    peta = {s["skill"]: s["job_count"] for s in skills}

    assert peta["python"] == 10
    assert peta["sql"] == 10
    assert set(skills[0]) == {"skill", "job_count"}


def test_skill_limit(insights) -> None:
    """`limit` membatasi jumlah skill yang dikembalikan."""
    from app.insights import service

    assert len(service.get_top_skills(limit=1)) == 1


# --- R-05-08..R-05-11: gaji ---------------------------------------------

def test_salary_from_service(insights) -> None:
    """Service meneruskan ke aturan salary: sampel dan kuartil benar."""
    from app.insights import service

    gaji = service.get_salary_stats()

    assert gaji["sample_sufficient"] is True
    grup = gaji["groups"][0]
    assert grup["currency"] == "IDR"
    assert grup["sample"] == 10
    assert grup["median"] == 10_000_000


def test_salary_insufficient(insights, monkeypatch) -> None:
    """`sample_sufficient` False saat sampel kurang dari lima (R-05-11)."""
    from app.insights import repository

    jobs = [_job(i) for i in range(1, 4)]
    monkeypatch.setattr(repository, "_client", lambda: FakeDB(jobs, [], SUMBER))

    from app.insights import service

    gaji = service.get_salary_stats()
    assert gaji["sample_sufficient"] is False
    assert gaji["groups"] == []


# --- Kontrak halaman ----------------------------------------------------

def test_insights_contract(insights) -> None:
    """`get_insights` memenuhi kontrak PRD-F05 §4.1 plus `summary`."""
    from app.insights import service

    data = service.get_insights()

    assert set(data) >= {"categories", "skills", "salary", "sample_sufficient"}
    assert data["sample_sufficient"] == data["salary"]["sample_sufficient"]

    summary = data["summary"]
    assert summary["total_jobs"] == 10
    assert summary["unique_skills"] == 2, "python dan sql"
    assert summary["categories"] == len(data["categories"])


def test_no_prediction_keys(insights) -> None:
    """Tidak ada field prediksi di keluaran mana pun (R-05-10)."""
    from app.insights import service

    teks = repr(service.get_insights()).lower()
    for kata in ("predict", "forecast", "estimate", "expected_salary"):
        assert kata not in teks, f"keluaran memuat {kata!r}"


# --- R-05-12: perusahaan ------------------------------------------------

def test_company_derived_from_jobs_only(insights) -> None:
    """`get_company` hanya memakai kolom dari tabel `jobs`."""
    from app.insights import service

    perusahaan = service.get_company("novatech-labs")

    assert set(perusahaan) == {
        "name", "slug", "job_count", "locations",
        "employment_types", "top_skills", "jobs",
    }
    assert perusahaan["job_count"] == 10
    assert perusahaan["name"] == "NovaTech Labs"


def test_company_not_found(insights) -> None:
    """Slug tanpa lowongan melempar NotFoundError, bukan halaman kosong."""
    from app.insights import service

    with pytest.raises(NotFoundError):
        service.get_company("tidak-ada")


# --- Route --------------------------------------------------------------

def test_insights_page_renders(insights) -> None:
    """`/insights` merender dengan data, bukan fixture."""
    resp = insights.get("/insights")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Backend" in body
    assert "python" in body


def test_insights_sample_low_forces_banner(insights) -> None:
    """`?sample=low` memaksa pesan data terbatas (§7.2 butir 4)."""
    body = insights.get("/insights?sample=low").get_data(as_text=True)

    assert "Data gaji belum dapat ditampilkan" in body


def test_unknown_period_not_labelled_monthly(insights, monkeypatch) -> None:
    """Gaji tanpa periode tidak dilabeli "bulanan".

    Terukur pada data nyata: 6 lowongan USD punya sampel cukup tetapi tanpa
    periode. Template lama memakai "bulanan" sebagai nilai cadangan — klaim
    yang tidak dimiliki data.

    Statistik kini dikelompokkan per kategori, jadi barisnya perlu
    ``cluster_id`` dan cluster-nya perlu label.
    """
    from app.insights import repository

    jobs = [
        _job(i, salary_currency="USD", salary_period=None, cluster_id=1,
             salary_min=4_000, salary_max=6_000)
        for i in range(1, 7)
    ]
    clusters = [{"id": 1, "label": "Backend", "keywords": ["python"]}]
    monkeypatch.setattr(repository, "_client", lambda: FakeDB(jobs, clusters, SUMBER))

    body = insights.get("/insights").get_data(as_text=True)

    assert "tidak menyebut periodenya" in body
    assert "bulanan" not in body.lower()


def test_company_page_renders(insights) -> None:
    """`/companies/<slug>` merender ringkasan turunan."""
    body = insights.get("/companies/novatech-labs").get_data(as_text=True)
    assert "NovaTech Labs" in body
    assert "10 lowongan tersedia" in body


def test_company_page_404(insights) -> None:
    assert insights.get("/companies/tidak-ada").status_code == 404
