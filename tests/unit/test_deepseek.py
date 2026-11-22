"""PRD-08: klien HTTP DeepSeek.

Tidak ada panggilan jaringan (R-08-13). ``session`` diinjeksi sebagai tiruan
sehingga yang diuji adalah **bentuk permintaan** yang dikirim — di situlah dua
kesalahan nyata terjadi:

1. Nama model ``deepseek-chat`` dihentikan DeepSeek pada 2026-07-24. Setiap
   panggilan dibalas 400, dan pengguna melihat "asisten sedang sibuk".
2. Thinking mode menyala secara bawaan, memakan jatah ``max_tokens`` sehingga
   ``content`` dapat kosong — dan ``temperature`` diabaikan tanpanya.
"""

from __future__ import annotations

import json

import pytest

from core.external.deepseek import AssistantError, DeepSeek


class Respons:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("bukan JSON")
        return self._payload


class Sesi:
    """Merekam permintaan, membalas dengan respons yang sudah disiapkan."""

    def __init__(self, respons):
        self.respons = respons
        self.permintaan: list[dict] = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.permintaan.append(
            {"url": url, "payload": json, "headers": headers, "timeout": timeout}
        )
        return self.respons


def _balasan(teks: str) -> Respons:
    return Respons(200, {"choices": [{"message": {"content": teks}}]})


def test_payload_memakai_model_terkini_dan_thinking_mati() -> None:
    """Model harus ``deepseek-flash``, dan thinking harus dimatikan.

    ``deepseek-chat`` sudah dihentikan 2026-07-24. Thinking mode bawaan memakan
    ``max_tokens`` sehingga jawaban bisa kosong, dan membuat ``temperature``
    diabaikan — padahal temperature rendah itulah yang menahan model mengarang.
    """
    sesi = Sesi(_balasan("ok"))
    klien = DeepSeek("kunci", "deepseek-flash", session=sesi)

    klien.chat([{"role": "user", "content": "halo"}], max_tokens=32)

    payload = sesi.permintaan[0]["payload"]
    assert payload["model"] == "deepseek-flash"
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 32


def test_balasan_200_diparse() -> None:
    """Balasan 200 menjadi ``{"reply": ..., "sumber": []}``."""
    sesi = Sesi(_balasan("  Ini jawabannya.  "))
    klien = DeepSeek("kunci", "deepseek-flash", session=sesi)

    hasil = klien.chat([{"role": "user", "content": "halo"}])

    assert hasil == {"reply": "Ini jawabannya.", "sumber": []}


def test_galat_400_menjadi_assistant_error() -> None:
    """Model tidak dikenal dibalas 400; pesan pengguna tidak membocorkan detail."""
    sesi = Sesi(
        Respons(400, {"error": {"message": "Model Not Exist"}})
    )
    klien = DeepSeek("kunci", "deepseek-chat", session=sesi)

    with pytest.raises(AssistantError) as info:
        klien.chat([{"role": "user", "content": "halo"}])

    assert "Model Not Exist" not in info.value.message
    assert "sibuk" in info.value.message.lower()


def test_kunci_ditolak_tidak_disebut_sibuk() -> None:
    """401 berarti kunci salah — bukan gangguan sementara, jangan bilang "sibuk".

    Terukur: kunci di ``.env`` dibalas "Authentication Fails ... invalid", lalu
    pengguna melihat "asisten sedang sibuk" dan menunggu tanpa akhir.
    """
    sesi = Sesi(
        Respons(401, {"error": {"message": "Authentication Fails"}})
    )
    klien = DeepSeek("kunci", "deepseek-flash", session=sesi)

    with pytest.raises(AssistantError) as info:
        klien.chat([{"role": "user", "content": "halo"}])

    assert "kunci api ditolak" in info.value.message.lower()
    assert "sibuk" not in info.value.message.lower()


def test_tanpa_api_key_menolak_lebih_awal() -> None:
    """Kunci kosong tidak boleh menghasilkan permintaan jaringan."""
    sesi = Sesi(_balasan("ok"))
    klien = DeepSeek("", "deepseek-flash", session=sesi)

    with pytest.raises(AssistantError):
        klien.chat([{"role": "user", "content": "halo"}])

    assert sesi.permintaan == []


def test_alasan_galat_dicatat_tanpa_isi_percakapan(caplog) -> None:
    """Log memuat alasan DeepSeek, tetapi tidak memuat pertanyaan pengguna (R-08-11)."""
    sesi = Sesi(Respons(400, {"error": {"message": "Model Not Exist"}}))
    klien = DeepSeek("kunci", "deepseek-chat", session=sesi)

    with caplog.at_level("WARNING"):
        with pytest.raises(AssistantError):
            klien.chat([{"role": "user", "content": "rahasia pribadi saya"}])

    teks = caplog.text
    assert "Model Not Exist" in teks
    assert "rahasia pribadi" not in teks
