"""Pipeline pengolahan data setelah parse.

Alur PRD-03: ``RawJob`` -> ``normalize()`` -> ``dedup.compute_hash()`` ->
``persist.upsert()``. Fungsi di modul ini adalah satu-satunya jalan dari
``runner`` ke database, sehingga orkestrasi tidak perlu tahu aturan normalisasi.

Ringkas:
  - ``persist_run`` menyimpan satu sumber dan mengembalikan hitungannya.
  - ``record_outcome`` mencatat ke ``scrape_runs``, termasuk ``jobs_updated``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import persist
from .dedup import compute_hash
# Diimpor dengan alias: `from .normalize import normalize` akan menimpa atribut
# submodul `normalize` pada paket ini dengan fungsinya, sehingga
# `pipeline.normalize.normalize()` gagal dengan AttributeError.
from .normalize import normalize as normalize_job

logger = logging.getLogger(__name__)


def _baris_dari(job, source_id: int | None = None) -> dict:
    """``RawJob`` -> baris ``jobs`` siap simpan (R-03-01).

    Normalisasi dilakukan di sini, bukan di adapter: adapter hanya memindahkan
    data mentah, dan aturan format harus sama untuk semua sumber.
    """
    mentah = job.as_row(source_id=source_id)
    baris = normalize_job(mentah)
    baris["dedup_hash"] = compute_hash(baris)
    baris["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return baris


def persist_run(source: str, jobs: list) -> dict[str, int]:
    """Simpan hasil satu sumber; kembalikan ``{inserted, updated, duplicate}``.

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


def persist_hapus_di_luar(url_dipertahankan: set[str], abaikan_sumber: set[str] | None = None) -> int:
    """Teruskan ke :func:`persist.hapus_di_luar` (dipakai ``--replace``)."""
    return persist.hapus_di_luar(url_dipertahankan, abaikan_sumber=abaikan_sumber)


def record_outcome(outcome) -> None:
    """Catat satu sumber ke ``scrape_runs`` (R-02-06 s.d. R-02-08, R-03-13).

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
            jobs_updated=getattr(outcome, "jobs_updated", 0),
            error_message=outcome.error_message,
        )
        persist.touch_source(source_id)
    except Exception as exc:
        logger.error(
            "Gagal mencatat scrape_runs untuk %s: %s", outcome.source, exc
        )
