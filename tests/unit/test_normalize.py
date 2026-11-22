"""PRD-03 §7.1: normalisasi dan deduplikasi.

Semua test **murni**: tidak ada jaringan, tidak ada database, tidak ada AI
(R-03-01, R-03-14). Contoh input diambil dari data nyata di database agar
aturannya diuji terhadap bentuk yang benar-benar ada, bukan karangan.
"""

from __future__ import annotations

import pytest

from scraper.adapters.base import RawJob
from scraper.pipeline import dedup, normalize
from scraper.pipeline.persist import FIELD_DIPERBARUI


def _job(**ubah) -> dict:
    """Baris mentah berbentuk dict — sama dengan yang dihasilkan ``RawJob.as_row()``."""
    dasar = {
        "title": "Backend Engineer",
        "source_url": "https://contoh.test/1",
        "company_name": "NovaTech Labs",
    }
    dasar.update(ubah)
    return dasar


# --- R-03-02: teks -------------------------------------------------------

def test_normalize_title_whitespace() -> None:
    """Whitespace ganda, entity, dan tag HTML dirapikan (R-03-02).

    Data nyata memuat judul seperti "LIVE STREAMING HOST & CONTENT CREATOR —
    Press On Nails | Full-time, On-site". Entity ``&amp;`` harus menjadi ``&``.
    """
    hasil = normalize.normalize(_job(title="  Backend   Engineer &amp;  Data  "))
    assert hasil["title"] == "Backend Engineer & Data"

    hasil = normalize.normalize(_job(title="<b>Senior</b>   Developer\n"))
    assert hasil["title"] == "Senior Developer"

    # Kapitalisasi asli dipertahankan: "PT" dan "pt" berbeda arti.
    assert normalize.normalize(_job(title="PHP Developer"))["title"] == "PHP Developer"


def test_company_slug_generation() -> None:
    """Slug konsisten untuk penulisan perusahaan berbeda (R-03-03).

    "PT Sinar Mitra Finance" dan "pt  sinar mitra finance" harus menghasilkan
    slug yang sama agar halaman perusahaan tidak terpecah.
    """
    a = normalize.normalize(_job(company_name="PT Sinar Mitra Finance"))["company_slug"]
    b = normalize.normalize(_job(company_name="  pt  Sinar Mitra Finance "))["company_slug"]

    assert a == b == "pt-sinar-mitra-finance"
    assert not a.startswith("-") and not a.endswith("-")


def test_slug_drops_punctuation() -> None:
    """Titik pada "PT. Digivana" tidak boleh menjadi bagian slug.

    Data nyata memuat "PT. Digivana Solusi Digital"; slug yang keluar harus
    ``pt-digivana-solusi-digital``, bukan ``pt.-digivana-solusi-digital``.
    """
    slug = normalize.normalize(
        _job(company_name="PT. Digivana Solusi Digital")
    )["company_slug"]

    assert slug == "pt-digivana-solusi-digital"
    assert "." not in slug
    assert not slug.startswith("-") and not slug.endswith("-")


def test_employment_type_mapping() -> None:
    """Seluruh varian terpetakan ke himpunan baku (R-03-04)."""
    for mentah, harap in [
        ("Full Time", "full-time"),
        ("fulltime", "full-time"),
        ("Full_Time", "full-time"),
        ("Penuh waktu", "full-time"),
        ("Kontrak", "contract"),
        ("Part Time", "part-time"),
        ("Paruh waktu", "part-time"),
        ("Magang", "internship"),
        ("Lepas", "freelance"),
        ("something else", "unknown"),
        (None, "unknown"),
        ("", "unknown"),
    ]:
        hasil = normalize.normalize(_job(employment_type=mentah))["employment_type"]
        assert hasil == harap, f"{mentah!r} -> {hasil!r}, seharusnya {harap!r}"


def test_employment_type_output_is_always_canonical() -> None:
    """Keluarannya selalu salah satu himpunan baku, tidak pernah nilai mentah."""
    for mentah in ("Full Time", "xyz", None, "Contract"):
        hasil = normalize.normalize(_job(employment_type=mentah))["employment_type"]
        assert hasil in normalize.EMPLOYMENT_TYPES


def test_description_strip_html() -> None:
    """Tag HTML dan entity hilang, baris per butir dipertahankan (R-03-05).

    Dealls menyimpan deskripsi sebagai `<ul><li>…</li></ul>`. Tanpa batas
    baris, seluruh butir menempel menjadi satu paragraf panjang.
    """
    mentah = (
        "<ul><li>Mengembangkan layanan &amp; API.</li>"
        "<li>Menjaga   kualitas data.</li></ul>"
    )
    hasil = normalize.normalize(_job(description=mentah))["description"]

    assert "<" not in hasil and "&amp;" not in hasil
    assert "Mengembangkan layanan & API." in hasil
    assert hasil.count("\n") >= 1, "butir harus terpisah baris"


def test_description_truncated_with_marker() -> None:
    """Deskripsi melebihi batas dipotong dengan penanda, bukan di tengah kata."""
    panjang = "kata " * 6000
    hasil = normalize.normalize(_job(description=panjang))["description"]

    assert len(hasil) <= normalize.MAX_DESCRIPTION
    assert hasil.endswith("…")


def test_skills_dedup_and_order() -> None:
    """Skill lowercase, unik, terurut (R-03-06)."""
    hasil = normalize.normalize(
        _job(skills=["Python", "python", " SQL ", "go", "a"])
    )["skills"]

    assert hasil == sorted(hasil)
    assert hasil.count("python") == 1
    assert "sql" in hasil
    # 'a' satu huruf dibuang oleh core/skills.
    assert "a" not in hasil


# --- R-03-07: gaji dan tanggal ------------------------------------------

def test_salary_normalization() -> None:
    """``min <= max``, nilai tidak valid ditolak, periode baku (R-03-07)."""
    # Urutan tertukar: ditukar, bukan dibuang.
    hasil = normalize.normalize(_job(salary_min=18_000_000, salary_max=12_000_000))
    assert hasil["salary_min"] == 12_000_000
    assert hasil["salary_max"] == 18_000_000

    # Nol dan negatif adalah ketiadaan data, bukan gaji.
    assert normalize.normalize(_job(salary_min=0))["salary_min"] is None
    assert normalize.normalize(_job(salary_max=-5))["salary_max"] is None

    # Gaji parsial disimpan apa adanya.
    parsial = normalize.normalize(_job(salary_min=9_000_000, salary_max=None))
    assert parsial["salary_min"] == 9_000_000
    assert parsial["salary_max"] is None


def test_salary_currency_and_period() -> None:
    """Mata uang tiga huruf; periode hanya dari himpunan baku."""
    assert normalize.normalize(_job(salary_currency="idr"))["salary_currency"] == "IDR"
    assert normalize.normalize(_job(salary_currency="rupiah"))["salary_currency"] is None
    assert normalize.normalize(_job(salary_currency="US"))["salary_currency"] is None

    assert normalize.normalize(_job(salary_period="MONTH"))["salary_period"] == "month"
    assert normalize.normalize(_job(salary_period="weekly"))["salary_period"] is None


def test_posted_at_normalized_to_utc() -> None:
    """Tanggal menjadi ISO-8601 UTC, atau ``None`` bila tak terbaca."""
    assert normalize.normalize(
        _job(posted_at="2026-11-17T09:21:26.139Z")
    )["posted_at"] == "2026-11-17T09:21:26.139000+00:00"

    assert normalize.normalize(_job(posted_at="bukan tanggal"))["posted_at"] is None
    assert normalize.normalize(_job(posted_at=None))["posted_at"] is None


# --- Asal skill: declared vs inferred ------------------------------------

def test_declared_skills_win() -> None:
    """Skill dari sumber sendiri berlabel ``declared`` (R-03-06 lanjutan)."""
    hasil = normalize.normalize(
        _job(skills=["Python", "SQL"], description="Experience with Python and SQL.")
    )
    assert hasil["skills_source"] == "declared"
    assert hasil["skills"] == ["python", "sql"]


def test_inferred_skills_for_source_without_field() -> None:
    """Sumber tanpa field skill mendapat ``inferred``, bukan kosong.

    Dealls menyatakan skill-nya; Kalibrr dan Remotive hanya punya prosa. Tanpa
    inferensi, 32 dari 49 lowongan tampil tanpa satu pun skill di kartunya.
    """
    hasil = normalize.normalize(
        _job(
            title="Backend Software Engineer",
            skills=[],
            description=(
                "Requirements:\n"
                "Proficient in at least one programming language such as Golang, "
                "C++, C, or Python.\n"
                "Strong understanding of SQL and NoSQL databases."
            ),
        )
    )
    assert hasil["skills_source"] == "inferred"
    assert "python" in hasil["skills"]
    assert "sql" in hasil["skills"]


def test_no_skills_has_no_origin() -> None:
    """Tanpa skill sama sekali, asalnya ``None`` — bukan ``inferred`` kosong."""
    hasil = normalize.normalize(
        _job(title="Community Officer", skills=[], description="melayani pelanggan")
    )
    assert hasil["skills"] == []
    assert hasil["skills_source"] is None


def test_inferred_ignores_recruiter_boilerplate() -> None:
    """Skill tidak diambil dari bagian promosi di atas syarat sebenarnya.

    Terukur pada data nyata: Lemon.io menulis "New roles for Senior React
    Full-stack Engineers come in all the time" di bagian promosi, sehingga
    "Senior Data Engineer" mendapat ``react`` bila seluruh deskripsi dibaca.
    """
    hasil = normalize.normalize(
        _job(
            title="Senior Data Engineer",
            skills=[],
            description=(
                "Lemon.io helps companies hire experienced engineers.\n"
                "New roles for Senior React Full-stack Engineers come in all the time.\n"
                "Who we're looking for\n"
                "Experience with Apache Airflow and Snowflake, or Python and SQL, is required\n"
                "Experience with AWS, GCP, or Microsoft Azure is mandatory\n"
                "NOT YOUR TECH STACK?\n"
                "We place React, Golang, and Ruby developers."
            ),
        )
    )
    assert hasil["skills_source"] == "inferred"
    assert "react" not in hasil["skills"], "boilerplate tidak boleh jadi skill"
    assert "python" in hasil["skills"]
    assert "airflow" in hasil["skills"]


def test_inferred_skips_device_requirements() -> None:
    """Syarat perangkat keras bukan skill.

    "Content Reviewer" menyebut "a reliable computer and a smartphone
    (Android 5.0, iOS 14 or higher)"; itu spesifikasi perangkat, bukan
    kemampuan yang diminta, sehingga ``android``/``ios`` tidak boleh muncul.
    """
    from core.skills import infer_skills

    hasil = infer_skills(
        "Content Reviewer",
        "Qualifications to succeed in this project:\n"
        "Professional fluency in English\n"
        "Access to a stable broadband internet, a reliable computer and a "
        "smartphone (Android 5.0, iOS 14 or higher)\n"
        "Experience with content moderation.",
    )
    assert "android" not in hasil, f"perangkat bukan skill: {hasil}"
    assert "ios" not in hasil, f"perangkat bukan skill: {hasil}"


def test_rest_is_not_rest_api() -> None:
    """Prosa "the rest of our content team" bukan REST API.

    Alias ``rest`` -> ``rest api`` dulu membuat kata biasa di prosa menjadi
    skill. Alias itu dihapus dari kamus.
    """
    from core.skills import match_skills

    assert match_skills("the rest of our content management team") == []
    assert match_skills("Restaurants Contracting") == []
    # Bentuk yang memang menyebut REST tetap dikenali.
    assert "rest api" in match_skills("Build REST APIs with Django")


def test_requirement_section_extraction() -> None:
    """Hanya isi di bawah heading syarat yang diambil."""
    from core.skills import requirement_section

    teks = (
        "About us\nWe are great.\n"
        "Requirements\nPython and SQL.\n"
        "Benefits\nFree lunch and React conference tickets."
    )
    bagian = requirement_section(teks)

    assert bagian is not None
    assert "python" in bagian.lower()
    assert "react" not in (bagian or "").lower(), "bagian Benefits tidak ikut"
    assert "free lunch" not in (bagian or "").lower()


# --- R-03-11: data tidak lengkap -----------------------------------------

def test_incomplete_data_saved() -> None:
    """Field kosong tersimpan sebagai ``None``/list kosong, bukan string palsu."""
    hasil = normalize.normalize(_job(company_name=None, location="", description=None))

    assert hasil["company_name"] is None
    assert hasil["company_slug"] is None
    assert hasil["location"] is None
    assert hasil["description"] is None
    assert hasil["skills"] == []
    assert hasil["salary_min"] is None


def test_normalize_accepts_dict() -> None:
    """Menerima dict juga, agar PRD-07 dapat memakai aturan yang sama."""
    hasil = normalize.normalize({
        "title": " Data Engineer ",
        "source_url": "https://contoh.test/9",
        "employment_type": "Full Time",
    })

    assert hasil["title"] == "Data Engineer"
    assert hasil["employment_type"] == "full-time"


# --- R-03-08: dedup_hash ------------------------------------------------

def test_dedup_hash_stable() -> None:
    """Hash stabil untuk input setara, berbeda untuk input berbeda (R-03-08).

    ``hash()`` bawaan Python diacak per proses (PYTHONHASHSEED), sehingga hash
    yang tidak stabil akan membuat seluruh baris terlihat baru setiap eksekusi.
    """
    a = dedup.compute_hash({"title": "Backend Engineer", "company_name": "NovaTech"})
    b = dedup.compute_hash({"title": "  backend   engineer ", "company_name": "NOVATECH"})
    c = dedup.compute_hash({"title": "Backend Engineer", "company_name": "NovaTech"})
    d = dedup.compute_hash({"title": "Frontend Engineer", "company_name": "NovaTech"})

    assert a == b == c, "penulisan setara harus menghasilkan hash sama"
    assert a != d
    assert len(a) == 64, "SHA-256 dalam hex"


def test_dedup_hash_includes_location() -> None:
    """Lokasi ikut dihitung: judul sama di kota berbeda bukan duplikat."""
    a = dedup.compute_hash({"title": "Designer", "company_name": "X", "location": "Bandung"})
    b = dedup.compute_hash({"title": "Designer", "company_name": "X", "location": "Jakarta"})

    assert a != b


def test_dedup_hash_field_separator() -> None:
    """Pemisah antar-field mencegah tabrakan "AB|C" dengan "A|BC"."""
    a = dedup.compute_hash({"title": "AB", "company_name": "C"})
    b = dedup.compute_hash({"title": "A", "company_name": "BC"})

    assert a != b


def test_duplicate_flag_not_filtered_by_source() -> None:
    """Duplikat dikenali walau dari sumber yang sama.

    Remotive terbukti memuat lowongan kembar: dua ID berbeda, judul dan
    perusahaan identik ("Content Reviewer - United States" 2091166 dan 2091177).
    Menyaring per sumber akan meloloskan duplikat semacam itu, jadi pencarian
    hanya menyaring ``source_url`` yang sama.
    """
    pertama = {"title": "Content Reviewer", "company_name": "TELUS Digital",
               "source_url": "https://remotive.com/a-2091166", "source_id": 3}
    kembar = {"title": "Content Reviewer", "company_name": "TELUS Digital",
              "source_url": "https://remotive.com/a-2091177", "source_id": 3}
    lintas = {"title": "Content Reviewer", "company_name": "TELUS Digital",
              "source_url": "https://kalibrr.com/a", "source_id": 2}

    assert dedup.is_duplicate(pertama, kembar), "kembar satu sumber tetap duplikat"
    assert dedup.is_duplicate(pertama, lintas), "lintas sumber juga duplikat"
    assert not dedup.is_duplicate(pertama, {**pertama, "title": "Data Engineer"})
    assert not dedup.is_duplicate(pertama, pertama), "baris yang sama bukan duplikat"


def test_group_by_hash() -> None:
    """Pengelompokan mengembalikan semua baris, tanpa menghapus apa pun."""
    jobs = [
        {"title": "Designer", "company_name": "X", "location": "Bandung"},
        {"title": "designer", "company_name": "x", "location": "bandung"},
        {"title": "Engineer", "company_name": "Y"},
    ]

    hasil = dedup.group_by_hash(jobs)

    assert sum(len(v) for v in hasil.values()) == 3, "tidak ada baris hilang"
    assert len(hasil) == 2, "dua hash unik"


# --- R-03-12 / R-03-13: idempoten ---------------------------------------

def test_insert_or_update_idempotent(monkeypatch) -> None:
    """Dua eksekusi tidak menambah duplikat; yang kedua memperbarui (R-03-12)."""
    from scraper.pipeline import persist

    class Tabel:
        """Tabel `jobs` tiruan: cukup untuk menguji alur upsert."""

        def __init__(self):
            self.baris: dict[str, dict] = {}
            self.berikut = 1
            self._mode = None
            self._payload = None

        def select(self, *_a, **_k):
            self._mode = "select"
            return self

        def insert(self, payload):
            self._mode = "insert"
            self._payload = payload if isinstance(payload, dict) else payload[0]
            return self

        def update(self, payload):
            self._mode = "update"
            self._payload = payload
            return self

        def eq(self, kolom, nilai):
            self._kunci = (kolom, nilai)
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self._mode == "select":
                kolom, nilai = self._kunci
                hasil = [r for r in self.baris.values() if r.get(kolom) == nilai]
                if kolom == "dedup_hash":
                    return type("R", (), {"data": hasil})()
                return type("R", (), {"data": hasil[:1]})()

            if self._mode == "insert":
                payload = dict(self._payload)
                payload["id"] = self.berikut
                self.berikut += 1
                self.baris[payload["source_url"]] = payload
                return type("R", (), {"data": [payload]})()

            kolom, nilai = self._kunci
            for r in self.baris.values():
                if r.get(kolom) == nilai:
                    r.update(self._payload)
            return type("R", (), {"data": []})()

    tabel = Tabel()
    monkeypatch.setattr(persist.core_db, "get_db",
                        lambda: type("DB", (), {"table": staticmethod(lambda _n: tabel)})())

    baris = normalize.normalize(_job(title="Backend Engineer", source_id=1))
    baris["dedup_hash"] = dedup.compute_hash(baris)

    assert persist.upsert(baris) == "inserted"
    assert persist.upsert(baris) == "updated", "eksekusi kedua memperbarui"
    assert len(tabel.baris) == 1, "tidak ada baris baru"

    # Perubahan isi ikut tersimpan.
    baru = {**baris, "title": "Backend Engineer (Python)"}
    assert persist.upsert(baru) == "updated"
    assert tabel.baris[baris["source_url"]]["title"] == "Backend Engineer (Python)"


def test_update_never_changes_identity(monkeypatch) -> None:
    """Pembaruan tidak boleh mengubah ``source_url`` atau ``source_id``.

    Mengubah keduanya berarti membuat baris baru secara diam-diam.
    """
    assert "source_url" not in FIELD_DIPERBARUI
    assert "source_id" not in FIELD_DIPERBARUI


def test_insert_many_counts_per_outcome(monkeypatch) -> None:
    """`insert_many` mengembalikan hitungan per hasil, bukan satu angka."""
    from scraper.pipeline import persist

    class Tabel:
        """Tabel `jobs` tiruan: cukup untuk menguji hitungan `insert_many`."""

        def __init__(self):
            self.urls: set[str] = set()
            self._mode = None

        def select(self, *_a, **_k):
            self._mode = "select"
            return self

        def insert(self, payload):
            self._mode = "insert"
            self._payload = payload
            return self

        def update(self, payload):
            self._mode = "update"
            self._payload = payload
            return self

        def eq(self, kolom, nilai):
            self._kunci = nilai
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self._mode == "select":
                ada = self._kunci in self.urls
                return type("R", (), {"data": [{"id": 1, "source_url": self._kunci}] if ada else []})()
            if self._mode == "update":
                return type("R", (), {"data": []})()
            self.urls.add(self._payload["source_url"])
            return type("R", (), {"data": []})()

    tabel = Tabel()
    monkeypatch.setattr(persist.core_db, "get_db",
                        lambda: type("DB", (), {"table": staticmethod(lambda _n: tabel)})())

    a = {**_job(title="A"), "source_url": "https://contoh.test/a"}
    b = {**_job(title="B"), "source_url": "https://contoh.test/b"}

    pertama = persist.insert_many([a, b, a])
    assert pertama == {"inserted": 2, "updated": 0, "duplicate": 0}

    kedua = persist.insert_many([a, b])
    assert kedua["inserted"] == 0
    assert kedua["updated"] == 2


# --- R-03-14: tanpa layanan eksternal -----------------------------------

def test_normalize_is_pure() -> None:
    """Normalisasi tidak memanggil jaringan, database, atau AI (R-03-14).

    Diperiksa dari sumber modul: tidak ada impor klien HTTP, Supabase, maupun
    pustaka AI. Aturan ini mudah luntur tanpa penjaga.
    """
    import inspect

    sumber = inspect.getsource(normalize)
    for dilarang in ("requests", "httpx", "supabase", "openai", "deepseek", "anthropic"):
        assert dilarang not in sumber, f"normalize.py mengimpor {dilarang}"
