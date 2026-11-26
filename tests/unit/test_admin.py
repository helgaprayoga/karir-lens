"""PRD-09 §7.1: panel admin dan REST API.

Semua test memakai klien database tiruan — tidak ada panggilan jaringan.
Yang diuji adalah akses berbasis peran, bentuk respons JSON, dan janji bahwa
API memakai service yang sama dengan halaman web.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.config import CONFIG_MAP
from app.admin import repository as admin_repo


# --- tiruan database -----------------------------------------------------

class Hasil:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class Query:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama
        self._pred = []
        self._mode = "select"
        self._limit = None
        self._rentang = None

    def select(self, *a, count=None):
        self._mode = "select"
        self._count = count == "exact"
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._mode = "insert"
        self._payload = payload
        return self

    def eq(self, kolom, nilai):
        self._pred.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def ov(self, *_a, **_k):
        """Operator PostgREST lain (overlap array) tidak memengaruhi test ini."""
        return self

    def in_(self, *_a, **_k):
        return self

    def is_(self, *_a, **_k):
        return self

    def __getattr__(self, nama):
        # Operator PostgREST lain (neq, gte, lte, ...) tidak memengaruhi test
        # panel admin; mengembalikan self membuat rantainya tetap jalan.
        if nama.startswith("_"):
            raise AttributeError(nama)

        def apa_saja(*_a, **_k):
            return self

        return apa_saja

    def or_(self, ekspresi):
        import re as _re

        klausa = _re.findall(r"(\w+)\.ilike\.%([^%]*)%", ekspresi)

        def cocok(row):
            return any(p.lower() in str(row.get(k) or "").lower() for k, p in klausa)

        self._pred.append(cocok)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, mulai, akhir):
        self._rentang = (mulai, akhir)
        return self

    def execute(self):
        tabel = self._db.tabel(self._nama)
        if self._mode == "insert":
            tabel.append(dict(self._payload))
            return Hasil()
        if self._mode == "delete":
            sisa = [r for r in tabel if not all(p(r) for p in self._pred)]
            tabel[:] = sisa
            return Hasil()
        baris = [r for r in tabel if all(p(r) for p in self._pred)]
        total = len(baris)
        if self._rentang:
            mulai, akhir = self._rentang
            baris = baris[mulai : akhir + 1]
        if self._limit:
            baris = baris[: self._limit]
        return Hasil(baris, total)


class Tabel:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama

    def select(self, *a, **k):
        return Query(self._db, self._nama).select(*a, **k)

    def delete(self):
        return Query(self._db, self._nama).delete()

    def upsert(self, *a, **k):
        return Query(self._db, self._nama).upsert(*a, **k)


class DB:
    def __init__(self, jobs=None, users=None, runs=None, clusters=None):
        self._t = {
            "jobs": jobs or [],
            "users": users or [],
            "scrape_runs": runs or [],
            "clusters": clusters or [],
            "sources": [{"id": 1, "name": "dealls"}],
            "saved_jobs": [],
            "user_skills": [],
        }

    def tabel(self, nama):
        return self._t.setdefault(nama, [])

    def table(self, nama):
        return Tabel(self, nama)


def _job(i, **ubah):
    dasar = {
        "id": i,
        "title": f"Backend Engineer {i}",
        "company_name": "Northwind",
        "location": "Jakarta",
        "posted_at": "2026-11-01T00:00:00+00:00",
        "source_id": 1,
    }
    dasar.update(ubah)
    return dasar


def _user(i, role="user", **ubah):
    dasar = {
        "id": i,
        "email": f"u{i}@contoh.test",
        "name": f"Uji {i}",
        "role": role,
        "created_at": "2026-10-01T00:00:00+00:00",
    }
    dasar.update(ubah)
    return dasar


@pytest.fixture
def db(monkeypatch):
    dari = DB(
        jobs=[_job(i) for i in range(1, 4)],
        users=[_user(1, "admin"), _user(2)],
        runs=[
            {
                "id": 1,
                "source_id": 1,
                "started_at": "2026-11-20T00:30:00+00:00",
                "finished_at": "2026-11-20T00:35:00+00:00",
                "status": "success",
                "jobs_found": 363,
                "jobs_inserted": 12,
                "jobs_updated": 5,
                "error_message": None,
            }
        ],
        clusters=[{"id": 1, "label": "Data & Ai", "keywords": ["data"], "job_count": 3}],
    )
    monkeypatch.setattr(admin_repo, "_client", lambda: dari)
    return dari


def _app():
    CONFIG_MAP["prd09"] = type(
        "Prd09", (CONFIG_MAP["testing"],), {"WTF_CSRF_ENABLED": False}
    )
    app = create_app("prd09")
    app.config.update(TESTING=True)
    return app


def _login(c, uid=1):
    with c.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


@pytest.fixture
def auth(monkeypatch):
    """Pengguna login yang dapat dipilih perannya."""

    def pasang(db, role="admin"):
        from app.auth import repository as auth_repo

        monkeypatch.setattr(
            auth_repo,
            "find_by_id",
            lambda uid: {"id": uid, "email": "u@contoh.test", "name": "Uji",
                         "role": role, "created_at": "2026-10-01T00:00:00+00:00"},
        )
        return db

    return pasang


# --- R-09-01: akses berbasis peran ---------------------------------------

def test_admin_requires_role(db, auth) -> None:
    """Pengguna biasa ditolak dari /admin* (R-09-01)."""
    auth(db, role="user")
    c = _app().test_client()
    _login(c)

    for path in ("/admin", "/admin/jobs", "/admin/users", "/admin/runs", "/admin/clusters"):
        assert c.get(path).status_code == 403, f"{path} seharusnya 403"


def test_guest_redirected_to_login(db, auth) -> None:
    """Tamu diarahkan ke login, bukan melihat data admin (R-09-01)."""
    c = _app().test_client()

    r = c.get("/admin")
    assert r.status_code == 302
    assert "/auth/login" in r.headers["Location"]


def test_admin_can_open_panel(db, auth) -> None:
    """Admin melihat seluruh halaman panel."""
    auth(db, role="admin")
    c = _app().test_client()
    _login(c)

    for path in ("/admin", "/admin/jobs", "/admin/users", "/admin/runs", "/admin/clusters"):
        assert c.get(path).status_code == 200, f"{path} gagal"


# --- R-09-02: ringkasan --------------------------------------------------

def test_admin_summary_counts(db, auth) -> None:
    """Ringkasan sesuai isi database uji."""
    auth(db, role="admin")
    c = _app().test_client()
    _login(c)

    body = c.get("/admin").get_data(as_text=True)
    assert "Backend Engineer" in body or "Lowongan tersimpan" in body
    assert "363" in body, "jobs_found pada proses terakhir tidak tampil"


# --- R-09-04: hapus lowongan ---------------------------------------------

def test_admin_delete_invalid_job(db, auth) -> None:
    """Lowongan terhapus dari database (R-09-04)."""
    auth(db, role="admin")
    c = _app().test_client()
    _login(c)

    r = c.post("/admin/jobs/2/delete")

    assert r.status_code == 302
    assert [j["id"] for j in db.tabel("jobs")] == [1, 3]


def test_admin_delete_missing_job_is_404(db, auth) -> None:
    """Menghapus ID yang tidak ada menghasilkan 404, bukan 500."""
    auth(db, role="admin")
    c = _app().test_client()
    _login(c)

    assert c.post("/admin/jobs/999/delete").status_code == 404


def test_delete_removes_bookmarks_first(db, auth) -> None:
    """Bookmark yang menunjuk lowongan ikut dilepas.

    `saved_jobs.job_id` tidak punya ON DELETE CASCADE; tanpa penghapusan ini
    Postgres menolak dan admin melihat 500.
    """
    auth(db, role="admin")
    db.tabel("saved_jobs").extend([{"user_id": 2, "job_id": 2}])
    c = _app().test_client()
    _login(c)

    c.post("/admin/jobs/2/delete")

    assert db.tabel("saved_jobs") == []


# --- R-09-09: tidak ada data CV ------------------------------------------

def test_admin_no_cv_access(db, auth) -> None:
    """Tidak ada route CV di panel admin, dan halaman tidak memuat teks CV."""
    jalur = {rule.rule for rule in _app().url_map.iter_rules()}
    assert not any("cv" in path for path in jalur if path.startswith("/admin"))

    auth(db, role="admin")
    db.tabel("user_skills").extend(
        [{"id": 1, "user_id": 2, "skill": "python", "is_confirmed": True}]
    )
    c = _app().test_client()
    _login(c)

    body = c.get("/admin/users").get_data(as_text=True)
    assert "python" not in body.lower(), "nama skill tidak boleh tampil di admin"
    assert "password" not in body.lower()


# --- R-09-11..R-09-13: API ------------------------------------------------

def test_api_jobs_pagination(db, monkeypatch) -> None:
    """Metadata pagination benar (R-09-12)."""
    from app.jobs import repository as jobs_repo

    monkeypatch.setattr(jobs_repo, "_client", lambda: db)

    c = _app().test_client()
    body = c.get("/api/jobs?per_page=2").get_json()

    assert set(body) == {"data", "meta"}
    assert body["meta"]["page"] == 1
    assert body["meta"]["per_page"] == 2
    assert body["meta"]["total"] == 3
    assert body["meta"]["has_next"] is True


def test_api_job_detail(db, monkeypatch) -> None:
    """Detail JSON valid; 404 memakai format galat yang sama (R-09-13)."""
    from app.jobs import repository as jobs_repo

    monkeypatch.setattr(jobs_repo, "_client", lambda: db)

    c = _app().test_client()
    assert c.get("/api/jobs/1").get_json()["data"]["title"] == "Backend Engineer 1"

    hilang = c.get("/api/jobs/999")
    assert hilang.status_code == 404
    assert hilang.get_json()["error"]["code"] == "NOT_FOUND"


def test_api_insights(db, monkeypatch) -> None:
    """Endpoint insight mengembalikan data sesuai (R-09-11)."""
    from app.insights import repository as insights_repo

    monkeypatch.setattr(insights_repo, "_client", lambda: db)

    c = _app().test_client()
    for path in ("/api/insights/categories", "/api/insights/skills", "/api/insights/salary"):
        body = c.get(path).get_json()
        assert "data" in body, f"{path} tidak mengembalikan data"


def test_api_salary_min_sample(db, monkeypatch) -> None:
    """Statistik gaji tidak muncul saat sampel < 5 (R-05-08)."""
    from app.insights import repository as insights_repo

    monkeypatch.setattr(insights_repo, "_client", lambda: db)

    body = _app().test_client().get("/api/insights/salary").get_json()
    assert body["data"]["sample_sufficient"] is False


def test_api_personal_requires_auth(db) -> None:
    """Endpoint personal menolak tanpa sesi dengan 401 (R-09-17)."""
    c = _app().test_client()

    for path in ("/api/saved-jobs", "/api/recommendations"):
        r = c.get(path)
        assert r.status_code == 401, f"{path} tidak 401"
        assert r.get_json()["error"]["code"] == "UNAUTHORIZED"

    assert c.post("/api/saved-jobs", json={"job_id": 1}).status_code == 401


def test_api_saved_jobs_crud(db, auth, monkeypatch) -> None:
    """Simpan dan hapus bookmark lewat API (R-09-11)."""
    from app.profile import repository as profile_repo

    monkeypatch.setattr(profile_repo, "_client", lambda: db)
    auth(db, role="user")

    c = _app().test_client()
    _login(c, uid=2)

    r = c.post("/api/saved-jobs", json={"job_id": 1})
    assert r.status_code == 201
    assert r.get_json()["data"]["created"] is True

    # Sekali lagi: idempoten, bukan duplikat.
    assert c.post("/api/saved-jobs", json={"job_id": 1}).status_code == 200
    assert len(db.tabel("saved_jobs")) == 1

    assert c.delete("/api/saved-jobs/1").status_code == 200
    assert db.tabel("saved_jobs") == []


def test_api_error_format(db) -> None:
    """Format galat konsisten dan tanpa detail internal (R-09-13)."""
    body = _app().test_client().get("/api/jobs/999").get_json()

    assert set(body["error"]) == {"code", "message"}
    for bocor in ("Traceback", "supabase", "psycopg"):
        assert bocor not in str(body)


def test_api_uses_same_service() -> None:
    """API memanggil service modul, bukan query sendiri (R-09-15)."""
    import inspect

    from app.api import routes as api_routes

    sumber = inspect.getsource(api_routes)
    # Tanpa satu pun impor service, endpoint harus menulis query sendiri.
    for modul in ("jobs_service", "insights_service", "profile_service", "cv_service"):
        assert modul in sumber, f"API tidak memakai {modul}"
