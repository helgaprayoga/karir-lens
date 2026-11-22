"""Perhitungan rekomendasi deterministik, tanpa AI per permintaan (R-07-11).

Bobot kemiripan skill dan kecocokan kategori dibaca dari konfigurasi agar dapat
diuji tanpa jaringan.

**Kenapa deterministik, bukan model.** Skor yang sama harus dihasilkan untuk
masukan yang sama, setiap kali, tanpa memanggil layanan luar. Pengguna dapat
memeriksa alasannya ("cocok pada 3 skill: python, sql, git") dan mencocokkannya
dengan CV-nya sendiri — itu tidak mungkin bila skornya berasal dari model yang
jawabannya berubah-ubah.
"""

from __future__ import annotations

DEFAULT_SKILL_WEIGHT = 0.75
DEFAULT_CATEGORY_WEIGHT = 0.25

# Skor kategori hanya diberikan bila kategori lowongan sama dengan kategori
# terkuat pengguna. Ini bukan "kategori mirip": cluster hasil KMeans tidak punya
# jarak yang bermakna antar label, jadi menyatakan "hampir cocok" akan menjadi
# klaim yang tidak dimiliki data.
CATEGORY_FULL_CREDIT = 1.0


def _rapi(nama) -> str:
    return " ".join(str(nama or "").lower().split())


def skill_overlap(job_skills: list | None, confirmed_skills: set[str] | None) -> list[str]:
    """Skill yang dimiliki pengguna dan diminta lowongan, terurut.

    Pencocokan memakai bentuk yang sudah dinormalisasi kamus
    (``core/skills.normalize_skills``) di kedua sisi, jadi "PostgreSQL" pada CV
    dan "postgresql" pada lowongan dihitung sama (R-07-04).
    """
    diminta = {_rapi(s) for s in (job_skills or []) if s}
    dimiliki = {_rapi(s) for s in (confirmed_skills or []) if s}
    return sorted(diminta & dimiliki)


def score(
    job: dict,
    confirmed_skills: set[str],
    cluster_id: int | None,
    *,
    skill_weight: float = DEFAULT_SKILL_WEIGHT,
    category_weight: float = DEFAULT_CATEGORY_WEIGHT,
) -> tuple[float, list[str]]:
    """Skor 0..100 dan alasan singkat (R-07-09, R-07-10).

    ``cluster_id`` adalah kategori terkuat pengguna — kategori yang paling
    banyak lowongannya cocok, bukan kategori yang dipilih manual. Alasannya
    dikembalikan sebagai daftar yang dapat langsung ditampilkan; satu alasan
    per baris lebih mudah dibaca daripada satu kalimat panjang.
    """
    cocok = skill_overlap(job.get("skills"), confirmed_skills)

    # Kemiripan skill = proporsi skill lowongan yang dimiliki pengguna.
    # Memakai proporsi terhadap *lowongan*, bukan terhadap CV: lowongan yang
    # meminta 3 skill dan semuanya dimiliki lebih cocok daripada lowongan yang
    # meminta 20 skill dan pengguna punya 3.
    diminta = {_rapi(s) for s in (job.get("skills") or []) if s}
    kemiripan = (len(cocok) / len(diminta)) if diminta else 0.0

    # **Kepercayaan atas sampel kecil.** Lowongan yang hanya menyebut 1 skill
    # dan skill itu dimiliki memberi kemiripan 1,0 — skor 100% untuk satu
    # kebetulan. Terukur pada data nyata: sebuah lowongan yang hanya menyebut
    # "aws" mendapat 100% dan menempati puncak rekomendasi di atas lowongan
    # yang cocok pada empat skill.
    #
    # Karena itu kemiripan dikalikan faktor kepercayaan yang tumbuh seiring
    # jumlah skill yang diminta, mencapai penuh pada 4 skill. Ini bukan
    # penalti terhadap lowongan berskill sedikit — melainkan pengakuan bahwa
    # satu titik data tidak cukup untuk menyimpulkan kecocokan.
    kepercayaan = min(1.0, len(diminta) / 4)
    kemiripan *= kepercayaan

    kategori_cocok = (
        cluster_id is not None
        and job.get("cluster_id") is not None
        and int(job["cluster_id"]) == int(cluster_id)
    )
    nilai_kategori = CATEGORY_FULL_CREDIT if kategori_cocok else 0.0

    total = skill_weight * kemiripan + category_weight * nilai_kategori
    skor = round(total * 100)

    alasan: list[str] = []
    if cocok:
        alasan.append(
            f"Cocok pada {len(cocok)} skill: {', '.join(cocok)}"
        )
    if kategori_cocok:
        alasan.append("Kategori lowongan sesuai dengan skill terbanyak Anda")
    if not alasan:
        alasan.append("Belum ada skill yang cocok")

    return skor, alasan


def rank(
    jobs: list[dict],
    confirmed_skills: set[str],
    cluster_id: int | None,
    *,
    limit: int = 10,
    skill_weight: float = DEFAULT_SKILL_WEIGHT,
    category_weight: float = DEFAULT_CATEGORY_WEIGHT,
    exclude_ids: set[int] | None = None,
) -> list[dict]:
    """Beri skor setiap lowongan dan kembalikan ``limit`` teratas (R-07-14).

    ``exclude_ids`` berisi lowongan yang sudah di-bookmark: R-07-14 meminta
    lowongan tersimpan tidak muncul sebagai rekomendasi utama, karena pengguna
    sudah menemukannya. Lowongan tanpa satu pun skill yang cocok dibuang —
    alasan "belum ada skill yang cocok" bukan rekomendasi.
    """
    abaikan = exclude_ids or set()
    hasil = []

    for job in jobs or []:
        if job.get("id") in abaikan:
            continue

        cocok = skill_overlap(job.get("skills"), confirmed_skills)
        if not cocok:
            continue

        skor, alasan = score(
            job,
            confirmed_skills,
            cluster_id,
            skill_weight=skill_weight,
            category_weight=category_weight,
        )
        hasil.append({**job, "match": {"score": skor, "reasons": alasan}})

    # Urutan: skor menurun, lalu tanggal terbit terbaru sebagai pemecah seri
    # agar hasilnya stabil antar permintaan (bukan urutan acak dari database).
    # `sorted` stabil, jadi dua pengurutan berurutan sudah cukup dan lebih
    # mudah dibaca daripada satu kunci gabungan.
    hasil.sort(key=lambda j: str(j.get("posted_at") or ""), reverse=True)
    hasil.sort(key=lambda j: j["match"]["score"], reverse=True)

    return hasil[:limit]
