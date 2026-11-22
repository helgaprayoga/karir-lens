"""PRD-07 §7.1: ekstraksi CV dan rekomendasi.

CV uji dibuat secara sintetis saat test berjalan (lihat
``tests/fixtures/cv/buat_cv.py``) — tidak ada CV nyata di repository, dan tidak
ada panggilan jaringan maupun AI.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from app.cv import extractor, recommender, service
from core.errors import ValidationError
from tests.fixtures.cv.buat_cv import TEKS_CV, buat_docx, buat_pdf

CV_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "cv"


class BerkasPalsu:
    """Meniru ``FileStorage`` Werkzeug seperlunya."""

    def __init__(self, path: Path, filename: str | None = None, mimetype: str | None = None):
        self._isi = path.read_bytes()
        self.filename = filename if filename is not None else path.name
        self.mimetype = mimetype if mimetype is not None else self._tebak()
        self._pos = 0

    def _tebak(self) -> str:
        if self.filename.lower().endswith(".pdf"):
            return "application/pdf"
        return extractor.DOCX_MIME

    def save(self, tujuan: str | os.PathLike) -> None:
        Path(tujuan).write_bytes(self._isi)

    # Sebagian kode memakai `.stream`; tidak dipakai `service`, tetapi
    # disediakan agar tiruan ini tidak rapuh bila pemakaian berubah.
    @property
    def stream(self):
        return io.BytesIO(self._isi)


@pytest.fixture(scope="module")
def pdf_path(tmp_path_factory) -> Path:
    return buat_pdf(tmp_path_factory.mktemp("cv") / "cv_uji.pdf")


@pytest.fixture(scope="module")
def docx_path(tmp_path_factory) -> Path:
    return buat_docx(tmp_path_factory.mktemp("cv") / "cv_uji.docx")


# --- R-07-01 / R-07-02: validasi ---------------------------------------

def test_reject_unsupported_file_type() -> None:
    """Tipe selain PDF/DOCX ditolak (R-07-01)."""
    berkas = BerkasPalsu.__new__(BerkasPalsu)
    berkas.filename = "cv.txt"
    berkas.mimetype = "text/plain"

    with pytest.raises(ValidationError) as info:
        service.validate_upload(berkas)

    assert info.value.code == "UNSUPPORTED_FILE_TYPE"
    assert "PDF atau DOCX" in info.value.message


def test_reject_oversize_file(tmp_path) -> None:
    """File > 5 MB ditolak (R-07-02)."""
    besar = tmp_path / "besar.pdf"
    besar.write_bytes(b"%PDF-1.4\n" + b"x" * (service.MAX_SIZE_BYTES + 10))
    berkas = BerkasPalsu(besar, "besar.pdf", "application/pdf")

    with pytest.raises(ValidationError) as info:
        service.extract_and_suggest(berkas)

    assert info.value.code == "FILE_TOO_LARGE"


def test_reject_missing_file() -> None:
    """Tanpa berkas, pesannya jelas — bukan error 500."""
    with pytest.raises(ValidationError):
        service.validate_upload(None)


def test_accepts_generic_mimetype_for_docx(docx_path) -> None:
    """Peramban mengirim `application/octet-stream` untuk DOCX; tetap diterima.

    Yang menentukan adalah ekstensi, dengan content-type sebagai pemeriksaan
    tambahan bila ada.
    """
    berkas = BerkasPalsu(docx_path, "cv.docx", "application/octet-stream")
    assert service.validate_upload(berkas) == extractor.DOCX_MIME


# --- R-07-03: ekstraksi ------------------------------------------------

def test_extract_pdf_fixture(pdf_path) -> None:
    """Teks dan skill diekstrak dari PDF."""
    teks = extractor.extract_text(str(pdf_path), "application/pdf")

    assert "Backend Engineer" in teks
    assert "Python" in teks


def test_extract_docx_fixture(docx_path) -> None:
    """Teks dan skill diekstrak dari DOCX, termasuk isi tabel."""
    teks = extractor.extract_text(str(docx_path), extractor.DOCX_MIME)

    assert "Backend Engineer" in teks
    assert "Terraform" in teks, "isi tabel harus ikut terbaca"


def test_extract_empty_pdf(tmp_path) -> None:
    """PDF tanpa lapisan teks menghasilkan pesan ramah, bukan error mentah."""
    kosong = buat_pdf(tmp_path / "kosong.pdf", teks="")
    with pytest.raises(extractor.ExtractionError) as info:
        extractor.extract_text(str(kosong), "application/pdf")

    assert "Tidak ada teks" in str(info.value)


def test_extract_corrupt_pdf(tmp_path) -> None:
    """Berkas rusak menghasilkan pesan ramah tanpa membocorkan isi."""
    rusak = tmp_path / "rusak.pdf"
    rusak.write_bytes(b"bukan pdf sama sekali")

    with pytest.raises(extractor.ExtractionError) as info:
        extractor.extract_text(str(rusak), "application/pdf")

    assert "tidak dapat dibaca" in str(info.value).lower()


# --- R-07-04: kamus ----------------------------------------------------

def test_dictionary_matching_only() -> None:
    """Skill cocok dengan kamus tanpa AI (R-07-04, R-07-16)."""
    hasil = service.suggest_skills(TEKS_CV)

    assert "python" in hasil["skills"]
    assert "django" in hasil["skills"]
    assert "postgresql" in hasil["skills"]
    assert "docker" in hasil["skills"]
    assert isinstance(hasil["ambiguous"], list)


def test_skills_are_normalized() -> None:
    """Skill hasil ekstraksi memakai bentuk baku yang sama dengan PRD-03."""
    hasil = service.suggest_skills("Saya memakai JavaScript, Node.js, dan Postgres.")

    assert "javascript" in hasil["skills"]
    assert "node.js" in hasil["skills"]
    assert "postgresql" in hasil["skills"], "Postgres adalah alias"


# --- R-07-05: batas fallback ambigu ------------------------------------

def test_ai_fallback_limited() -> None:
    """Kandidat ambigu dibatasi, dan AI tidak dipanggil sama sekali.

    PRD-07 R-07-05 membatasi jumlahnya; R-07-16 menuntut pengujian tanpa
    jaringan. Karena itu `suggest_skills` hanya **mengusulkan** kandidat, tidak
    mengirimnya ke layanan luar.
    """
    teks = " ".join(f"kata{i}" for i in range(50))
    hasil = service.suggest_skills(teks)

    assert len(hasil["ambiguous"]) <= service.MAX_AI_FALLBACK


def test_ambiguity_only_for_short_terms() -> None:
    """Kata panjang yang tidak dikenal tidak diusulkan sebagai skill.

    Tanpa batas ini, daftar "perlu diputuskan" berisi kata biasa dari prosa CV
    dan pengguna dibanjiri pertanyaan yang tidak perlu.
    """
    hasil = service.suggest_skills("Pengalaman panjang sekali dalam mengerjakan proyek besar.")
    assert hasil["ambiguous"] == []


def test_common_words_not_offered_as_skill() -> None:
    """Kata fungsi dan nama orang tidak masuk daftar ambigu.

    Terukur pada CV uji: tanpa daftar buang, "budi" (nama), "dan", "data", dan
    "di" muncul sebagai skill yang perlu diputuskan. Daftar itu jadi tidak
    bermakna bila isinya kata biasa.
    """
    hasil = service.suggest_skills(TEKS_CV)
    teks_ambigu = {a["text"] for a in hasil["ambiguous"]}

    for kata in ("budi", "dan", "di", "ke", "yang", "untuk", "data", "tahun"):
        assert kata not in teks_ambigu, f"kata biasa {kata!r} diusulkan sebagai skill"


def test_single_skill_job_not_full_score() -> None:
    """Lowongan dengan satu skill tidak memberi skor 100%.

    Terukur pada data nyata: lowongan yang hanya menyebut "aws" mendapat 100%
    dan menempati puncak rekomendasi, di atas lowongan yang cocok pada empat
    skill. Satu titik data tidak cukup untuk menyimpulkan kecocokan.
    """
    satu, _ = recommender.score(_job(1, ["aws"]), {"aws"}, cluster_id=None)
    empat, _ = recommender.score(
        _job(2, ["aws", "docker", "python", "sql"]),
        {"aws", "docker", "python", "sql"},
        cluster_id=None,
    )

    assert satu < 100, f"skor satu skill seharusnya di bawah 100, dapat {satu}"
    assert empat > satu, "cocok pada empat skill harus lebih tinggi"


def test_full_score_still_reachable() -> None:
    """Skor tinggi tetap dapat dicapai bila banyak skill cocok.

    Faktor kepercayaan bukan penalti permanen: lowongan yang meminta empat
    skill dan semuanya dimiliki tetap mendapat skor tertinggi.
    """
    skor, _ = recommender.score(
        _job(1, ["python", "sql", "docker", "aws"]),
        {"python", "sql", "docker", "aws"},
        cluster_id=1,
    )
    assert skor >= 95


# --- R-07-08: privasi -------------------------------------------------

def test_temp_file_removed(pdf_path, monkeypatch) -> None:
    """Tidak ada berkas sementara tersisa setelah proses (R-07-08)."""
    dibuat: list[str] = []
    asli = service.tempfile.mkstemp

    def rekam(*a, **k):
        fd, path = asli(*a, **k)
        dibuat.append(path)
        return fd, path

    monkeypatch.setattr(service.tempfile, "mkstemp", rekam)

    service.extract_and_suggest(BerkasPalsu(pdf_path))

    assert dibuat, "berkas sementara sempat dibuat"
    for path in dibuat:
        assert not Path(path).exists(), f"berkas sementara tertinggal: {path}"


def test_temp_file_removed_on_failure(tmp_path, monkeypatch) -> None:
    """Berkas sementara juga dihapus ketika ekstraksi gagal.

    Ini inti R-07-08: `finally`, bukan hanya jalur sukses. Berkas rusak yang
    tertinggal di disk adalah kebocoran data pengguna.
    """
    rusak = tmp_path / "rusak.pdf"
    rusak.write_bytes(b"bukan pdf")

    dibuat: list[str] = []
    asli = service.tempfile.mkstemp

    def rekam(*a, **k):
        fd, path = asli(*a, **k)
        dibuat.append(path)
        return fd, path

    monkeypatch.setattr(service.tempfile, "mkstemp", rekam)

    with pytest.raises(ValidationError):
        service.extract_and_suggest(BerkasPalsu(rusak))

    assert dibuat
    for path in dibuat:
        assert not Path(path).exists()


def test_no_cv_logging(pdf_path, caplog) -> None:
    """Log tidak memuat isi CV (R-07-08).

    Yang boleh muncul hanya jumlah kandidat; kalimat dari CV ("Budi Santoso",
    "PostgreSQL") tidak boleh bocor ke log.
    """
    with caplog.at_level("DEBUG"):
        service.extract_and_suggest(BerkasPalsu(pdf_path))

    teks_log = caplog.text
    assert "Budi Santoso" not in teks_log
    assert "Backend Engineer" not in teks_log
    assert "PostgreSQL" not in teks_log


def test_error_messages_have_no_cv_text(tmp_path) -> None:
    """Pesan galat tidak memuat isi berkas."""
    rusak = tmp_path / "rusak.docx"
    rusak.write_bytes(b"PK\x03\x04 bukan docx")

    try:
        extractor.extract_text(str(rusak), extractor.DOCX_MIME)
    except extractor.ExtractionError as error:
        assert "Budi" not in str(error)
    else:  # pragma: no cover
        pytest.fail("seharusnya melempar ExtractionError")


# --- R-07-09 / R-07-10: skor dan alasan -------------------------------

def _job(id_, skills, cluster_id=1, posted="2026-11-01T00:00:00+00:00", **ubah):
    dasar = {
        "id": id_,
        "title": f"Job {id_}",
        "company_name": "NovaTech",
        "company_slug": "novatech",
        "location": "Jakarta",
        "employment_type": "full-time",
        "description": "Deskripsi.",
        "skills": skills,
        "skills_source": "declared",
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "source_id": 1,
        "source_url": f"https://dealls.com/{id_}",
        "posted_at": posted,
        "cluster_id": cluster_id,
    }
    dasar.update(ubah)
    return dasar


def test_recommendation_reason() -> None:
    """Alasan menyebut skill yang cocok (R-07-10)."""
    skor, alasan = recommender.score(
        _job(1, ["python", "sql", "airflow"]),
        {"python", "sql", "git"},
        cluster_id=1,
    )

    assert skor > 0
    assert any("python" in a and "sql" in a for a in alasan), alasan


def test_recommendation_score_bounds() -> None:
    """Skor berada di 0..100 dan skill identik memberi skor tertinggi."""
    penuh, _ = recommender.score(_job(1, ["python"]), {"python"}, cluster_id=1)
    nol, _ = recommender.score(_job(2, ["rust"]), {"python"}, cluster_id=1)

    assert 0 <= nol < penuh <= 100


def test_category_contributes() -> None:
    """Kategori yang sama menambah skor; kategori berbeda tidak menguranginya."""
    dasar = _job(1, ["python"], cluster_id=7)
    sama, _ = recommender.score(dasar, {"python"}, cluster_id=7)
    beda, _ = recommender.score(dasar, {"python"}, cluster_id=9)

    assert sama > beda


def test_rank_excludes_bookmarked() -> None:
    """Lowongan tersimpan tidak muncul sebagai rekomendasi utama (R-07-14)."""
    jobs = [_job(1, ["python"]), _job(2, ["python"])]
    hasil = recommender.rank(jobs, {"python"}, 1, exclude_ids={1})

    assert [j["id"] for j in hasil] == [2]


def test_rank_drops_no_overlap() -> None:
    """Lowongan tanpa satu pun skill cocok tidak direkomendasikan.

    "Belum ada skill yang cocok" bukan rekomendasi; menampilkannya hanya
    memenuhi halaman dengan kartu yang tidak relevan.
    """
    jobs = [_job(1, ["python"]), _job(2, ["rust", "haskell"])]
    hasil = recommender.rank(jobs, {"python"}, None)

    assert [j["id"] for j in hasil] == [1]


def test_rank_stable_order() -> None:
    """Skor sama diurutkan menurut tanggal terbit terbaru."""
    jobs = [
        _job(1, ["python"], posted="2026-11-01T00:00:00+00:00"),
        _job(2, ["python"], posted="2026-11-05T00:00:00+00:00"),
    ]
    hasil = recommender.rank(jobs, {"python"}, None)

    assert [j["id"] for j in hasil] == [2, 1]


# --- R-07-11: tanpa AI per permintaan ---------------------------------

def test_recommendation_no_ai_call(monkeypatch) -> None:
    """Perhitungan rekomendasi tidak memanggil AI (R-07-11).

    Diperiksa dari modul sumbernya: `recommender` dan `service` tidak mengimpor
    klien jaringan mana pun.
    """
    import inspect

    for modul in (recommender, service):
        sumber = inspect.getsource(modul)
        for dilarang in ("deepseek", "DeepSeek", "requests", "httpx", "openai"):
            assert dilarang not in sumber, f"{modul.__name__} memuat {dilarang!r}"


# --- Kontrak hasil ----------------------------------------------------

def test_suggest_contract() -> None:
    """Bentuk hasil sesuai kontrak `POST /api/cv/extract`."""
    hasil = service.suggest_skills(TEKS_CV)

    assert set(hasil) == {"skills", "ambiguous"}
    assert isinstance(hasil["skills"], list)
    for item in hasil["ambiguous"]:
        assert set(item) == {"text", "reason"}


def test_empty_text_rejected() -> None:
    """Teks kosong ditolak dengan pesan jelas."""
    with pytest.raises(ValidationError):
        service.suggest_skills("   ")


def test_skill_overlap_normalizes_both_sides() -> None:
    """Perbandingan skill tidak peka huruf besar dan spasi berlebih."""
    hasil = recommender.skill_overlap(["Python", " SQL "], {"python", "sql"})
    assert hasil == ["python", "sql"]
