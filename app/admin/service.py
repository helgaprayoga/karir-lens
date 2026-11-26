"""Aturan bisnis panel admin (PRD-09).

Tempat tinggal: satu ringkasan agregat untuk kartu dan tabel (R-09-02), serta
penghapusan lowongan tidak valid. Panel admin tidak pernah menyentuh data CV
(R-09-09).

``service`` tidak mengenal Flask dan tidak menyentuh Supabase langsung: seluruh
akses data lewat ``repository`` (docs/ARCHITECTURE.md §4 aturan 2).
"""

from __future__ import annotations

from core.errors import NotFoundError
from core.pagination import build_meta, parse_page

from . import repository

DEFAULT_PAGE_SIZE = 20


def summary() -> dict:
    """Jumlah lowongan, pengguna, kategori, dan proses pembaruan terbaru.

    Bentuknya mengikuti kontrak PRD-F05 §4.1 yang sudah dipakai template
    ``admin/index.html``: ``total_jobs``, ``active_users``, ``total_clusters``,
    ``total_runs``, dan ``last_run_at``.
    """
    runs = repository.find_recent_runs(limit=1)
    return {
        "total_jobs": repository.count_jobs(),
        "active_users": repository.count_users(),
        "total_clusters": repository.count_clusters(),
        "total_runs": repository.count_runs(),
        "last_run_at": runs[0]["started_at"] if runs else None,
    }


def list_jobs(query: str | None = None, page=None, per_page=None) -> dict:
    """Daftar lowongan admin dengan pencarian dan pagination (R-09-03)."""
    halaman, per_halaman, offset = parse_page(
        {"page": page, "per_page": per_page}, default_per_page=DEFAULT_PAGE_SIZE
    )
    items = repository.find_jobs_page(query, offset, per_halaman)
    total = repository.count_jobs_matching(query)
    return {"items": items, "meta": build_meta(halaman, per_halaman, total)}


def list_users(page=None, per_page=None) -> dict:
    """Daftar pengguna dengan pagination, tanpa password atau CV (R-09-05)."""
    halaman, per_halaman, offset = parse_page(
        {"page": page, "per_page": per_page}, default_per_page=DEFAULT_PAGE_SIZE
    )
    items = repository.find_users_page(offset, per_halaman)
    return {"items": items, "meta": build_meta(halaman, per_halaman, repository.count_users())}


def list_runs(limit: int = 50) -> list[dict]:
    """Riwayat pembaruan; halaman admin menampilkan seluruhnya (R-09-06)."""
    return repository.find_recent_runs(limit=limit)


def list_clusters() -> list[dict]:
    return repository.find_clusters()


def remove_job(job_id: int) -> None:
    """Hapus lowongan tidak valid (R-09-04).

    ``NotFoundError`` dilempar bila ID tidak ada, supaya admin melihat 404 yang
    jujur alih-alih "berhasil" untuk baris yang sejak awal tidak ada.
    """
    if not repository.job_exists(job_id):
        raise NotFoundError("Lowongan tidak ditemukan.")
    repository.delete_job(job_id)
