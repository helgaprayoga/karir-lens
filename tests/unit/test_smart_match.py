"""Pengurutan "cocokkan otomatis" pada katalog (PRD-04 + PRD-07).

Checkbox ini ada di template sejak PRD-F02, tetapi route tidak pernah membaca
parameternya — tombolnya tidak melakukan apa pun. Test di sini menjaga agar
nilainya benar-benar mengubah urutan, dan agar tamu tidak mendapat halaman
kosong karena tidak punya skill untuk dicocokkan.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP
from app.jobs import repository as jobs_repo
from app.profile import repository as profile_repo


class Hasil:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class Query:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama
        self._pred = []
        self._limit = None
        self._rentang = None

    def select(self, *a, count=None):
        return self

    def __getattr__(self, nama):
        if nama.startswith("_"):
            raise AttributeError(nama)

        def apa_saja(*_a, **_k):
            return self

        return apa_saja

    def execute(self):
        tabel = self._db.tabel(self._nama)
        baris = [r for r in tabel if all(p(r) for p in self._pred)]
        if self._rentang:
            mulai, akhir = self._rentang
            baris = baris[mulai : akhir + 1]
        if self._limit:
            baris = baris[: self._limit]
        return Hasil(baris, len(baris))


class Tabel:
    def __init__(self, db, nama):
        self._db = db
        self._nama = nama

    def select(self, *a, **k):
        return Query(self._db, self._nama).select(*a, **k)


class DB:
    def __init__(self):
        self._t = {
            "jobs": [
                {
                    "id": 1,
                    "title": "Lowongan umum",
                    "company_name": "PT A",
                    "company_slug": "pt-a",
                    "location": "Jakarta",
                    "employment_type": "full-time",
                    "description": None,
                    "skills": ["excel"],
                    "skills_source": "declared",
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "salary_period": None,
                    "source_id": 1,
                    "source_url": "https://x/1",
                    "posted_at": "2026-11-02T00:00:00+00:00",
                    "cluster_id": 2,
                },
                {
                    "id": 2,
                    "title": "Backend Python",
                    "company_name": "PT B",
                    "company_slug": "pt-b",
                    "location": "Jakarta",
                    "employment_type": "full-time",
                    "description": None,
                    # Cocok penuh dengan skill pengguna di fixture.
                    "skills": ["python", "sql", "docker", "git"],
                    "skills_source": "declared",
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "salary_period": None,
                    "source_id": 1,
                    "source_url": "https://x/2",
                    "posted_at": "2026-11-01T00:00:00+00:00",
                    "cluster_id": 1,
                },
            ],
            "sources": [{"id": 1, "name": "dealls"}],
            "clusters": [
                {"id": 1, "label": "Backend", "keywords": ["python"]},
                {"id": 2, "label": "Umum", "keywords": ["excel"]},
            ],
            "user_skills": [
                {"id": 1, "user_id": 1, "skill": s, "is_confirmed": True}
                for s in ("python", "sql", "docker", "git")
            ],
            "saved_jobs": [],
        }

    def tabel(self, nama):
        return self._t.setdefault(nama, [])

    def table(self, nama):
        return Tabel(self, nama)


@pytest.fixture
def db(monkeypatch):
    dari = DB()
    monkeypatch.setattr(jobs_repo, "_client", lambda: dari)
    monkeypatch.setattr(profile_repo, "_client", lambda: dari)
    return dari


def _app(monkeypatch):
    from app.auth import repository as auth_repo

    monkeypatch.setattr(
        auth_repo,
        "find_by_id",
        lambda uid: {"id": uid, "email": "u@contoh.test", "name": "Uji",
                     "role": "user", "created_at": "2026-10-01T00:00:00+00:00"},
    )
    CONFIG_MAP["smart_test"] = type(
        "SmartTest", (CONFIG_MAP["testing"],), {"WTF_CSRF_ENABLED": False}
    )
    app = create_app("smart_test")
    app.config.update(TESTING=True)
    return app


def _login(c, uid=1):
    with c.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_smart_reorders_by_skill_match(db, monkeypatch) -> None:
    """``smart=1`` menaruh lowongan yang cocok di atas, bukan yang terbaru.

    Tanpa ini checkbox di template hanya dekorasi: nilainya tidak pernah
    dibaca route maupun service.
    """
    from app.jobs import service

    biasa = service.search_jobs(user_id=1)
    pintar = service.search_jobs(smart="1", user_id=1)

    assert biasa["items"][0]["id"] == 1, "urutan biasa: terbaru dulu"
    assert pintar["items"][0]["id"] == 2, "urutan pintar: yang cocok dulu"
    assert pintar["filters"]["smart"] is True


def test_smart_attaches_match_score(db, monkeypatch) -> None:
    """Setiap kartu membawa skor, sehingga badge kecocokan dapat dirender."""
    from app.jobs import service

    data = service.search_jobs(smart="1", user_id=1)

    assert all("match" in job for job in data["items"])
    assert data["items"][0]["match"]["score"] > 0


def test_smart_ignored_for_guest(db, monkeypatch) -> None:
    """Tamu yang mengirim ``smart=1`` tetap melihat lowongan, bukan halaman kosong."""
    from app.jobs import service

    data = service.search_jobs(smart="1", user_id=None)

    assert len(data["items"]) == 2
    assert data["filters"]["smart"] is False


def test_smart_ignored_without_skills(db, monkeypatch) -> None:
    """Pengguna tanpa skill terkonfirmasi tidak mendapat urutan kosong."""
    from app.jobs import service

    db.tabel("user_skills")[:] = []
    data = service.search_jobs(smart="1", user_id=1)

    assert len(data["items"]) == 2
    assert data["filters"]["smart"] is False


def test_smart_checkbox_stays_checked(db, monkeypatch) -> None:
    """Setelah halaman dimuat ulang, kotak centangnya tetap tercentang.

    Tanpa ini pengguna menekan "Terapkan" dan tidak tahu apakah pilihannya
    tersimpan — dan menekan sekali lagi akan mematikannya tanpa sengaja.
    """
    app = _app(monkeypatch)
    c = app.test_client()
    _login(c)

    body = c.get("/jobs?smart=1").get_data(as_text=True)

    kotak = re.search(r'<input[^>]*id="smart-match"[^>]*>', body)
    assert kotak, "tombol cocokkan otomatis tidak dirender"
    assert "checked" in kotak.group(0)


def test_guest_does_not_see_smart_toggle(db, monkeypatch) -> None:
    """Tombol "Cocokkan otomatis" tidak ditawarkan tanpa skill untuk dicocokkan."""
    app = _app(monkeypatch)
    body = app.test_client().get("/jobs").get_data(as_text=True)

    assert "Cocokkan otomatis" not in body


def test_logged_in_user_sees_smart_toggle(db, monkeypatch) -> None:
    """Pengguna dengan skill terkonfirmasi melihat tombolnya."""
    app = _app(monkeypatch)
    c = app.test_client()
    _login(c)

    body = c.get("/jobs").get_data(as_text=True)

    assert "Cocokkan otomatis" in body


def test_skill_panel_shows_confirmed_skills(db, monkeypatch) -> None:
    """Panel kanan menampilkan skill dari database, bukan keadaan kosong.

    Regresi: panel pernah dirender dengan keadaan "belum masuk" meski pengguna
    login, sehingga skill yang jelas ada di `user_skills` tidak muncul.
    """
    app = _app(monkeypatch)
    c = app.test_client()
    _login(c)

    body = c.get("/jobs").get_data(as_text=True)

    assert "Skill terkonfirmasi" in body
    assert "Belum ada skill terkonfirmasi" not in body
    for skill in ("python", "sql", "docker", "git"):
        assert f'class="tag">{skill}<' in body, f"{skill} tidak tampil di panel"


def test_skill_panel_links_to_cv_not_login(db, monkeypatch) -> None:
    """Tombol "Kelola skill" menuju /cv, bukan /auth/login.

    Pengguna yang sudah login tidak boleh dikirim ke halaman login untuk
    mengelola skill miliknya sendiri.
    """
    app = _app(monkeypatch)
    c = app.test_client()
    _login(c)

    body = c.get("/jobs").get_data(as_text=True)

    assert 'href="/cv' in body
    assert 'href="/auth/login">Kelola skill' not in body


def test_guest_panel_says_sign_in(db, monkeypatch) -> None:
    """Tamu diarahkan masuk, dan panelnya tidak berisi skill siapa pun."""
    app = _app(monkeypatch)
    body = app.test_client().get("/jobs").get_data(as_text=True)

    assert "Masuk untuk mengelola skill" in body
    assert "Belum masuk" in body

    # Periksa panelnya saja: tag skill di kartu lowongan memang milik lowongan,
    # bukan milik pengguna.
    panel = re.search(
        r'aria-label="Profil dan skill terkonfirmasi".*?</section>', body, re.S
    )
    assert panel, "panel skill tidak dirender untuk tamu"
    assert 'class="tag"' not in panel.group(0)
