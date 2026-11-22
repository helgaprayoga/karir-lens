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

# Kolom yang boleh diperbarui saat `source_url` yang sama diambil ulang.
# `source_url` dan `source_id` tidak ada di sini: keduanya identitas baris, dan
# mengubahnya berarti membuat baris baru secara diam-diam.
FIELD_DIPERBARUI = (
    "title", "company_name", "company_slug", "location", "employment_type",
    "description", "skills", "skills_source", "salary_min", "salary_max",
    "salary_currency",
    "salary_period", "source_job_id", "posted_at", "dedup_hash", "scraped_at",
)


def find_by_source_url(source_url: str) -> dict | None:
    """Baris ``jobs`` yang sudah ada untuk ``source_url`` ini, atau ``None``."""
    hasil = (
        core_db.get_db()
        .table(JOBS)
        .select("id,source_url")
        .eq("source_url", source_url)
        .limit(1)
        .execute()
    )
    baris = getattr(hasil, "data", None) or []
    return baris[0] if baris else None


def exists(source_url: str) -> bool:
    """True bila ``source_url`` sudah tersimpan (R-02-09)."""
    return find_by_source_url(source_url) is not None


def insert(job: dict) -> bool:
    """Simpan satu lowongan baru. False bila ``source_url`` sudah ada."""
    if exists(job["source_url"]):
        return False
    core_db.get_db().table(JOBS).insert(job).execute()
    return True


def find_duplicate(job: dict) -> dict | None:
    """Baris lain dengan ``dedup_hash`` sama, dari **sumber berbeda** (R-03-09).

    Satu sumber biasanya tidak menduplikasi dirinya sendiri: dua lowongan dari
    Dealls dengan judul dan perusahaan sama biasanya memang dua lowongan
    berbeda (satu perusahaan, dua lokasi). Tetapi Remotive **terbukti** memuat
    lowongan kembar — dua ID berbeda, judul dan perusahaan identik
    ("Content Reviewer - United States" 2091166 dan 2091177). Karena itu
    pencarian tidak menyaring per sumber.

    Yang disaring hanya ``source_url`` yang sama, karena itu baris yang sama,
    bukan duplikat.
    """
    dedup_hash = job.get("dedup_hash")
    if not dedup_hash:
        return None

    hasil = (
        core_db.get_db()
        .table(JOBS)
        .select("id,source_url,source_id,dedup_hash")
        .eq("dedup_hash", dedup_hash)
        .limit(5)
        .execute()
    )
    for baris in getattr(hasil, "data", None) or []:
        if baris.get("source_url") != job.get("source_url"):
            return baris
    return None


def _tandai_duplikat(job: dict, induk: dict) -> dict:
    """Tambahkan penanda duplikat pada baris yang akan disimpan."""
    return {
        **job,
        "duplicate_of": induk.get("id"),
        "dedup_source": induk.get("source_url"),
    }


def upsert(job: dict) -> str:
    """Simpan lowongan secara idempoten (R-03-09, R-03-12).

    Kembalian:
      ``"inserted"``  baris baru
      ``"updated"``   baris dengan ``source_url`` sama sudah ada, isinya diperbarui
      ``"duplicate"`` ``dedup_hash`` sama dengan baris sumber lain; disimpan
                      dengan penanda, bukan digabung diam-diam (R-03-10)
    """
    lama = find_by_source_url(job["source_url"])

    if lama is not None:
        perubahan = {k: v for k, v in job.items() if k in FIELD_DIPERBARUI}
        if not perubahan:
            return "updated"
        core_db.get_db().table(JOBS).update(perubahan).eq("id", lama["id"]).execute()
        return "updated"

    induk = find_duplicate(job)
    if induk is not None:
        core_db.get_db().table(JOBS).insert(_tandai_duplikat(job, induk)).execute()
        return "duplicate"

    core_db.get_db().table(JOBS).insert(job).execute()
    return "inserted"


def insert_many(rows: list[dict]) -> dict[str, int]:
    """Simpan sekumpulan baris; kembalikan jumlah per hasil.

    Duplikat ``source_url`` di dalam satu eksekusi disaring lebih dulu: kolomnya
    unik di database, dan mengirim dua baris dengan URL sama dalam satu batch
    akan menggagalkan seluruh batch.
    """
    unik: dict[str, dict] = {}
    for baris in rows:
        url = baris.get("source_url")
        if url and url not in unik:
            unik[url] = baris

    hasil = {"inserted": 0, "updated": 0, "duplicate": 0}
    for baris in unik.values():
        hasil[upsert(baris)] += 1
    return hasil


def insert_or_update(job: dict) -> str:
    """Nama lama; sekarang meneruskan ke :func:`upsert`."""
    return upsert(job)


def hapus_di_luar(
    url_dipertahankan: set[str], abaikan_sumber: set[str] | None = None
) -> int:
    """Hapus baris yang ``source_url``-nya tidak ada di himpunan (R-02-11).

    Dipakai oleh ``--replace``: hasil pengambilan terbaru menjadi daftar
    kebenaran, dan baris lama yang tidak muncul lagi dianggap sudah tidak
    tersedia.

    Tiga penjagaan, semuanya disengaja:

    1. ``url_dipertahankan`` kosong berarti **tidak menghapus apa pun**. Daftar
       kosong hampir selalu berarti pengambilan gagal, bukan "semua lowongan
       hilang dari internet".
    2. ``abaikan_sumber`` berisi sumber yang gagal pada eksekusi ini; lowongan
       miliknya tidak ikut dihapus, karena kita tidak punya dasar menyatakan
       lowongan itu sudah tidak ada.
    3. Penghapusan per batch memakai ``in_`` pada ``source_url``, bukan
       menghapus seluruh tabel lalu memasukkannya kembali — ``saved_jobs``
       menunjuk ke ``jobs.id``, dan menghapus lalu memasukkan ulang akan
       memutus bookmark pengguna.

    Baris mengembalikan jumlah yang dihapus.
    """
    if not url_dipertahankan:
        return 0

    klien = core_db.get_db()
    dihapus = 0
    sumber_dilewati = set(abaikan_sumber or ())

    peta_sumber = {
        row["name"]: row["id"]
        for row in (klien.table(SOURCES).select("id,name").execute().data or [])
    }
    id_dilewati = {peta_sumber[nama] for nama in sumber_dilewati if nama in peta_sumber}

    while True:
        baris = (
            klien.table(JOBS)
            .select("id,source_url,source_id")
            .limit(500)
            .execute()
            .data
            or []
        )
        if not baris:
            break

        buang = [
            r["id"]
            for r in baris
            if r.get("source_url") not in url_dipertahankan
            and r.get("source_id") not in id_dilewati
        ]
        if not buang:
            # Tidak ada yang perlu dibuang pada halaman ini; berhenti agar tidak
            # berputar selamanya membaca 500 baris yang sama.
            break

        for mulai in range(0, len(buang), 100):
            potong = buang[mulai : mulai + 100]
            klien.table(JOBS).delete().in_("id", potong).execute()
            dihapus += len(potong)

    return dihapus
