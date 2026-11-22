"""Akses data untuk asisten AI (PRD-08).

Modul ini membaca ``jobs``, ``clusters``, dan ``ai_usage`` lewat repository
miliknya sendiri (docs/ARCHITECTURE.md §4 aturan 2), bukan lewat repository
modul lain.

Konteks dibatasi kolomnya: hanya yang dibutuhkan untuk menjawab, karena setiap
byte ikut ke prompt dan memengaruhi biaya serta latensi (§9).
"""

from __future__ import annotations

from datetime import datetime, timezone

from core import db as core_db

JOBS = "jobs"
CLUSTERS = "clusters"
SAVED_JOBS = "saved_jobs"
USER_SKILLS = "user_skills"
USAGE = "ai_usage"
SOURCES = "sources"


def _client():
    return core_db.get_db()


def search_jobs(kata: list[str], limit: int = 8) -> list[dict]:
    """Lowongan yang cocok dengan kata kunci pertanyaan (R-08-02, R-08-06).

    Pencocokan sengaja sederhana dan dapat dijelaskan: kata dari pertanyaan
    dicari pada judul, perusahaan, dan skill. Ini bukan pencarian semantik —
    asisten yang menjawab dari daftar lowongan yang salah lebih buruk daripada
    asisten yang mengaku tidak menemukan.

    ``source_url`` selalu ikut, karena tautan yang ditampilkan harus berasal
    dari data tersimpan (R-08-06).
    """
    kata = [k.strip().lower() for k in (kata or []) if len(k.strip()) > 2]
    if not kata:
        return find_latest_jobs(limit)

    klausa = []
    for k in kata[:4]:
        aman = k.replace(",", " ").replace("(", " ").replace(")", " ")
        klausa.append(f"title.ilike.%{aman}%")
        klausa.append(f"company_name.ilike.%{aman}%")
        klausa.append(f"skills.cs.{{{aman}}}")

    hasil = (
        _client()
        .table(JOBS)
        .select("id,title,company_name,location,employment_type,skills,"
                "salary_min,salary_max,salary_currency,salary_period,"
                "source_id,source_url,posted_at,cluster_id")
        .or_(",".join(klausa))
        .limit(limit)
        .execute()
        .data
        or []
    )
    # Hasil kosong berarti tidak ada yang cocok; jangan diisi lowongan acak,
    # karena asisten akan menyebutnya "relevan" padahal bukan.
    return hasil


def find_latest_jobs(limit: int = 8) -> list[dict]:
    """Lowongan terbaru, dipakai sebagai pijakan bila tidak ada yang persis cocok.

    Pertanyaan seperti "lowongan apa saja yang ada?" tidak punya kata kunci
    yang berguna, jadi konteksnya adalah daftar terbaru.
    """
    return (
        _client()
        .table(JOBS)
        .select("id,title,company_name,location,employment_type,skills,"
                "salary_min,salary_max,salary_currency,salary_period,"
                "source_id,source_url,posted_at,cluster_id")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def find_clusters() -> list[dict]:
    """Label dan kata kunci kategori (R-08-02)."""
    return (
        _client().table(CLUSTERS).select("id,label,keywords").order("id").execute().data
        or []
    )


def find_jobs_with_salary(limit: int = 400) -> list[dict]:
    """Gaji faktual untuk dihitung statistiknya.

    Hanya kolom gaji: statistik tidak butuh judul maupun deskripsi.
    """
    return (
        _client()
        .table(JOBS)
        .select("salary_min,salary_max,salary_currency,salary_period")
        .limit(limit)
        .execute()
        .data
        or []
    )


def find_confirmed_skills(user_id: int) -> list[str]:
    """Skill terkonfirmasi milik pengguna (R-08-04).

    Hanya ``is_confirmed = true``, dan hanya nama skill — isi CV tidak pernah
    dibaca di sini maupun disimpan di database.
    """
    baris = (
        _client()
        .table(USER_SKILLS)
        .select("skill")
        .eq("user_id", user_id)
        .eq("is_confirmed", True)
        .execute()
        .data
        or []
    )
    return [r["skill"] for r in baris if r.get("skill")]


def find_sources() -> list[dict]:
    """``source_id`` -> nama sumber, untuk label tautan."""
    return _client().table(SOURCES).select("id,name").execute().data or []


# --- rate limit ---------------------------------------------------------

def hari_ini() -> str:
    """Tanggal UTC sebagai kunci harian."""
    return datetime.now(timezone.utc).date().isoformat()


def hitung_pemakaian(user_id: int, tanggal: str) -> int:
    """Jumlah pertanyaan pengguna ini pada ``tanggal`` (R-08-09)."""
    hasil = (
        _client()
        .table(USAGE)
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("tanggal", tanggal)
        .execute()
    )
    jumlah = getattr(hasil, "count", None)
    return jumlah if jumlah is not None else len(hasil.data or [])


def catat_pemakaian(user_id: int, tanggal: str) -> None:
    """Catat satu pemakaian.

    Disimpan di tabel, bukan memori proses: beberapa worker atau restart
    aplikasi akan menghapus penghitung di memori, dan batas harian menjadi tidak
    berarti.
    """
    (
        _client()
        .table(USAGE)
        .insert({"user_id": user_id, "tanggal": tanggal})
        .execute()
    )
