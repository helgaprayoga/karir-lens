"""Satu-satunya orkestrator ingestion (PRD-02 §9).

Adapter tidak saling memanggil. ``runner.run`` membuat ``scrape_runs``, menjalankan
adapter yang diminta, lalu mencatat hasilnya. Kegagalan satu sumber tidak
menghentikan sumber lain (R-02-08).

Isolasi kegagalan diadaptasi dari ``run()`` pada proyek referensi
(``Praktik Scripting/Pertemuan 9/scraper.py``): ``RobotsDisallowedError``
menandai sumber itu ``skipped`` dan lanjut; galat lain menandainya ``failed``
dan lanjut. Perbedaan penting: di sini TIDAK ada `raise` yang menghentikan
seluruh putaran — referensi menghentikan semua sumber saat robots menolak, dan
itu bertentangan dengan R-02-08 yang berlaku per sumber.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from .adapters.base import RawJob
from .adapters.registry import ADAPTERS
from .errors import RobotsDisallowedError, ScrapeError

logger = logging.getLogger(__name__)


@dataclass
class SourceOutcome:
    """Hasil satu sumber dalam satu eksekusi."""

    source: str
    status: str = "failed"
    jobs_found: int = 0
    jobs_inserted: int = 0
    error_message: str | None = None
    jobs: list[RawJob] = field(default_factory=list)


def _outcome_for(source: str, max_pages: int, dry_run: bool, with_detail: bool = False) -> SourceOutcome:
    """Jalankan satu adapter secara terisolasi; tidak pernah melempar."""
    from . import pipeline

    hasil = SourceOutcome(source=source)
    adapter_cls = ADAPTERS[source]
    adapter = adapter_cls()

    mulai = time.monotonic()
    try:
        jobs = list(adapter.iter_jobs(max_pages=max_pages, with_detail=with_detail))
    except RobotsDisallowedError as exc:
        hasil.status = "skipped"
        hasil.error_message = str(exc)
        logger.warning("%s: dilewati — %s", source, exc)
        return hasil
    except ScrapeError as exc:
        hasil.status = "failed"
        hasil.error_message = str(exc)
        logger.error("%s: gagal — %s", source, exc)
        return hasil
    except Exception as exc:  # adapter pihak ketiga bisa melempar apa saja
        hasil.status = "failed"
        hasil.error_message = f"{type(exc).__name__}: {exc}"
        logger.exception("%s: galat tak terduga", source)
        return hasil
    finally:
        adapter.http.close()

    durasi = time.monotonic() - mulai
    hasil.jobs = jobs
    hasil.jobs_found = len(jobs)

    if dry_run:
        hasil.status = "success" if jobs else "failed"
        logger.info(
            "%s: %d lowongan dalam %.1f detik (dry-run, tidak disimpan)",
            source, hasil.jobs_found, durasi,
        )
        return hasil

    if not jobs:
        # Tidak ada data sama sekali bukan keberhasilan: bisa berarti struktur
        # halaman berubah dan parser tidak menemukan apa pun.
        hasil.status = "failed"
        hasil.error_message = "Tidak ada lowongan yang berhasil diparse."
        return hasil

    try:
        hasil.jobs_inserted = pipeline.persist_run(source, jobs)
        hasil.status = "success"
    except Exception as exc:
        hasil.status = "partial"
        hasil.error_message = f"Gagal menyimpan sebagian data: {exc}"
        logger.exception("%s: gagal menyimpan", source)

    logger.info(
        "%s: %d ditemukan, %d baru, %.1f detik",
        source, hasil.jobs_found, hasil.jobs_inserted, durasi,
    )
    return hasil


def run(
    source: str = "all",
    max_pages: int = 5,
    dry_run: bool = False,
    with_detail: bool = False,
) -> int:
    """Jalankan ingestion; kembalikan kode keluar (0 sukses sebagian, 1 semua gagal).

    R-02-10: keluar 1 hanya bila SEMUA sumber gagal. Satu sumber berhasil sudah
    cukup untuk keluar 0, karena data parsial tetap berguna.

    ``with_detail`` mengambil halaman detail per lowongan (deskripsi dan skill).
    Bawaannya mati: satu halaman daftar berarti puluhan permintaan tambahan, dan
    itu tidak boleh terjadi tanpa diminta.
    """
    from . import pipeline

    sumber = list(ADAPTERS) if source == "all" else [source]
    if source != "all" and source not in ADAPTERS:
        logger.error("Sumber tidak dikenal: %s", source)
        return 1

    if not dry_run:
        # Pipeline berjalan di luar Flask; koneksi Supabase harus disiapkan
        # sendiri sebelum ada yang mencoba menulis.
        pipeline.persist.configure_from_settings()

    logger.info(
        "Mulai ingestion: %s (max_pages=%d, dry_run=%s, detail=%s)",
        ", ".join(sumber), max_pages, dry_run, with_detail,
    )

    hasil: list[SourceOutcome] = []
    for nama in sumber:
        hasil.append(
            _outcome_for(nama, max_pages=max_pages, dry_run=dry_run, with_detail=with_detail)
        )
        if not dry_run:
            pipeline.record_outcome(hasil[-1])

    berhasil = [h for h in hasil if h.status in {"success", "partial"}]
    for h in hasil:
        logger.info("  %-9s %-8s ditemukan=%d baru=%d", h.source, h.status, h.jobs_found, h.jobs_inserted)

    return 0 if berhasil else 1
