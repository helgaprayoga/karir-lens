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

# Batas atas ketika `--pages 0` (ambil sampai habis). Dealls punya 134 halaman
# saat diperiksa; 300 memberi ruang tanpa membuka loop tak berujung.
MAX_PAGES_ALL = 300

# Ambang pengaman `--replace`: penghapusan dibatalkan bila lowongan yang
# terkumpul hari ini kurang dari 60% isi database. Penurunan sebesar itu hampir
# selalu berarti pengambilan hanya berhasil sebagian, bukan lowongan yang
# benar-benar hilang.
MIN_REPLACE_RATIO = 0.6


@dataclass
class SourceOutcome:
    """Hasil satu sumber dalam satu eksekusi."""

    source: str
    status: str = "failed"
    jobs_found: int = 0
    jobs_inserted: int = 0
    jobs_updated: int = 0
    jobs_duplicate: int = 0
    # Jumlah lowongan non-IT yang disaring. Dilaporkan agar "sumbernya cuma
    # segini" dapat dibedakan dari "memang segini yang IT".
    jobs_filtered: int = 0
    error_message: str | None = None
    jobs: list[RawJob] = field(default_factory=list)


def _outcome_for(
    source: str,
    max_pages: int,
    dry_run: bool,
    with_detail: bool = False,
    tech_only: bool = True,
) -> SourceOutcome:
    """Jalankan satu adapter secara terisolasi; tidak pernah melempar.

    ``max_pages=0`` berarti ambil sampai daftar habis: adapter berhenti sendiri
    ketika sebuah halaman tidak berisi item baru.
    """
    from . import pipeline

    hasil = SourceOutcome(source=source)
    adapter_cls = ADAPTERS[source]
    adapter = adapter_cls()
    adapter.tech_only = tech_only

    # 0 berarti "sampai habis"; batas atas yang longgar mencegah loop tak
    # berujung bila sebuah sumber terus mengembalikan halaman yang sama
    # (Remotive `?page=N` pernah berperilaku begitu).
    halaman = max_pages if max_pages and max_pages > 0 else MAX_PAGES_ALL

    mulai = time.monotonic()
    try:
        jobs = list(adapter.iter_jobs(max_pages=halaman, with_detail=with_detail))
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
    hasil.jobs_filtered = adapter.filtered_out

    if dry_run:
        hasil.status = "success" if jobs else "failed"
        logger.info(
            "%s: %d lowongan IT dalam %.1f detik (%d non-IT disaring, dry-run, tidak disimpan)",
            source, hasil.jobs_found, durasi, hasil.jobs_filtered,
        )
        return hasil

    if not jobs:
        # Tidak ada data sama sekali bukan keberhasilan: bisa berarti struktur
        # halaman berubah dan parser tidak menemukan apa pun.
        hasil.status = "failed"
        hasil.error_message = "Tidak ada lowongan yang berhasil diparse."
        return hasil

    try:
        hasil_data = pipeline.persist_run(source, jobs)
        hasil.jobs_inserted = hasil_data.get("inserted", 0)
        hasil.jobs_updated = hasil_data.get("updated", 0)
        hasil.jobs_duplicate = hasil_data.get("duplicate", 0)
        hasil.status = "success"
    except Exception as exc:
        hasil.status = "partial"
        hasil.error_message = f"Gagal menyimpan sebagian data: {exc}"
        logger.exception("%s: gagal menyimpan", source)

    logger.info(
        "%s: %d ditemukan, %d baru, %d diperbarui, %d duplikat, %.1f detik",
        source, hasil.jobs_found, hasil.jobs_inserted, hasil.jobs_updated,
        hasil.jobs_duplicate, durasi,
    )
    return hasil


def run(
    source: str = "all",
    max_pages: int = 0,
    dry_run: bool = False,
    with_detail: bool = False,
    tech_only: bool = True,
    replace: bool = False,
) -> int:
    """Jalankan ingestion; kembalikan kode keluar (0 sukses sebagian, 1 semua gagal).

    R-02-10: keluar 1 hanya bila SEMUA sumber gagal. Satu sumber berhasil sudah
    cukup untuk keluar 0, karena data parsial tetap berguna.

    ``with_detail`` mengambil halaman detail per lowongan (deskripsi dan skill).
    Bawaannya mati: satu halaman daftar berarti puluhan permintaan tambahan, dan
    itu tidak boleh terjadi tanpa diminta.

    ``max_pages=0`` (bawaan CLI) mengambil sampai daftar habis.

    ``replace`` mengganti isi tabel ``jobs`` dengan hasil eksekusi ini. Urutannya
    sengaja: **pengambilan dulu, penghapusan kemudian**. Bila pengambilan gagal
    atau tidak menghasilkan satu lowongan pun, data lama dibiarkan utuh —
    kehilangan seluruh data karena satu kegagalan jaringan jauh lebih buruk
    daripada data yang belum segar.
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
        "Mulai ingestion: %s (max_pages=%s, dry_run=%s, detail=%s, tech_only=%s, replace=%s)",
        ", ".join(sumber),
        max_pages if max_pages else "semua",
        dry_run, with_detail, tech_only, replace,
    )

    hasil: list[SourceOutcome] = []
    for nama in sumber:
        hasil.append(
            _outcome_for(
                nama,
                max_pages=max_pages,
                dry_run=dry_run,
                with_detail=with_detail,
                tech_only=tech_only,
            )
        )
        if not dry_run:
            # Hitungan `scrape_runs` dicatat setelah penyimpanan, supaya
            # `jobs_updated` dari eksekusi ini ikut terbaca.
            pipeline.record_outcome(hasil[-1])

    berhasil = [h for h in hasil if h.status in {"success", "partial"}]
    for h in hasil:
        logger.info(
            "  %-9s %-8s IT=%d disaring=%d baru=%d diperbarui=%d duplikat=%d",
            h.source, h.status, h.jobs_found, h.jobs_filtered,
            h.jobs_inserted, h.jobs_updated, h.jobs_duplicate,
        )

    if replace and not dry_run:
        _replace_if_successful(hasil, berhasil)

    return 0 if berhasil else 1


def _replace_if_successful(
    hasil: list[SourceOutcome], berhasil: list[SourceOutcome]
) -> None:
    """Hapus baris yang tidak ada di hasil eksekusi ini.

    Yang dihapus hanya ``source_url`` yang **tidak** muncul pada pengambilan
    ini — bukan mengosongkan tabel. Dengan begitu:
      - Lowongan yang masih ada tetap utuh beserta ``saved_jobs`` yang menunjuk
        ke sana (menghapus lalu memasukkan ulang akan memutus bookmark).
      - Bila sebuah sumber gagal, lowongannya tidak ikut terhapus, karena kita
        tidak punya dasar untuk menyatakan lowongan itu sudah tidak tersedia.

    **Ambang pengaman.** Bila hasil hari ini jauh lebih kecil daripada yang
    tersimpan, penghapusan dibatalkan. Penyebabnya bukan lowongan yang benar-benar
    hilang, melainkan pengambilan yang setengah berhasil — situs membatasi
    jumlah halaman, atau struktur berubah di tengah jalan. Menghapus ratusan
    baris karena satu kegagalan sementara jauh lebih mahal daripada
    mempertahankan data yang belum segar sehari lagi.
    """
    from . import pipeline

    gagal = {h.source for h in hasil if h.status not in {"success", "partial"}}
    if gagal:
        logger.warning(
            "Ganti data dilewati untuk sumber yang gagal (%s); datanya dibiarkan.",
            ", ".join(sorted(gagal)),
        )

    url_terbaru = {
        job.source_url
        for outcome in berhasil
        for job in outcome.jobs
        if job.source_url
    }
    if not url_terbaru:
        logger.warning("Ganti data dilewati: tidak ada satu pun lowongan baru.")
        return

    tersimpan = pipeline.persist_hitung_tersimpan()
    if tersimpan:
        rasio = len(url_terbaru) / tersimpan
        if rasio < MIN_REPLACE_RATIO:
            logger.warning(
                "Ganti data DIBATALKAN: hasil hari ini %d lowongan, sementara "
                "database berisi %d (%.0f%%, di bawah ambang %.0f%%). "
                "Kemungkinan pengambilan hanya berhasil sebagian.",
                len(url_terbaru),
                tersimpan,
                rasio * 100,
                MIN_REPLACE_RATIO * 100,
            )
            return

    dihapus = pipeline.persist_hapus_di_luar(url_terbaru, abaikan_sumber=gagal)
    logger.info("Ganti data: %d lowongan lama dihapus, %d dipertahankan.", dihapus, len(url_terbaru))
