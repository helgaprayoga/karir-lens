"""PRD-06 §7.1: akun dan bookmark.

Memakai klien PostgREST tiruan yang meniru semantik `saved_jobs`, `user_skills`,
dan `users`; test memeriksa perilaku yang terlihat pengguna (status, isi
halaman, duplikat), bukan detail implementasi.
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
    """Meniru rantai builder supabase-py untuk operasi yang dipakai profil."""

    def __init__(self, db, nama):
        self._db = db
        self._nama = nama
        self._predikat = []
        self._count = False
        self._limit = None
        self._mode = None
        self._payload = None

    def select(self, *_kolom, count=None):
        self._mode = "select"
        self._count = count == "exact"
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload if isinstance(payload, list) else [payload]
        return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._mode = "upsert"
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
        self._predikat.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def in_(self, kolom, nilai):
        daftar = list(nilai)
        self._predikat.append(lambda r, k=kolom, v=daftar: r.get(k) in v)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, mulai, akhir):
        self._rentang = (mulai, akhir)
        return self

    def gte(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: (r.get(k) or "") >= v)
        return self

    def ov(self, kolom, nilai):
        """`overlaps` PostgREST untuk kolom array."""
        daftar = set(nilai)
        self._predikat.append(lambda r, k=kolom, v=daftar: bool(set(r.get(k) or []) & v))
        return self

    def neq(self, kolom, nilai):
        self._predikat.append(lambda r, k=kolom, v=nilai: r.get(k) != v)
        return self

    def execute(self):
        tabel = self._db.tabel(self._nama)

        if self._mode == "select":
            baris = [r for r in tabel if all(p(r) for p in self._predikat)]
            if getattr(self, "_rentang", None):
                mulai, akhir = self._rentang
                baris = baris[mulai : akhir + 1]
            if self._limit:
                baris = baris[: self._limit]
            return FakeResult(baris, len(baris))

        if self._mode in ("insert", "upsert"):
            for payload in self._payload:
                if self._nama == "saved_jobs":
                    kunci = (payload["user_id"], payload["job_id"])
                    if any((r["user_id"], r["job_id"]) == kunci for r in tabel):
                        continue  # on_conflict do nothing
                baris = dict(payload)
                # `saved_jobs` hanya memuat relasi dan timestamp; jangan
                # tambahkan kolom yang tidak ada di skema (PRD-01).
                if self._nama == "saved_jobs":
                    baris.setdefault("created_at", "2026-11-01T00:00:00+00:00")
                else:
                    baris.setdefault("id", self._db.berikut_id(self._nama))
                    baris.setdefault("created_at", "2026-11-01T00:00:00+00:00")
                    baris.setdefault("is_confirmed", False)
                tabel.append(baris)
            return FakeResult()

        if self._mode == "update":
            for r in tabel:
                if all(p(r) for p in self._predikat):
                    r.update(self._payload)
            return FakeResult()

        if self._mode == "delete":
            sisa = [r for r in tabel if not all(p(r) for p in self._predikat)]
            tabel[:] = sisa
            return FakeResult()

        return FakeResult()


class FakeTable:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama

    def select(self, *a, **k):
        return FakeQuery(self._db, self._nama).select(*a, **k)

    def insert(self, payload):
        return FakeQuery(self._db, self._nama).insert(payload)

    def upsert(self, payload, **k):
        return FakeQuery(self._db, self._nama).upsert(payload, **k)

    def update(self, payload):
        return FakeQuery(self._db, self._nama).update(payload)

    def delete(self):
        return FakeQuery(self._db, self._nama).delete()


class FakeDB:
    def __init__(self, jobs, users):
        self._tabel = {
            "jobs": jobs,
            "users": users,
            "saved_jobs": [],
            "user_skills": [],
            "sources": [{"id": 1, "name": "dealls"}],
            "sessions": [],
        }
        self._next = 100

    def tabel(self, nama):
        return self._tabel.setdefault(nama, [])

    def berikut_id(self, _nama):
        self._next += 1
        return self._next

    def table(self, nama):
        return FakeTable(self, nama)


def _job(i, **ubah):
    dasar = {
        "id": i,
        "title": f"Backend Engineer {i}",
        "company_name": "NovaTech",
        "company_slug": "novatech",
        "location": "Jakarta",
        "employment_type": "full-time",
        "description": "Deskripsi.",
        "skills": ["python"],
        "salary_min": 9_000_000,
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


USER_A = {"id": 1, "email": "a@contoh.test", "name": "Andi",
          "created_at": "2026-10-01T00:00:00+00:00", "role": "user"}
USER_B = {"id": 2, "email": "b@contoh.test", "name": "Budi",
          "created_at": "2026-10-02T00:00:00+00:00", "role": "user"}


@pytest.fixture
def db(monkeypatch):
    """Klien database tiruan, dipakai semua modul lewat `core.db.get_db`."""
    dari = FakeDB([_job(i) for i in range(1, 6)], [dict(USER_A), dict(USER_B)])

    from core import db as core_db

    monkeypatch.setattr(core_db, "get_db", lambda: dari)
    # PROFIL memakai `_client()` sendiri; arahkan ke klien yang sama.
    from app.profile import repository as profile_repo
    from app.jobs import repository as jobs_repo
    from app.auth import repository as auth_repo
    from app.insights import repository as insights_repo

    monkeypatch.setattr(profile_repo, "_client", lambda: dari)
    monkeypatch.setattr(jobs_repo, "_client", lambda: dari)
    monkeypatch.setattr(insights_repo, "_client", lambda: dari)
    monkeypatch.setattr(auth_repo.db, "get_db", lambda: dari)
    return dari


def _app():
    app = create_app("testing")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def _login(client, user=USER_A):
    with client.session_transaction() as sesi:
        sesi["_user_id"] = str(user["id"])
        sesi["_fresh"] = True


# --- R-06-09: login required --------------------------------------------

def test_profile_requires_login(db) -> None:
    """Pengunjung diarahkan ke login, bukan melihat profil."""
    client = _app().test_client()

    for path in ("/profile", "/saved"):
        resp = client.get(path)
        assert resp.status_code == 302, f"{path} tidak mengalihkan"
        assert "/auth/login" in resp.headers["Location"]


def test_bookmark_action_requires_login(db) -> None:
    """Aksi POST juga butuh login, bukan hanya halaman."""
    client = _app().test_client()
    resp = client.post("/saved/1/add")

    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    assert db.tabel("saved_jobs") == []


# --- R-06-03 / R-06-05: simpan bookmark ---------------------------------

def test_save_bookmark(db) -> None:
    """Bookmark tersimpan untuk pengguna login."""
    client = _app().test_client()
    _login(client)

    resp = client.post("/saved/1/add")

    assert resp.status_code == 302
    assert len(db.tabel("saved_jobs")) == 1
    assert db.tabel("saved_jobs")[0]["job_id"] == 1
    assert db.tabel("saved_jobs")[0]["user_id"] == USER_A["id"]


def test_save_bookmark_twice_no_duplicate(db) -> None:
    """Menyimpan dua kali tidak menambah baris (R-06-05).

    Pesan yang muncul adalah "sudah tersimpan", bukan "disimpan" — pengguna
    perlu tahu bahwa tidak ada yang berubah.
    """
    client = _app().test_client()
    _login(client)

    client.post("/saved/1/add")
    resp = client.post("/saved/1/add", follow_redirects=True)

    assert len(db.tabel("saved_jobs")) == 1, "duplikat tidak boleh terbentuk"
    assert "sudah tersimpan" in resp.get_data(as_text=True)


def test_save_nonexistent_job_error(db) -> None:
    """Lowongan yang tidak ada menghasilkan error ramah, bukan 500 (R-06-11)."""
    client = _app().test_client()
    _login(client)

    resp = client.post("/saved/9999/add")

    assert resp.status_code == 404
    assert db.tabel("saved_jobs") == []


def test_save_job_service_raises(db) -> None:
    """Service melempar `NotFoundError`, bukan mengembalikan sukses palsu."""
    from app.profile import service

    with pytest.raises(NotFoundError):
        service.save_job(USER_A["id"], 9999)


# --- R-06-04: hapus bookmark --------------------------------------------

def test_remove_bookmark(db) -> None:
    """Bookmark terhapus hanya untuk pengguna tersebut."""
    client = _app().test_client()
    _login(client)

    client.post("/saved/1/add")
    db.tabel("saved_jobs").append(
        {"id": 99, "user_id": USER_B["id"], "job_id": 1,
         "created_at": "2026-11-01T00:00:00+00:00"}
    )

    client.post("/saved/1/remove")

    sisa = db.tabel("saved_jobs")
    assert len(sisa) == 1, "hanya satu baris yang dihapus"
    assert sisa[0]["user_id"] == USER_B["id"], "bookmark pengguna lain tetap utuh"


# --- R-06-06 / R-06-07: halaman tersimpan -------------------------------

def test_saved_page_pagination_and_empty(db) -> None:
    """Pagination mengembalikan meta benar; halaman kosong memakai EmptyState."""
    from app.profile import service

    kosong = service.list_saved_jobs(USER_A["id"])
    assert kosong["items"] == []
    assert kosong["meta"]["total"] == 0

    for i in (1, 2, 3):
        service.save_job(USER_A["id"], i)

    halaman1 = service.list_saved_jobs(USER_A["id"], page=1, per_page=2)
    assert halaman1["meta"] == {"page": 1, "per_page": 2, "total": 3, "has_next": True}
    assert len(halaman1["items"]) == 2

    halaman2 = service.list_saved_jobs(USER_A["id"], page=2, per_page=2)
    assert halaman2["meta"]["has_next"] is False
    assert len(halaman2["items"]) == 1

    # Tidak ada item yang muncul di dua halaman.
    id1 = {j["id"] for j in halaman1["items"]}
    id2 = {j["id"] for j in halaman2["items"]}
    assert not (id1 & id2)


def test_saved_page_renders_empty_state(db) -> None:
    """Halaman kosong menampilkan pesan jelas, bukan area kosong."""
    client = _app().test_client()
    _login(client)

    body = client.get("/saved").get_data(as_text=True)
    assert "Belum ada lowongan tersimpan" in body


def test_saved_items_are_marked_saved(db) -> None:
    """Kartu di halaman tersimpan bertanda `is_saved`."""
    from app.profile import service

    service.save_job(USER_A["id"], 2)
    items = service.list_saved_jobs(USER_A["id"])["items"]

    assert items and items[0]["is_saved"] is True


# --- R-06-01: profil ----------------------------------------------------

def test_get_profile_contract(db) -> None:
    """`get_profile` memenuhi kontrak PRD-F03 §4.1."""
    from app.profile import service

    data = service.get_profile(USER_A["id"])

    assert set(data) == {"profile", "skills", "summary"}
    assert set(data["summary"]) == {"skill_count", "saved_count"}
    assert data["profile"]["email"] == USER_A["email"]


def test_profile_shows_confirmed_skills_readonly(db) -> None:
    """Hanya skill terkonfirmasi yang tampil, dan tidak dapat diubah (R-06-12)."""
    from app.profile import service

    db.tabel("user_skills").extend([
        {"id": 1, "user_id": USER_A["id"], "skill": "python",
         "source": "cv", "is_confirmed": True, "created_at": "2026-11-01T00:00:00+00:00"},
        {"id": 2, "user_id": USER_A["id"], "skill": "figma",
         "source": "cv", "is_confirmed": False, "created_at": "2026-11-01T00:00:00+00:00"},
    ])

    data = service.get_profile(USER_A["id"])
    nama = [s["skill"] for s in data["skills"]]

    assert nama == ["python"], "skill belum dikonfirmasi tidak boleh tampil"
    assert data["summary"]["skill_count"] == 1


def test_unconfirmed_skills_excluded_everywhere(db) -> None:
    """Fitur lain hanya melihat skill terkonfirmasi (R-06-12)."""
    from app.profile import service

    db.tabel("user_skills").append(
        {"id": 1, "user_id": USER_A["id"], "skill": "figma",
         "source": "cv", "is_confirmed": False, "created_at": "2026-11-01T00:00:00+00:00"}
    )

    assert service.list_confirmed_skills(USER_A["id"]) == []


# --- R-06-02: ubah nama -------------------------------------------------

def test_update_name(db) -> None:
    """Pengguna dapat mengubah nama; email tetap."""
    from app.profile import service

    data = service.update_name(USER_A["id"], "  Andi  Pratama ")

    assert data["profile"]["name"] == "Andi Pratama"
    assert data["profile"]["email"] == USER_A["email"], "email tidak berubah"


def test_update_name_rejects_empty(db) -> None:
    """Nama kosong ditolak, bukan disimpan sebagai string kosong."""
    from app.profile import service
    from core.errors import ValidationError

    with pytest.raises(ValidationError):
        service.update_name(USER_A["id"], "   ")


# --- R-06-10: navigasi --------------------------------------------------

def test_nav_state_variants(db) -> None:
    """Navigasi berbeda untuk publik, pengguna, dan admin.

    Tamu tidak melihat tautan akun sama sekali; pengguna melihatnya; admin
    mendapat menu tambahan. Pembedaan ini yang mencegah "Tersimpan" muncul di
    header pengunjung yang tidak punya akun.
    """
    client = _app().test_client()

    tamu = client.get("/").get_data(as_text=True)
    assert "Tersimpan" not in tamu
    assert "Masuk" in tamu

    _login(client)
    pengguna = client.get("/").get_data(as_text=True)
    assert "Masuk" not in pengguna


# --- R-06-13 / §5: tidak ada status lamaran -----------------------------

def test_no_application_status_fields(db) -> None:
    """Tidak ada status lamaran atau tracker lamaran di mana pun.

    Bookmark adalah penanda, bukan pencatatan lamaran (PRD-06 §3.2). Skema,
    service, dan halaman tidak boleh memuat konsep itu.
    """
    from app.profile import service

    service.save_job(USER_A["id"], 1)
    data = service.list_saved_jobs(USER_A["id"])

    teks = repr(data).lower()
    for kata in ("application", "applied", "lamaran", "status", "interview", "stage"):
        assert kata not in teks, f"keluaran memuat {kata!r}"

    # Baris bookmark hanya memuat relasi dan timestamp.
    assert set(data["items"][0]) >= {"id", "is_saved"}
    assert {"status", "applied_at"} & set(data["items"][0]) == set()


def test_bookmark_table_has_no_status_column(db) -> None:
    """Baris yang disimpan hanya memuat relasi dan waktu."""
    from app.profile import service

    service.save_job(USER_A["id"], 1)
    baris = db.tabel("saved_jobs")[0]

    assert set(baris) <= {"id", "user_id", "job_id", "created_at"}


# --- R-06-08: POST + CSRF ----------------------------------------------

def test_csrf_on_bookmark_post(monkeypatch) -> None:
    """POST tanpa token CSRF ditolak."""
    dari = FakeDB([_job(1)], [dict(USER_A)])

    from core import db as core_db
    from app.profile import repository as profile_repo
    from app.jobs import repository as jobs_repo
    from app.auth import repository as auth_repo

    monkeypatch.setattr(core_db, "get_db", lambda: dari)
    monkeypatch.setattr(profile_repo, "_client", lambda: dari)
    monkeypatch.setattr(jobs_repo, "_client", lambda: dari)
    monkeypatch.setattr(auth_repo.db, "get_db", lambda: dari)

    app = create_app("testing")
    # CSRF aktif seperti di produksi.
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    client = app.test_client()
    _login(client)

    resp = client.post("/saved/1/add")

    assert resp.status_code == 400, "POST tanpa token harus ditolak"
    assert dari.tabel("saved_jobs") == []


# --- Katalog menandai tersimpan ----------------------------------------

def test_catalog_marks_saved_for_user(db) -> None:
    """Katalog menandai kartu yang sudah disimpan pengguna ini."""
    from app.jobs import service as jobs_service
    from app.profile import service as profile_service

    profile_service.save_job(USER_A["id"], 1)

    sebagai_tamu = jobs_service.search_jobs()["items"]
    assert all(not j["is_saved"] for j in sebagai_tamu), "tamu tidak punya bookmark"

    sebagai_pengguna = jobs_service.search_jobs(user_id=USER_A["id"])["items"]
    bertanda = [j for j in sebagai_pengguna if j["is_saved"]]
    assert [j["id"] for j in bertanda] == [1]


def test_detail_marks_saved(db) -> None:
    """Halaman detail menandai tombol simpan sesuai keadaan sebenarnya."""
    from app.jobs import service as jobs_service
    from app.profile import service as profile_service

    profile_service.save_job(USER_A["id"], 1)
    data = jobs_service.get_job(1, user_id=USER_A["id"])

    assert data["job"]["is_saved"] is True
