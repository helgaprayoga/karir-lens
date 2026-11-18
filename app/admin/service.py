"""Aturan bisnis panel admin (PRD-09).

Tempat tinggal: satu ringkasan agregat untuk kartu dan tabel (R-09-02), serta
penghapusan lowongan tidak valid. Panel admin tidak pernah menyentuh data CV
(R-09-09).
"""

from __future__ import annotations


def summary() -> dict:
    """Jumlah lowongan, pengguna, dan proses pembaruan terbaru."""
    raise NotImplementedError("Diisi pada PRD-09.")


def remove_job(job_id: int) -> None:
    raise NotImplementedError("Diisi pada PRD-09.")
