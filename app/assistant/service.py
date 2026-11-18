"""Aturan bisnis asisten AI (PRD-08).

Tempat tinggal: penyusunan konteks dari data aplikasi, larangan memakai isi CV
mentah (R-08-04), penolakan/klarifikasi saat konteks lemah (R-08-07), dan rate
limit per pengguna (R-08-09). Tidak boleh mengimpor ``flask``.
"""

from __future__ import annotations


def build_context(question: str, user_id: int) -> dict:
    """Konteks dari lowongan, cluster, statistik gaji, dan skill terkonfirmasi (R-08-02)."""
    raise NotImplementedError("Diisi pada PRD-08.")


def ask(question: str, user_id: int) -> dict:
    """Jawaban asisten yang hanya merujuk data aplikasi (R-08-03..R-08-07)."""
    raise NotImplementedError("Diisi pada PRD-08.")
