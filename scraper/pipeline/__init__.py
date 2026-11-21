"""Pipeline pengolahan data setelah parse.

PRD-02 hanya butuh dua operasi di sini: menyimpan hasil satu sumber dan
mencatatnya ke ``scrape_runs``. Normalisasi mendalam dan ``dedup_hash``
dikerjakan PRD-03 di ``normalize.py`` dan ``dedup.py``.

Fungsi di modul ini adalah satu-satunya jalan dari ``runner`` ke database,
sehingga PRD-03 cukup mengubah isi ``simpan`` tanpa menyentuh orkestrasi.
"""

from __future__ import annotations

import logging

from . import persist

logger = logging.getLogger(__name__)


def _baris_dari(job, source_id: int | None = None) -> dict:
    """``RawJob`` -> baris ``jobs``.

    PRD-02 memakai ``RawJob.as_row()`` apa adanya. PRD-03 akan mengganti ini
    dengan ``normalize()`` + ``dedup.compute_hash()``.
    """
    return job.as_row(source_id=source_id)


def persist_run(source: str, jobs: list) -> int:
    """Simpan hasil satu sumber; kembalikan jumlah baris baru.

    ``source_id`` dicari dari tabel ``sources`` lebih dulu: kolom itu yang
    menghubungkan setiap lowongan ke asalnya, dan tanpa nilainya baris tersimpan
    dengan relasi kosong.
    """
    from ..adapters.registry import ADAPTERS

    adapter_cls = ADAPTERS.get(source)
    base_url = adapter_cls.base_url if adapter_cls else ""
    source_id = persist.ensure_source(source, base_url)

    baris = []
    for job in jobs:
        try:
            baris.append(_baris_dari(job, source_id))
        except Exception:
            logger.warning("Melewati satu lowongan %s yang tidak dapat dipetakan", source)
    return persist.insert_many(baris)


def record_outcome(outcome) -> None:
    """Catat satu sumber ke ``scrape_runs`` (R-02-06 s.d. R-02-08).

    ``source_id`` dicari atau dibuat lebih dulu. Bila tabel tidak dapat
    dihubungi, kegagalannya dilaporkan tetapi tidak menghentikan sumber lain —
    mencatat riwayat bukan alasan menggagalkan pengambilan data.
    """
    from ..adapters.registry import ADAPTERS

    adapter_cls = ADAPTERS.get(outcome.source)
    base_url = adapter_cls.base_url if adapter_cls else ""

    try:
        source_id = persist.ensure_source(outcome.source, base_url)
        run_id = persist.start_run(source_id)
        persist.finish_run(
            run_id,
            status=outcome.status,
            jobs_found=outcome.jobs_found,
            jobs_inserted=outcome.jobs_inserted,
            error_message=outcome.error_message,
        )
        persist.touch_source(source_id)
    except Exception as exc:
        logger.error(
            "Gagal mencatat scrape_runs untuk %s: %s", outcome.source, exc
        )
