"""Aturan bisnis CV dan rekomendasi (PRD-07).

Tempat tinggal: validasi tipe/ukuran berkas, urutan ekstraksi lokal sebelum AI,
penghapusan berkas sementara di blok ``finally``, dan penyusunan alasan
rekomendasi. Berkas dan teks CV tidak boleh disimpan maupun dicatat ke log
(R-07-08).
"""

from __future__ import annotations

ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)


def extract_and_suggest(file_storage) -> list[str]:
    """Ekstrak skill dari CV lalu hapus berkas sementara (R-07-01..R-07-05)."""
    raise NotImplementedError("Diisi pada PRD-07.")


def get_recommendations(user_id: int, limit: int = 10) -> dict:
    """Rekomendasi berbasis skill terkonfirmasi, tanpa AI per permintaan (R-07-09..R-07-11)."""
    raise NotImplementedError("Diisi pada PRD-07.")
