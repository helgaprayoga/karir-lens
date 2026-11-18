"""Klien DeepSeek untuk asisten AI (PRD-08) dan fallback skill ambigu (PRD-07).

Diletakkan di ``core/`` karena dipakai oleh dua modul dan harus dapat diganti
dengan stub saat pengujian tanpa memanggil jaringan (R-08-13).

Kontrak ``DeepSeekClient.chat`` mengembalikan dict ``{"reply": str}`` mengikuti
bentuk hasil mesin BengkelBot yang menjadi acuan PRD-08 §10.

Implementasi nyata dibuat pada PRD-08.
"""

from __future__ import annotations

from typing import Protocol


class DeepSeekClient(Protocol):
    """Kontrak klien yang dipakai modul ``assistant`` dan ``cv``."""

    def chat(self, messages: list[dict[str, str]], *, timeout: float = 20.0) -> dict[str, object]:
        """Kirim percakapan dan kembalikan ``{"reply": "...", "sumber": [...]}``."""
        ...


class DeepSeek(DeepSeekClient):
    """Implementasi HTTP ke DeepSeek API dengan timeout eksplisit."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: list[dict[str, str]], *, timeout: float = 20.0) -> dict[str, object]:
        raise NotImplementedError("Diisi pada PRD-08 (integrasi DeepSeek).")
