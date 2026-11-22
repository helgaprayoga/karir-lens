"""PRD-07 §7.1: route CV, konfirmasi skill, dan rekomendasi.

Memakai klien database tiruan supaya alur route dapat diuji tanpa Supabase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app
from tests.fixtures.cv.buat_cv import buat_docx, buat_pdf


# --- Klien database tiruan ---------------------------------------------

class Hasil:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class Query:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama
        self._pred = []
        self._mode = None
        self._payload = None
        self._limit = None

    def select(self, *_a, count=None):
        self._mode = "select"
        self._count = count == "exact"
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload if isinstance(payload, list) else [payload]
        return self

    def upsert(self, payload, **k):
        self._mode = "insert"
        self._payload = payload if isinstance(payload, list) else [payload]
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def eq(self, kolom, nilai):
        self._pred.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def in_(self, kolom, nilai):
        d = list(nilai)
        self._pred.append(lambda r, k=kolom, v=d: r.get(k) in v)
        return self

    def neq(self, kolom, nilai):
        self._pred.append(lambda r, k=kolom, v=nilai: r.get(k) != v)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        tabel = self._db.tabel(self._nama)
        if self._mode == "select":
            baris = [r for r in tabel if all(p(r) for p in self._pred)]
            if self._limit:
                baris = baris[: self._limit]
            return Hasil(baris, len(baris))
        if self._mode == "insert":
            for p in self._payload:
                if self._nama == "user_skills":
                    kunci = (p["user_id"], p["skill"])
                    if any((r["user_id"], r["skill"]) == kunci for r in tabel):
                        continue
                b = dict(p)
                b.setdefault("id", self._db.berikut(self._nama))
                b.setdefault("is_confirmed", True)
                b.setdefault("created_at", "2026-11-01T00:00:00+00:00")
                tabel.append(b)
            return Hasil()
        if self._mode == "update":
            for r in tabel:
                if all(p(r) for p in self._pred):
                    r.update(self._payload)
            return Hasil()
        if self._mode == "delete":
            tabel[:] = [r for r in tabel if not all(p(r) for p in self._pred)]
            return Hasil()
        return Hasil()


class Tabel:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama

    def select(self, *a, **k):
        return Query(self._db, self._nama).select(*a, **k)

    def insert(self, p):
        return Query(self._db, self._nama).insert(p)

    def upsert(self, p, **k):
        return Query(self._db, self._nama).upsert(p, **k)

    def update(self, p):
        return Query(self._db, self._nama).update(p)

    def delete(self):
        return Query(self._db, self._nama).delete()


class DB:
    def __init__(self, jobs):
        self._t = {
            "jobs": jobs,
            "users": [{"id": 1, "email": "a@contoh.test", "name": "Andi",
                       "role": "user", "created_at": "2026-10-01T00:00:00+00:00"}],
            "user_skills": [],
            "saved_jobs": [],
            "sources": [{"id": 1, "name": "dealls"}],
        }
        self._n = 0

    def tabel(self, nama):
        return self._t.setdefault(nama, [])

    def berikut(self, _nama):
        self._n += 1
        return self._n

    def table(self, nama):
        return Tabel(self, nama)


def _job(i, skills, cluster_id=1, posted="2026-11-01T00:00:00+00:00"):
    return {
        "id": i, "title": f"Job {i}", "company_name": "NovaTech",
        "company_slug": "novatech", "location": "Jakarta",
        "employment_type": "full-time", "description": "Deskripsi.",
        "skills": skills, "skills_source": "declared",
        "salary_min": None, "salary_max": None, "salary_currency": None,
        "salary_period": None, "source_id": 1,
        "source_url": f"https://dealls.com/{i}", "posted_at": posted,
        "cluster_id": cluster_id,
    }


@pytest.fixture
def db(monkeypatch):
    dari = DB([
        _job(1, ["python", "sql", "airflow"]),
        _job(2, ["python", "docker"]),
        _job(3, ["figma", "sketch"]),
    ])

    from core import db as core_db
    from app.cv import repository as cv_repo
    from app.profile import repository as profile_repo
    from app.auth import repository as auth_repo

    monkeypatch.setattr(core_db, "get_db", lambda: dari)
    monkeypatch.setattr(cv_repo, "_client", lambda: dari)
    monkeypatch.setattr(profile_repo, "_client", lambda: dari)
    monkeypatch.setattr(auth_repo.db, "get_db", lambda: dari)
    return dari


def _app():
    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def _login(client, uid=1):
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


@pytest.fixture(scope="module")
def pdf(tmp_path_factory) -> Path:
    return buat_pdf(tmp_path_factory.mktemp("cv") / "cv.pdf")


@pytest.fixture(scope="module")
def docx(tmp_path_factory) -> Path:
    return buat_docx(tmp_path_factory.mktemp("cv") / "cv.docx")


# --- Bug: hasil ekstraksi hilang setelah unggah -------------------------

def test_extracted_skills_shown_after_upload(db, pdf) -> None:
    """Kandidat muncul di `/cv` setelah unggahan.

    Sebelum perbaikan, JavaScript memanggil `location.reload()` setelah
    ekstraksi dan hasilnya **dibuang**: halaman dimuat ulang tanpa kandidat,
    sehingga pengguna yang baru mengunggah CV hanya melihat "belum ada skill".
    Endpoint sekarang menyimpan kandidat di sesi.
    """
    client = _app().test_client()
    _login(client)

    with pdf.open("rb") as f:
        r = client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})
    assert r.status_code == 200

    body = client.get("/cv").get_data(as_text=True)

    assert "Skill terdeteksi" in body, "panel konfirmasi tidak muncul"
    assert 'data-skill-choices' in body
    assert "python" in body
    assert "Simpan skill terpilih" in body


def test_session_holds_only_skill_names(db, pdf) -> None:
    """Sesi menyimpan nama skill saja, bukan teks CV.

    Batas privasi PRD-07 R-07-08: CV tidak disimpan. Cookie sesi ikut aturan
    yang sama — menyimpan teks CV di sana akan sama-sama pelanggaran.
    """
    client = _app().test_client()
    _login(client)

    with pdf.open("rb") as f:
        client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})

    with client.session_transaction() as sesi:
        tersimpan = sesi.get("cv_suggestions") or {}

    assert set(tersimpan) == {"skills", "ambiguous"}
    teks = repr(tersimpan)
    assert "Budi" not in teks
    assert "Backend Engineer" not in teks
    assert "PostgreSQL" not in teks


def test_suggestions_cleared_after_confirm(db, pdf) -> None:
    """Setelah dikonfirmasi, panel kandidat tidak muncul lagi."""
    client = _app().test_client()
    _login(client)

    with pdf.open("rb") as f:
        client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})
    client.post("/cv/confirm", data={"skills": ["python"]})

    body = client.get("/cv").get_data(as_text=True)
    assert "Skill terdeteksi" not in body


def test_extract_failure_keeps_previous_suggestions(db, pdf) -> None:
    """Unggahan gagal tidak menghapus kandidat yang sudah ada.

    Bila pengguna mengunggah berkas yang salah setelah unggahan berhasil,
    kandidat sebelumnya tetap dapat dikonfirmasi — kehilangan keduanya karena
    satu kesalahan berkas akan menjengkelkan.
    """
    client = _app().test_client()
    _login(client)

    with pdf.open("rb") as f:
        client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})

    import io

    client.post(
        "/api/cv/extract",
        data={"file": (io.BytesIO(b"x"), "cv.txt")},
        content_type="multipart/form-data",
    )

    body = client.get("/cv").get_data(as_text=True)
    assert "Skill terdeteksi" in body
    assert "python" in body


# --- R-07-12: login -----------------------------------------------------

def test_cv_requires_login(db) -> None:
    """Tamu diarahkan ke login, bukan melihat halaman CV."""
    client = _app().test_client()
    for path in ("/cv", "/cv/"):
        r = client.get(path)
        assert r.status_code in (302, 308)
    r = client.get("/cv")
    assert "/auth/login" in r.headers["Location"]


def test_recommendation_requires_login(db) -> None:
    """Route rekomendasi menolak pengunjung (R-07-12)."""
    client = _app().test_client()
    r = client.get("/api/cv/recommendations")

    assert r.status_code == 302
    assert "/auth/login" in r.headers["Location"]


def test_extract_requires_login(db, pdf) -> None:
    """Ekstraksi juga butuh login: rekomendasi terikat ke akun."""
    client = _app().test_client()
    with pdf.open("rb") as f:
        r = client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})

    assert r.status_code == 302


# --- Ekstraksi lewat API ------------------------------------------------

def test_extract_api_contract(db, pdf) -> None:
    """`POST /api/cv/extract` memenuhi kontrak PRD-F04 §4.1."""
    client = _app().test_client()
    _login(client)

    with pdf.open("rb") as f:
        r = client.post("/api/cv/extract", data={"file": (f, "cv.pdf")})

    assert r.status_code == 200
    isi = r.get_json()
    assert set(isi) == {"data"}
    assert set(isi["data"]) == {"skills", "ambiguous"}
    assert "python" in isi["data"]["skills"]


def test_extract_api_rejects_wrong_type(db) -> None:
    """Tipe salah menghasilkan galat JSON yang ramah, bukan 500."""
    client = _app().test_client()
    _login(client)

    import io

    r = client.post(
        "/api/cv/extract",
        data={"file": (io.BytesIO(b"halo"), "cv.txt")},
        content_type="multipart/form-data",
    )

    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


# --- R-07-06 / R-07-07: konfirmasi -------------------------------------

def test_only_confirmed_skills_saved(db) -> None:
    """Hanya skill yang dicentang yang tersimpan (R-07-07)."""
    client = _app().test_client()
    _login(client)

    client.post("/cv/confirm", data={"skills": ["python"]})

    baris = db.tabel("user_skills")
    assert [b["skill"] for b in baris] == ["python"]
    assert baris[0]["source"] == "cv"


def test_confirm_requires_selection(db) -> None:
    """Tanpa pilihan, tidak ada yang tersimpan dan tidak ada baris kosong."""
    client = _app().test_client()
    _login(client)

    r = client.post("/cv/confirm", data={})

    assert r.status_code == 302
    assert db.tabel("user_skills") == []


def test_remove_skill(db) -> None:
    """Pengguna dapat menghapus skill terkonfirmasi (R-07-15)."""
    client = _app().test_client()
    _login(client)
    client.post("/cv/confirm", data={"skills": ["python", "sql"]})
    skill_id = db.tabel("user_skills")[0]["id"]

    client.post(f"/cv/skills/{skill_id}/remove")

    assert len(db.tabel("user_skills")) == 1


# --- Rekomendasi --------------------------------------------------------

def test_recommendations_need_skills(db) -> None:
    """Tanpa skill terkonfirmasi, halaman meminta pengguna menambahkan skill (R-07-13)."""
    client = _app().test_client()
    _login(client)

    body = client.get("/cv").get_data(as_text=True)
    assert "Belum ada skill terkonfirmasi" in body


def test_recommendations_rendered(db) -> None:
    """Dengan skill terkonfirmasi, rekomendasi muncul beserta skornya."""
    client = _app().test_client()
    _login(client)
    client.post("/cv/confirm", data={"skills": ["python"]})

    body = client.get("/cv").get_data(as_text=True)

    assert "Rekomendasi" in body
    assert 'class="job-card"' in body
    assert "cocok" in body.lower()


def test_recommendations_api(db) -> None:
    """API rekomendasi mengembalikan skill dan kartu ber-skor."""
    client = _app().test_client()
    _login(client)
    client.post("/cv/confirm", data={"skills": ["python"]})

    isi = client.get("/api/cv/recommendations").get_json()
    data = isi["data"]

    assert data["skills"] == ["python"]
    assert data["recommendations"]
    for job in data["recommendations"]:
        assert "score" in job["match"]
        assert "reasons" in job["match"]
        assert job["source_url"].startswith("http")


def test_recommendation_has_source_url(db) -> None:
    """Setiap rekomendasi punya tautan sumber asli (§5)."""
    client = _app().test_client()
    _login(client)
    client.post("/cv/confirm", data={"skills": ["python"]})

    isi = client.get("/api/cv/recommendations").get_json()
    for job in isi["data"]["recommendations"]:
        assert job["source_url"].startswith("http")


# --- R-07-08: CSRF ------------------------------------------------------

def test_csrf_on_confirm(monkeypatch) -> None:
    """POST konfirmasi dilindungi CSRF."""
    dari = DB([_job(1, ["python"])])

    from core import db as core_db
    from app.cv import repository as cv_repo
    from app.profile import repository as profile_repo
    from app.auth import repository as auth_repo

    monkeypatch.setattr(core_db, "get_db", lambda: dari)
    monkeypatch.setattr(cv_repo, "_client", lambda: dari)
    monkeypatch.setattr(profile_repo, "_client", lambda: dari)
    monkeypatch.setattr(auth_repo.db, "get_db", lambda: dari)

    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    client = app.test_client()
    _login(client)

    r = client.post("/cv/confirm", data={"skills": ["python"]})

    assert r.status_code == 400
    assert dari.tabel("user_skills") == []
