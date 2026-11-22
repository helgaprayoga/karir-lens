"""PRD-F04 §7.1: alur CV, konfirmasi skill, rekomendasi, dan asisten AI.

Track A memakai fixture, jadi halaman hidup di blueprint ``preview``. Test tetap
memeriksa template produksi yang sama.
"""

from __future__ import annotations

import re

import pytest

from app import create_app
from app.config import CONFIG_MAP


@pytest.fixture(scope="module")
def ui():
    CONFIG_MAP["f04_preview"] = type(
        "F04Preview", (CONFIG_MAP["testing"],), {"PREVIEW_UI": True, "WTF_CSRF_ENABLED": False}
    )
    application = create_app("f04_preview")
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def uiClient(ui):
    return ui.test_client()


def _html(response) -> str:
    return response.get_data(as_text=True)


# --- R-F04-01 / R-F04-02 / R-F04-06: zona unggah --------------------------

def test_cv_upload_accept_attr(uiClient) -> None:
    """Zona unggah membatasi tipe berkas ke PDF dan DOCX (R-F04-01)."""
    body = _html(uiClient.get("/preview/cv"))
    accept = re.search(r'<input[^>]*type="file"[^>]*accept="([^"]+)"', body)

    assert accept, "input file tanpa atribut accept"
    assert ".pdf" in accept.group(1)
    assert ".docx" in accept.group(1)


def test_cv_size_hint_present(uiClient) -> None:
    """Batas ukuran dan pernyataan tidak menyimpan terbaca sebelum unggah."""
    body = _html(uiClient.get("/preview/cv?state=idle"))

    assert "maksimum 5 MB" in body
    assert "tidak disimpan" in body
    # Batas ukuran juga tersedia sebagai angka untuk validasi klien.
    assert 'data-max-bytes="5242880"' in body


def test_cv_upload_keyboard_accessible(uiClient) -> None:
    """Input berkas tidak `display: none`, dan punya label terhubung."""
    body = _html(uiClient.get("/preview/cv"))
    # `type="file"` harus ada dan tidak disembunyikan dengan display:none.
    assert 'type="file"' in body
    assert 'for="cv-file"' in body
    assert 'id="cv-file"' in body

    css = open("static/css/components.css", encoding="utf-8").read()
    blok = css.split(".upload-input {")[1].split("}")[0]
    assert "display: none" not in blok, "input tidak boleh display:none"
    assert "clip" in blok, "input harus disembunyikan secara visual, bukan dihapus"


def test_cv_rejects_bad_type_and_size_scripted(uiClient) -> None:
    """Validasi klien menolak tipe salah dan berkas kebesaran (R-F04-03)."""
    body = _html(uiClient.get("/preview/cv"))

    assert "Berkas harus PDF atau DOCX" in body
    assert "melebihi batas" in body
    # Pesan galat kosong di render awal: tidak ada peringatan palsu.
    assert re.search(r'data-upload-error[^>]*hidden', body)


# --- R-F04-04 / R-F04-05: konfirmasi skill -------------------------------

def test_cv_skills_preselected(uiClient) -> None:
    """Semua kandidat skill terpilih sebagai bawaan (R-F04-04)."""
    body = _html(uiClient.get("/preview/cv?state=extracted"))
    kotak = re.findall(r'<input type="checkbox"[^>]*name="skills"[^>]*>', body)

    assert kotak, "tidak ada checkbox skill"
    belum_terpilih = [k for k in kotak if "checked" not in k]
    assert not belum_terpilih, f"{len(belum_terpilih)} kandidat tidak terpilih"


def test_cv_confirm_disabled_without_selection(uiClient) -> None:
    """Tombol simpan tidak aktif bila tidak ada skill dipilih (R-F04-05).

    Di state ``idle`` panel konfirmasi belum ada sama sekali — tidak ada kandidat
    untuk disimpan. Yang diuji di sini: template menandai tombol disabled saat
    kandidat kosong, dan skrip menonaktifkannya saat semua centang dilepas.
    """
    body = _html(uiClient.get("/preview/cv?state=extracted"))
    tombol = re.search(r'<button[^>]*data-confirm-skills[^>]*>', body)
    assert tombol, "tombol konfirmasi tidak dirender"
    # Ada kandidat, jadi tombol aktif.
    assert "disabled" not in tombol.group(0)

    # Skrip menonaktifkan tombol ketika tidak ada centang tersisa.
    assert "tombol.disabled = terpilih.length === 0" in body
    assert "Pilih minimal satu skill" in body

    # Template punya cabang disabled untuk kandidat kosong.
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    partial = (root / "templates" / "components" / "skill_confirm_list.html").read_text(encoding="utf-8")
    assert 'disabled" if not suggested' in partial


def test_cv_idle_has_no_confirm_panel(uiClient) -> None:
    """Sebelum ada ekstraksi, tidak ada panel konfirmasi yang menganga."""
    body = _html(uiClient.get("/preview/cv?state=idle"))
    # Skrip menyebut selector yang sama, jadi periksa markup saja.
    markup = body.split("<script>")[0]

    assert "data-confirm-skills" not in markup
    assert 'class="skill-choice"' not in markup


def test_cv_states_rendered(uiClient) -> None:
    """Empat state merender blok yang benar, tidak saling bercampur."""
    idle = _html(uiClient.get("/preview/cv?state=idle"))
    assert "Belum ada berkas dipilih" in idle
    assert 'class="skill-choice"' not in idle
    assert 'class="job-card"' not in idle

    extracted = _html(uiClient.get("/preview/cv?state=extracted"))
    assert 'class="skill-choice"' in extracted

    kosong = _html(uiClient.get("/preview/cv?state=no_skills"))
    assert 'class="empty"' in kosong
    assert "Belum ada skill terkonfirmasi" in kosong

    siap = _html(uiClient.get("/preview/cv?state=ready"))
    assert 'class="job-card"' in siap
    assert 'class="empty"' not in siap


def test_cv_unknown_state_falls_back(uiClient) -> None:
    """State tak dikenal tidak menjatuhkan halaman."""
    assert uiClient.get("/preview/cv?state=ngawur").status_code == 200


# --- R-F04-07 / R-F04-08 / R-F04-09: rekomendasi -------------------------

def test_no_skills_guidance(uiClient) -> None:
    """Tanpa skill, pengguna mendapat arahan, bukan rekomendasi kosong (R-F04-07)."""
    body = _html(uiClient.get("/preview/cv?state=no_skills"))

    assert 'class="empty"' in body
    assert "Unggah CV" in body or "Tambahkan skill" in body
    assert 'class="job-card"' not in body


def test_recommendation_has_reason(uiClient) -> None:
    """Setiap MatchBadge disertai alasan tekstual (R-F04-08)."""
    body = _html(uiClient.get("/preview/cv?state=ready"))

    badge = body.count('class="match ')
    alasan = body.count('class="match-reason"')
    assert badge > 0
    assert badge == alasan, f"{badge} badge tapi {alasan} alasan"


def test_low_score_not_danger_color(uiClient) -> None:
    """Skor rendah memakai abu-abu, bukan merah (R-F04-09)."""
    body = _html(uiClient.get("/preview/cv?state=ready"))

    # Fixture memuat skor 47, yaitu tier rendah.
    assert "47% cocok" in body
    assert "match-low" in body
    assert "match-danger" not in body
    assert "banner-error" not in body

    css = open("static/css/components.css", encoding="utf-8").read()
    rendah = css.split(".match-low {")[1].split("}")[0]
    assert "--danger" not in rendah
    assert "--ink-3" in rendah


# --- R-F04-10 s.d. R-F04-14: asisten -------------------------------------

def test_assistant_live_region(uiClient) -> None:
    """Area pesan memakai role=log dengan aria-live=polite (R-F04-10)."""
    body = _html(uiClient.get("/preview/assistant"))
    log = re.search(r'<div class="chat-log"[^>]*>', body)

    assert log, "tidak ada area pesan"
    assert 'aria-live="polite"' in log.group(0)
    assert 'role="log"' in log.group(0)
    assert 'data-chat-input' in body
    assert 'data-chat-send' in body


def test_assistant_processing_state(uiClient) -> None:
    """Indikator memproses tersembunyi di awal dan diatur skrip (R-F04-11)."""
    body = _html(uiClient.get("/preview/assistant"))

    assert re.search(r'data-chat-typing[^>]*hidden|hidden[^>]*data-chat-typing', body)
    assert "kirim.disabled = sibuk" in body
    assert "Mengirim…" in body


def test_assistant_error_banner(uiClient) -> None:
    """Galat jaringan tampil sebagai pesan ramah tanpa detail internal (R-F04-12)."""
    body = _html(uiClient.get("/preview/assistant"))

    assert "Maaf, jawaban gagal diambil" in body
    # Tidak boleh membocorkan kode status atau nama exception ke pengguna.
    pesan_galat = body.split("Maaf, jawaban gagal diambil")[1][:80]
    for bocor in ("HTTP", "Error:", "null", "undefined", "fetch"):
        assert bocor not in pesan_galat, f"pesan galat memuat {bocor}"


def test_assistant_sources_clickable(uiClient) -> None:
    """Sumber yang dikutip tampil sebagai tautan (R-F04-13)."""
    body = _html(uiClient.get("/preview/assistant"))

    assert 'class="msg-sources"' in body
    sumber = re.findall(r'<a href="([^"]+)"', body.split('class="msg-sources"')[1])
    assert sumber, "sumber tidak berupa tautan"
    assert any(u.startswith("/preview/jobs/") for u in sumber)


def test_no_cross_session_history(uiClient) -> None:
    """Tidak ada riwayat lintas sesi: tanpa localStorage, tanpa tombol muat (R-F04-14)."""
    body = _html(uiClient.get("/preview/assistant")).lower()

    for dilarang in ("localstorage", "sessionstorage", "muat riwayat",
                     "riwayat tersimpan", "indexeddb"):
        assert dilarang not in body, f"Asisten menyiratkan riwayat permanen: {dilarang}"


# --- R-F04-15: larangan penyimpanan CV ----------------------------------

def test_no_cv_persistence_ui(uiClient) -> None:
    """Tidak ada UI yang menyiratkan CV disimpan atau dapat dibuka kembali."""
    for path in ("/preview/cv", "/preview/cv?state=extracted", "/preview/cv?state=ready"):
        body = _html(uiClient.get(path)).lower()
        for dilarang in ("cv tersimpan", "riwayat cv", "lihat cv saya",
                         "unduh cv", "buka kembali cv", "arsip cv"):
            assert dilarang not in body, f"{path} menyiratkan penyimpanan CV: {dilarang}"


def test_api_contract_shapes(uiClient) -> None:
    """Bentuk respons API tiruan sesuai kontrak §4.1."""
    ekstrak = uiClient.post("/preview/api/cv/extract").get_json()
    assert set(ekstrak["data"]) == {"skills", "ambiguous"}
    assert isinstance(ekstrak["data"]["skills"], list)

    jawab = uiClient.post("/preview/api/assistant", json={"message": "halo"}).get_json()
    assert set(jawab["data"]) == {"reply", "sources"}
    assert isinstance(jawab["data"]["sources"], list)


def test_api_preview_mocked_only(uiClient) -> None:
    """Kedua endpoint kini punya versi produksi.

    ``/api/cv/extract`` diisi PRD-07 dan ``/api/assistant`` diisi PRD-08. Tiruan
    Track A tetap ada di bawah ``/preview`` untuk pengujian dengan fixture.
    """
    produksi = create_app("testing")
    jalur = {rule.rule for rule in produksi.url_map.iter_rules()}

    assert "/api/cv/extract" in jalur, "PRD-07 mengisi endpoint ini"
    assert "/api/cv/recommendations" in jalur
    assert "/api/assistant" in jalur, "PRD-08 mengisi endpoint ini"
    # Tiruan Track A tetap ada di bawah /preview.
    assert "/preview/api/cv/extract" in {
        rule.rule for rule in uiClient.application.url_map.iter_rules()
    }


# --- Bug yang ditemukan lewat audit browser ------------------------------

def test_fetch_carries_csrf_token(uiClient) -> None:
    """Permintaan AJAX mengirim token CSRF.

    Tanpa ini endpoint POST ditolak 400 di development, karena CSRF aktif di
    sana (hanya ``testing`` yang mematikannya). Test otomatis lama lolos karena
    test client tidak memakai CSRF, sementara browser sungguhan gagal.
    """
    for path in ("/preview/assistant", "/preview/cv"):
        body = _html(uiClient.get(path))
        assert 'name="csrf-token"' in body, f"{path} tidak menyediakan token"
        assert 'X-CSRFToken' in body, f"{path} tidak mengirim token pada fetch"


def test_chat_suggestions_wrap_at_narrow_width() -> None:
    """Chip saran tidak boleh melebar melewati layar.

    Kalimat saran membuat chip 382px pada viewport 360px, menyeret seluruh
    halaman menjadi 421px. Yang menjaga: max-width dan white-space normal.
    """
    css = open("static/css/components.css", encoding="utf-8").read()
    blok = css.split(".chat-suggest .chip {")[1].split("}")[0]

    assert "max-width: 100%" in blok
    assert "white-space: normal" in blok
    assert "width: fit-content" in blok


def test_nav_cannot_widen_page() -> None:
    """Nav dengan lima menu menyusut dan menggulir, bukan melebarkan halaman."""
    css = open("static/css/components.css", encoding="utf-8").read()
    blok = css.split(".top nav {")[1].split("}")[0]

    assert "min-width: 0" in blok
    assert "overflow-x: auto" in blok


def test_chat_uses_escaping_not_innerhtml(uiClient) -> None:
    """Jawaban server disisipkan lewat textContent, bukan innerHTML."""
    body = _html(uiClient.get("/preview/assistant"))
    skrip = body.split("<script>")[-1]

    assert "innerHTML" not in skrip, "jawaban server tidak boleh jadi HTML"
    assert "textContent" in skrip
