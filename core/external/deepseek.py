"""Klien DeepSeek untuk asisten AI (PRD-08) dan fallback skill ambigu (PRD-07).

Diletakkan di ``core/`` karena dipakai oleh dua modul dan harus dapat diganti
dengan stub saat pengujian tanpa memanggil jaringan (R-08-13).

Kontrak ``DeepSeekClient.chat`` mengembalikan dict ``{"reply": str, "sumber": [...]}``
mengikuti bentuk hasil mesin BengkelBot yang menjadi acuan PRD-08 §10.

**Batas keamanan.** Modul ini tidak pernah mencatat isi percakapan ke log:
pertanyaan pengguna dapat memuat hal pribadi, dan R-08-11 melarangnya. Yang
dicatat hanya jenis kegagalan dan kode status.
"""

from __future__ import annotations

import logging
from typing import Protocol

from core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.deepseek.com"
DEFAULT_TIMEOUT = 20.0

# Retry hanya untuk kegagalan yang mungkin sementara (jaringan, 5xx). Timeout
# tidak diulang: pengguna sudah menunggu, dan percobaan kedua akan menunggu lagi.
MAX_RETRY = 1


class AssistantError(ExternalServiceError):
    """Kegagalan layanan AI dengan pesan yang aman ditampilkan ke pengguna.

    Turunan ``ExternalServiceError`` supaya handler global PRD-01 memetakannya
    menjadi 502 dengan bentuk galat yang sama seperti endpoint lain, tanpa route
    perlu menangkapnya satu per satu (R-08-10).

    Pesan asli pustaka HTTP dapat memuat URL, header, atau potongan jawaban;
    semuanya tidak boleh sampai ke layar.
    """

    code = "EXTERNAL_SERVICE_ERROR"
    message = "Layanan asisten sedang tidak dapat dihubungi. Coba lagi nanti."


class DeepSeekClient(Protocol):
    """Kontrak klien yang dipakai modul ``assistant`` dan ``cv``."""

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        timeout: float = DEFAULT_TIMEOUT,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> dict[str, object]:
        """Kirim percakapan dan kembalikan ``{"reply": "...", "sumber": [...]}``."""
        ...


class DeepSeek(DeepSeekClient):
    """Implementasi HTTP ke DeepSeek API dengan timeout eksplisit."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = BASE_URL,
        session=None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._session = session

    def _klien(self):
        if self._session is not None:
            return self._session
        import requests

        self._session = requests.Session()
        return self._session

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        timeout: float = DEFAULT_TIMEOUT,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> dict[str, object]:
        """Kirim percakapan ke DeepSeek dan kembalikan balasannya.

        ``temperature`` rendah karena jawaban harus berdasarkan konteks yang
        diberikan, bukan mengarang. ``max_tokens`` dibatasi agar jawaban ringkas
        dan biaya terkendali (§9).
        """
        if not self.api_key:
            raise AssistantError(
                "Asisten belum dikonfigurasi. Hubungi pengelola aplikasi."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        tajuk = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        percobaan = 0
        while True:
            try:
                respons = self._klien().post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=tajuk,
                    timeout=timeout,
                )
            except Exception as exc:  # noqa: BLE001 - pustaka melempar tipe berbeda
                # Hanya jenis galat yang dicatat, bukan isi percakapan.
                logger.warning("DeepSeek tidak dapat dihubungi (%s).", type(exc).__name__)
                if percobaan < MAX_RETRY:
                    percobaan += 1
                    continue
                raise AssistantError(
                    "Layanan asisten sedang tidak dapat dihubungi. Coba lagi nanti."
                ) from None

            if respons.status_code == 200:
                break

            # 5xx mungkin sementara; 4xx tidak akan berubah bila diulang.
            logger.warning("DeepSeek membalas %s.", respons.status_code)
            if respons.status_code >= 500 and percobaan < MAX_RETRY:
                percobaan += 1
                continue
            raise AssistantError(
                "Asisten sedang sibuk. Coba lagi beberapa saat lagi."
            )

        try:
            data = respons.json()
            balasan = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            logger.warning("Balasan DeepSeek tidak berbentuk seperti yang diharapkan.")
            raise AssistantError("Asisten mengirim balasan yang tidak dapat dibaca.") from None

        return {"reply": (balasan or "").strip(), "sumber": []}


def from_settings(settings) -> DeepSeekClient | None:
    """Klien sesuai konfigurasi, atau ``None`` bila tidak ada API key.

    ``None`` bukan kesalahan: aplikasi harus tetap berjalan tanpa AI, dan
    pemanggil menampilkan pesan yang jelas alih-alih gagal saat start.
    """
    if not getattr(settings, "deepseek_api_key", None):
        return None
    return DeepSeek(settings.deepseek_api_key, settings.deepseek_model)
