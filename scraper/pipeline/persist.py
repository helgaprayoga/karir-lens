"""Penyimpanan idempoten ke tabel ``jobs`` dan ``scrape_runs`` (PRD-02 §3.1).

Satu-satunya berkas di ``scraper/`` yang boleh memakai ``core/db.py``.

PRD-02 menyimpan baris baru saja; pembaruan dan ``dedup_hash`` dikerjakan
PRD-03. Karena itu ``insert_or_update`` di sini sengaja sederhana: cek
keberadaan ``source_url``, lalu simpan bila belum ada (R-02-09).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core import db as core_db

logger = logging.getLogger(__name__)

JOBS = "jobs"
RUNS = "scrape_runs"
SOURCES = "sources"

# Status yang dipakai kolom `scrape_runs.status` (PRD-02 §4.2, PRD-F05 §4.1).
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_from_settings(settings=None) -> None:
    """Sambungkan ``core/db`` ke Supabase dari konfigurasi environment.

    Aplikasi web melakukan ini di ``create_app``. Pipeline berjalan di luar
    Flask (docs/ARCHITECTURE.md §4 aturan 5), jadi ia harus melakukannya
    sendiri — tanpa ini setiap penulisan gagal dengan "Koneksi Supabase belum
    dikonfigurasi" padahal ``.env`` sudah benar.

    Tidak membuka koneksi: ``core_db.configure`` hanya menyimpan kredensial,
    client dibuat lazy pada pemakaian pertama.
    """
    from core.config import Settings

    settings = settings or Settings.from_env()
    core_db.configure(settings.supabase_url, settings.supabase_key)


# --- sources -------------------------------------------------------------

def ensure_source(name: str, base_url: str) -> int | None:
    """Pastikan baris ``sources`` ada; kembalikan id-nya.

    Tabel ``sources`` sudah diisi migrasi? Tidak — migrasi hanya membuat
    tabelnya. Runner yang mengisi baris per sumber pada eksekusi pertama.
    """
    db = core_db.get_db()
    hasil = db.table(SOURCES).select("id").eq("name", name).limit(1).execute()
    baris = getattr(hasil, "data", None) or []
    if baris:
        return baris[0].get("id")

    dibuat = db.table(SOURCES).insert({"name": name, "base_url": base_url}).execute()
    data = getattr(dibuat, "data", None) or []
    return data[0].get("id") if data else None


def touch_source(source_id: int | None) -> None:
    """Catat waktu pengambilan terakhir pada ``sources``."""
    if source_id is None:
        return
    core_db.get_db().table(SOURCES).update({"last_scraped_at": _now()}).eq(
        "id", source_id
    ).execute()


# --- scrape_runs ---------------------------------------------------------

def start_run(source_id: int | None) -> int | None:
    """Buat baris ``scrape_runs`` berstatus ``running`` (R-02-06)."""
    baris = {
        "source_id": source_id,
        "started_at": _now(),
        "status": STATUS_RUNNING,
        "jobs_found": 0,
        "jobs_inserted": 0,
        "jobs_updated": 0,
    }
    hasil = core_db.get_db().table(RUNS).insert(baris).execute()
    data = getattr(hasil, "data", None) or []
    return data[0].get("id") if data else None


def finish_run(
    run_id: int | None,
    *,
    status: str,
    jobs_found: int = 0,
    jobs_inserted: int = 0,
    jobs_updated: int = 0,
    error_message: str | None = None,
) -> None:
    """Perbarui baris ``scrape_runs`` menjadi status akhir (R-02-06, R-02-08)."""
    if run_id is None:
        return
    core_db.get_db().table(RUNS).update(
        {
            "finished_at": _now(),
            "status": status,
            "jobs_found": jobs_found,
            "jobs_inserted": jobs_inserted,
            "jobs_updated": jobs_updated,
            "error_message": error_message,
        }
    ).eq("id", run_id).execute()


# --- jobs ----------------------------------------------------------------

def exists(source_url: str) -> bool:
    """True bila ``source_url`` sudah tersimpan (R-02-09)."""
    hasil = (
        core_db.get_db()
        .table(JOBS)
        .select("id")
        .eq("source_url", source_url)
        .limit(1)
        .execute()
    )
    return bool(getattr(hasil, "data", None))


def insert(job: dict) -> bool:
    """Simpan satu lowongan baru. False bila ``source_url`` sudah ada."""
    if exists(job["source_url"]):
        return False
    core_db.get_db().table(JOBS).insert(job).execute()
    return True


def insert_many(rows: list[dict]) -> int:
    """Simpan sekumpulan baris; kembalikan jumlah yang benar-benar baru.

    Duplikat di dalam satu eksekusi disaring lebih dulu: ``source_url`` unik di
    database, dan mengirim dua baris dengan URL sama dalam satu batch akan
    menggagalkan seluruh batch (acceptance §5: tidak ada duplikasi).
    """
    unik: dict[str, dict] = {}
    for baris in rows:
        url = baris.get("source_url")
        if url and url not in unik:
            unik[url] = baris

    tersimpan = 0
    for url, baris in unik.items():
        if insert(baris):
            tersimpan += 1
    return tersimpan


def insert_or_update(job: dict) -> str:
    """Simpan lowongan; kembalikan ``"inserted"`` atau ``"existing"``.

    Pembaruan sungguhan (dan ``dedup_hash``) datang di PRD-03. Nama fungsi
    dipertahankan agar pemanggilnya tidak berubah saat itu terjadi.
    """
    return "inserted" if insert(job) else "existing"
