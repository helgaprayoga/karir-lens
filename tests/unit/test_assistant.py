"""PRD-08 §7.1: asisten AI.

Semua test memakai klien DeepSeek tiruan — tidak ada panggilan jaringan
(R-08-13). Yang diuji adalah perilaku: konteks yang disusun, batas yang
ditegakkan, dan janji bahwa jawaban hanya merujuk data tersimpan.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.assistant import repository as assistant_repo
from app.assistant import service
from core.errors import RateLimitError
from core.external.deepseek import AssistantError


# --- tiruan -------------------------------------------------------------

class Klien:
    """Klien DeepSeek tiruan: merekam pesan, mengembalikan jawaban siap pakai."""

    def __init__(self, balasan: str = "Jawaban dari data."):
        self.balasan = balasan
        self.panggilan: list[list[dict]] = []

    def chat(self, messages, **_k):
        self.panggilan.append(messages)
        return {"reply": self.balasan, "sumber": []}


class KlienGagal:
    def chat(self, messages, **_k):
        raise AssistantError("Layanan asisten sedang tidak dapat dihubungi.")


class KlienTimeout:
    def chat(self, messages, **_k):
        raise AssistantError("Asisten sedang sibuk. Coba lagi beberapa saat lagi.")


# --- klien database tiruan ---------------------------------------------

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
        self._limit = None
        self._count = False

    def select(self, *_a, count=None):
        self._mode = "select"
        self._count = count == "exact"
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def eq(self, kolom, nilai):
        self._pred.append(lambda r, k=kolom, v=nilai: r.get(k) == v)
        return self

    def or_(self, ekspresi):
        """Tiruan `or_` PostgREST: cocok bila salah satu klausa cocok.

        Di-parse sungguhan, bukan diabaikan: kalau tiruan mengembalikan semua
        baris, test "pertanyaan asing memicu klarifikasi" akan lulus atau gagal
        karena alasan yang salah.
        """
        import re as _re

        klausa = _re.findall(r"(\w+)\.ilike\.%([^%]*)%", ekspresi)
        skill = _re.findall(r"skills\.cs\.\{([^}]*)\}", ekspresi)

        def cocok(row):
            for kolom, pola in klausa:
                if pola.lower() in str(row.get(kolom) or "").lower():
                    return True
            for nama in skill:
                if nama in (row.get("skills") or []):
                    return True
            return False

        self._pred.append(cocok)
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
            tabel.append(dict(self._payload))
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


class DB:
    def __init__(self, jobs, clusters, skills=None):
        self._t = {
            "jobs": jobs,
            "clusters": clusters,
            "sources": [{"id": 1, "name": "dealls"}],
            "user_skills": skills or [],
            "ai_usage": [],
        }

    def tabel(self, nama):
        return self._t.setdefault(nama, [])

    def table(self, nama):
        return Tabel(self, nama)


def _job(i, **ubah):
    dasar = {
        "id": i,
        "title": f"Data Analyst {i}",
        "company_name": "Northwind Data",
        "location": "Jakarta",
        "employment_type": "full-time",
        "skills": ["python", "sql"],
        "salary_min": 9_000_000,
        "salary_max": 12_000_000,
        "salary_currency": "IDR",
        "salary_period": "month",
        "source_id": 1,
        "source_url": f"https://dealls.com/loker/data-analyst-{i}",
        "posted_at": "2026-11-01T00:00:00+00:00",
        "cluster_id": 1,
    }
    dasar.update(ubah)
    return dasar


@pytest.fixture
def db(monkeypatch):
    dari = DB(
        [_job(i) for i in range(1, 4)],
        [{"id": 1, "label": "Data & Ai", "keywords": ["data", "python"]}],
        skills=[
            {"id": 1, "user_id": 1, "skill": "python", "is_confirmed": True},
            {"id": 2, "user_id": 1, "skill": "figma", "is_confirmed": False},
        ],
    )
    monkeypatch.setattr(assistant_repo, "_client", lambda: dari)

    # `user_loader` Flask-Login membaca tabel `users`; tanpa tambalan ini ia
    # menghubungi Supabase sungguhan, gagal, dan sesi dianggap tidak login —
    # setiap request berakhir 302 alih-alih diuji.
    from app.auth import repository as auth_repo

    monkeypatch.setattr(
        auth_repo,
        "find_by_id",
        lambda uid: {"id": uid, "email": "u@contoh.test", "name": "Uji",
                     "created_at": "2026-10-01T00:00:00+00:00"},
    )
    return dari


@pytest.fixture
def app_factory(monkeypatch):
    """Pembuat aplikasi dengan CSRF dimatikan lewat kelas config.

    ``WTF_CSRF_ENABLED`` harus mati **sebelum** ``create_app``: ``CSRFProtect``
    membaca config itu saat diikat ke aplikasi, bukan per permintaan. Mengubah
    ``app.config`` sesudahnya tidak berpengaruh.
    """
    from app.config import CONFIG_MAP

    monkeypatch.setitem(
        CONFIG_MAP,
        "assistant_test",
        type("AssistantTest", (CONFIG_MAP["testing"],), {"WTF_CSRF_ENABLED": False}),
    )
    return lambda client=None: _app(client, "assistant_test")


def _app(client=None, config="assistant_test"):
    from app.config import CONFIG_MAP

    if config not in CONFIG_MAP:
        CONFIG_MAP[config] = type(
            "AssistantDefault", (CONFIG_MAP["testing"],), {"WTF_CSRF_ENABLED": False}
        )
    app = create_app(config)
    app.config.update(TESTING=True)
    if client is not None:
        app.config["DEEPSEEK_CLIENT"] = client
    return app


def _login(c, uid=1):
    with c.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


# --- R-08-02 / R-08-04: konteks ---------------------------------------

def test_context_uses_confirmed_skills_only(db) -> None:
    """Konteks hanya memuat skill terkonfirmasi, bukan CV mentah (R-08-04)."""
    context = service.build_context("lowongan data analyst", 1)

    assert context["skills"] == ["python"], "skill belum dikonfirmasi tidak boleh ikut"
    assert "figma" not in context["skills"]


def test_context_has_jobs_clusters_salary(db) -> None:
    """Konteks disusun dari lowongan, kategori, dan statistik gaji (R-08-02)."""
    context = service.build_context("data analyst", 1)

    assert set(context) == {"jobs", "categories", "salary", "skills"}
    assert context["jobs"], "lowongan relevan harus ada"
    assert context["categories"][0]["label"] == "Data & Ai"
    assert "sample_sufficient" in context["salary"]


def test_context_never_contains_cv_text(db) -> None:
    """Tidak ada jalur yang membaca isi CV (R-08-04)."""
    import inspect

    sumber = inspect.getsource(service)
    for dilarang in ("extract_text", "pypdf", "docx", "cv_suggestions"):
        assert dilarang not in sumber, f"service memuat {dilarang!r}"


def test_context_size_bounded(db) -> None:
    """Konteks dibatasi agar biaya dan latensi terkendali (§9)."""
    context = service.build_context("data analyst", 1)
    assert len(context["jobs"]) <= service.MAX_JOBS_IN_CONTEXT


# --- R-08-05 / R-08-06: jawaban ---------------------------------------

def test_answer_grounded_in_context(db) -> None:
    """Model menerima system prompt yang melarang klaim di luar konteks."""
    klien = Klien("Ada 3 lowongan Data Analyst di Northwind Data.")
    hasil = service.ask("lowongan data analyst", 1, client=klien)

    pesan = klien.panggilan[0]
    assert pesan[0]["role"] == "system"
    assert "HANYA dari DATA" in pesan[0]["content"]
    assert "Jangan mengarang" in pesan[0]["content"]
    # Konteks benar-benar dikirim ke model.
    assert "Northwind Data" in pesan[1]["content"]
    assert hasil["reply"].startswith("Ada 3 lowongan")


def test_links_from_stored_jobs(db) -> None:
    """Tautan yang dikembalikan berasal dari `jobs`, bukan dari model (R-08-06).

    Model dapat mengarang URL; karena itu sumber diambil dari konteks, bukan
    dari jawaban model.
    """
    klien = Klien("Lihat https://contoh-palsu.test/lowongan")
    hasil = service.ask("data analyst", 1, client=klien)

    url = [s["url"] for s in hasil["sources"]]
    assert url, "sumber harus ada"
    for u in url:
        assert u.startswith("https://dealls.com/"), f"URL bukan dari data: {u}"
    assert all("contoh-palsu" not in u for u in url)


def test_sources_have_label_and_url(db) -> None:
    """Setiap sumber punya label yang dapat dibaca dan URL."""
    hasil = service.ask("data analyst", 1, client=Klien())
    for sumber in hasil["sources"]:
        assert set(sumber) == {"label", "url"}
        assert "Data Analyst" in sumber["label"]


# --- R-08-07: data tidak cukup ----------------------------------------

def test_insufficient_data_asks_clarification(monkeypatch) -> None:
    """Konteks kosong memicu klarifikasi, bukan panggilan model (R-08-07)."""
    dari = DB([], [], skills=[])
    monkeypatch.setattr(assistant_repo, "_client", lambda: dari)

    klien = Klien()
    hasil = service.ask("apa itu quantum computing", 1, client=klien)

    assert klien.panggilan == [], "model tidak boleh dipanggil saat data kosong"
    assert "belum menemukan lowongan" in hasil["reply"].lower()
    assert hasil["sources"] == []


def test_unrelated_question_asks_clarification(db) -> None:
    """Pertanyaan di luar data tidak dikirim ke model.

    Kategori selalu ada setelah clustering, jadi syarat "kategori kosong" tidak
    pernah terpenuhi dan pertanyaan apa pun akan lolos ke model. Terukur: "apa
    itu quantum computing" sempat dijawab model dengan "Ada lowongan Data
    Analyst" — jawaban yang tidak menjawab pertanyaannya.
    """
    klien = Klien()
    hasil = service.ask("apa itu quantum computing", 1, client=klien)

    assert klien.panggilan == [], "model tidak boleh dipanggil untuk pertanyaan asing"
    assert "belum menemukan lowongan" in hasil["reply"].lower()


def test_category_question_still_answered(monkeypatch) -> None:
    """Pertanyaan tentang kategori tetap dikirim ke model.

    Konteks memang memuat kategori, jadi klarifikasi tidak perlu — menolaknya
    akan membuat asisten tidak berguna untuk pertanyaan yang datanya ada.
    """
    dari = DB(
        [],
        [{"id": 1, "label": "Data & Ai", "keywords": ["data", "python"]}],
        skills=[],
    )
    monkeypatch.setattr(assistant_repo, "_client", lambda: dari)

    klien = Klien("Kategori yang tersedia: Data & Ai.")
    hasil = service.ask("kategori apa saja yang ada", 1, client=klien)

    assert klien.panggilan, "model harus dipanggil saat kategori relevan"
    assert "Data" in hasil["reply"]


def test_clarification_suggests_what_to_ask(monkeypatch) -> None:
    """Klarifikasi menyebut apa yang bisa ditanyakan agar pengguna tidak buntu."""
    dari = DB([], [], skills=[])
    monkeypatch.setattr(assistant_repo, "_client", lambda: dari)

    hasil = service.ask("xyz", 1, client=Klien())
    assert "posisi" in hasil["reply"].lower() or "skill" in hasil["reply"].lower()


# --- R-08-09: rate limit ---------------------------------------------

def test_rate_limit_per_user(db) -> None:
    """Permintaan melebihi batas ditolak dengan pesan jelas (R-08-09)."""
    klien = Klien()

    for _ in range(3):
        service.ask("data analyst", 1, client=klien, batas_harian=3)

    with pytest.raises(RateLimitError) as info:
        service.ask("data analyst", 1, client=klien, batas_harian=3)

    assert "Batas 3 pertanyaan" in info.value.message
    assert "besok" in info.value.message.lower()


def test_daily_limit_counts_per_day(db) -> None:
    """Batas dihitung per hari: kemarin tidak mengurangi hari ini (R-08-09)."""
    db.tabel("ai_usage").extend(
        [{"user_id": 1, "tanggal": "2026-01-01"} for _ in range(5)]
    )

    # Hari ini masih kosong, jadi permintaan pertama harus lolos.
    hasil = service.ask("data analyst", 1, client=Klien(), batas_harian=3)
    assert hasil["reply"]


def test_limit_not_consumed_on_clarification(monkeypatch) -> None:
    """Pertanyaan yang tidak terjawab tidak memotong kuota.

    Pengguna tidak menerima jawaban; memotong kuota atas pertanyaan yang kita
    tolak sendiri akan menghukumnya dua kali.
    """
    dari = DB([], [], skills=[])
    monkeypatch.setattr(assistant_repo, "_client", lambda: dari)

    before = len(dari.tabel("ai_usage"))
    service.ask("xyz", 1, client=Klien())
    assert len(dari.tabel("ai_usage")) == before


def test_limit_not_consumed_on_failure(db) -> None:
    """Permintaan yang gagal tidak mengurangi kuota pengguna.

    Pengguna tidak mendapat jawaban; mengurangi kuotanya akan menghukum mereka
    atas kegagalan layanan.
    """
    before = len(db.tabel("ai_usage"))

    with pytest.raises(AssistantError):
        service.ask("data analyst", 1, client=KlienGagal(), batas_harian=5)

    assert len(db.tabel("ai_usage")) == before


def test_limit_not_consumed_without_client(db) -> None:
    """Tanpa klien, tidak ada jawaban dan tidak ada pemakaian tercatat."""
    before = len(db.tabel("ai_usage"))
    hasil = service.ask("data analyst", 1, client=None)

    assert "belum dikonfigurasi" in hasil["reply"].lower()
    assert len(db.tabel("ai_usage")) == before


# --- R-08-10: error dan timeout ---------------------------------------

def test_api_timeout_handled(db) -> None:
    """Timeout menghasilkan pesan ramah tanpa detail internal (R-08-10)."""
    with pytest.raises(AssistantError) as info:
        service.ask("data analyst", 1, client=KlienTimeout())

    pesan = info.value.message
    assert "Coba lagi" in pesan
    for bocor in ("traceback", "httpx", "requests", "timeout", "20.0"):
        assert bocor not in pesan.lower()


def test_route_returns_friendly_error_on_timeout(db) -> None:
    """Route mengubah kegagalan AI menjadi 502 dengan pesan ramah."""
    app = _app(KlienTimeout())
    c = app.test_client()
    _login(c)

    r = c.post("/api/assistant", json={"message": "data analyst"})

    assert r.status_code == 502
    isi = r.get_json()
    assert isi["error"]["code"] in {"EXTERNAL_SERVICE_ERROR", "ASSISTANT_FAILED"}
    assert "traceback" not in r.get_data(as_text=True).lower()


# --- R-08-11: tanpa penyimpanan isi ----------------------------------

def test_no_cv_content_in_response(db) -> None:
    """Jawaban tidak memuat isi CV (R-08-04)."""
    hasil = service.ask("data analyst", 1, client=Klien())
    teks = repr(hasil).lower()

    for dilarang in ("curriculum vitae", "budi santoso", "pendidikan s1"):
        assert dilarang not in teks


def test_usage_table_has_no_content(db) -> None:
    """Tabel pemakaian hanya mencatat jumlah, bukan pertanyaan atau jawaban.

    R-08-11 melarang menyimpan pertanyaan dan jawaban secara permanen. Dipakai
    pertanyaan yang benar-benar dijawab, supaya barisnya memang terbentuk.
    """
    service.ask("data analyst", 1, client=Klien())

    baris = db.tabel("ai_usage")[0]
    assert set(baris) <= {"user_id", "tanggal"}
    assert "data analyst" not in repr(baris).lower()
    assert "jawaban" not in repr(baris).lower()


def test_logs_have_no_question_content(db, caplog) -> None:
    """Log tidak memuat pertanyaan pengguna (R-08-11)."""
    with caplog.at_level("DEBUG"):
        service.ask("gaji saya berapa ya di perusahaan rahasia", 1, client=Klien())

    assert "perusahaan rahasia" not in caplog.text


# --- R-08-12: rekomendasi tidak memakai asisten -----------------------

def test_recommendation_not_using_assistant() -> None:
    """Rekomendasi CV tidak memanggil asisten (R-08-12).

    Diperiksa dari sumber modul: kalau cepat atau lambat seseorang menyambung
    keduanya, rekomendasi akan bergantung pada AI dan biayanya membengkak.
    """
    import inspect

    from app.cv import recommender, service as cv_service

    for modul in (recommender, cv_service):
        sumber = inspect.getsource(modul)
        assert "assistant" not in sumber, f"{modul.__name__} memanggil asisten"


# --- route ------------------------------------------------------------

def test_assistant_requires_login(db) -> None:
    """Pengunjung ditolak (R-08-01)."""
    c = _app(Klien()).test_client()

    assert c.get("/assistant").status_code == 302
    r = c.post("/api/assistant", json={"message": "halo"})
    assert r.status_code == 302
    assert "/auth/login" in r.headers["Location"]


def test_route_contract(db) -> None:
    """Respons memenuhi kontrak PRD-F04 §4.1."""
    c = _app(Klien("Jawaban.")).test_client()
    _login(c)

    r = c.post("/api/assistant", json={"message": "data analyst"})
    isi = r.get_json()

    assert r.status_code == 200
    assert set(isi) == {"data"}
    assert set(isi["data"]) == {"reply", "sources"}
    assert isinstance(isi["data"]["sources"], list)


def test_route_rejects_empty_question(db) -> None:
    """Pertanyaan kosong ditolak 400, bukan dikirim ke model."""
    c = _app(Klien()).test_client()
    _login(c)

    r = c.post("/api/assistant", json={"message": "   "})
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_route_rejects_non_object_body(db) -> None:
    """Body bukan objek tidak menghasilkan 500."""
    c = _app(Klien()).test_client()
    _login(c)

    r = c.post("/api/assistant", json=["bukan", "objek"])
    assert r.status_code == 400


def test_question_truncated(db) -> None:
    """Pertanyaan sangat panjang dipotong, bukan dikirim utuh."""
    klien = Klien()
    service.ask("data " * 500, 1, client=klien)

    dikirim = klien.panggilan[0][1]["content"]
    assert len(dikirim) < len("data " * 500) + 2000


def test_no_client_returns_notice(db) -> None:
    """Tanpa API key, pengguna mendapat pemberitahuan, bukan error (R-08-08)."""
    c = _app().test_client()  # tanpa DEEPSEEK_CLIENT, config testing tanpa key
    _login(c)

    r = c.post("/api/assistant", json={"message": "data analyst"})
    assert r.status_code == 200
    assert "belum dikonfigurasi" in r.get_json()["data"]["reply"].lower()
