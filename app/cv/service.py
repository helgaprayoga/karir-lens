"""Aturan bisnis CV dan rekomendasi (PRD-07).

Tempat tinggal: validasi tipe/ukuran berkas, urutan ekstraksi lokal sebelum AI,
penghapusan berkas sementara di blok ``finally``, dan penyusunan alasan
rekomendasi. Berkas dan teks CV tidak boleh disimpan maupun dicatat ke log
(R-07-08).
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections import Counter

from core.errors import ValidationError
from core.skills import is_ambiguous, match_skills, normalize_skills

from . import extractor, recommender, repository

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)

# Ekstensi diperiksa juga: sebagian peramban mengirim content-type kosong atau
# `application/octet-stream` untuk DOCX.
ALLOWED_EXTENSIONS = (".pdf", ".docx")

MAX_SIZE_BYTES = 5 * 1024 * 1024

# Jumlah maksimum kandidat yang boleh dikirim ke AI fallback dalam satu unggahan
# (R-07-05). Batas ini melindungi kuota dan mencegah satu CV menguras anggaran.
MAX_AI_FALLBACK = 5


def _ekstensi(nama: str | None) -> str:
    return os.path.splitext(str(nama or "").lower())[1]


def validate_upload(file_storage) -> str:
    """Periksa tipe dan ukuran sebelum berkas ditulis (R-07-01, R-07-02).

    Mengembalikan ``content_type`` yang akan menentukan pembaca. Tipe yang
    tidak dikenal tetapi ber-ekstensi sah tetap diterima, karena peramban
    sering mengirim tipe generik untuk DOCX.

    Ukuran diperiksa lebih dulu lewat ``content_length`` bila ada, lalu
    diperiksa lagi setelah ditulis — ``content_length`` dapat berbohong.
    """
    if file_storage is None or not getattr(file_storage, "filename", None):
        raise ValidationError("Pilih berkas CV terlebih dahulu.")

    nama = file_storage.filename
    ekstensi = _ekstensi(nama)
    tipe = (getattr(file_storage, "mimetype", None) or "").lower()

    if ekstensi not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Berkas harus PDF atau DOCX.",
            code="UNSUPPORTED_FILE_TYPE",
        )
    if tipe and tipe not in ALLOWED_MIME_TYPES and tipe != "application/octet-stream":
        raise ValidationError(
            "Berkas harus PDF atau DOCX.",
            code="UNSUPPORTED_FILE_TYPE",
        )

    if ekstensi == ".pdf":
        return "application/pdf"
    return extractor.DOCX_MIME


def extract_and_suggest(file_storage) -> dict:
    """Ekstrak skill dari CV lalu hapus berkas sementara (R-07-01..R-07-05).

    Urutannya mengikuti §4.1: validasi → tulis ke berkas sementara → ekstraksi
    lokal → cocokkan kamus → AI fallback untuk ambigu → hapus berkas.

    **Batas privasi.** Berkas sementara dihapus di blok ``finally``, sehingga
    tetap terhapus meskipun ekstraksi gagal. Isi CV tidak pernah ditulis ke log;
    yang dicatat hanya jumlah kandidat.

    Kembalian: ``{"skills": [...], "ambiguous": [{text, reason}]}`` sesuai
    kontrak ``POST /api/cv/extract`` (PRD-F04 §4.1).
    """
    content_type = validate_upload(file_storage)

    # `mkstemp` membuat nama unik sehingga dua unggahan bersamaan tidak saling
    # menimpa; `NamedTemporaryFile` tidak dapat dibuka ulang di Windows.
    fd, path = tempfile.mkstemp(suffix=_ekstensi(file_storage.filename))
    os.close(fd)

    try:
        file_storage.save(path)

        ukuran = os.path.getsize(path)
        if ukuran > MAX_SIZE_BYTES:
            raise ValidationError(
                f"Ukuran berkas {ukuran / 1048576:.1f} MB melebihi batas 5 MB.",
                code="FILE_TOO_LARGE",
            )
        if ukuran == 0:
            raise ValidationError("Berkas kosong.", code="EMPTY_FILE")

        try:
            teks = extractor.extract_text(path, content_type)
        except extractor.ExtractionError as error:
            raise ValidationError(str(error), code="EXTRACTION_FAILED") from None
    finally:
        # Selalu dihapus: pada jalur sukses maupun gagal (R-07-08).
        try:
            os.unlink(path)
        except OSError:
            logger.warning("Berkas sementara gagal dihapus.")

    return suggest_skills(teks)


def suggest_skills(teks: str, *, taksonomi=None) -> dict:
    """Cocokkan teks dengan kamus, lalu tawarkan ambigu untuk diputuskan.

    **AI tidak dipanggil di sini.** Kandidat ambigu dikembalikan apa adanya;
    pemanggil (route) yang memutuskan apakah AI fallback dijalankan. Dengan
    begitu pencocokan kamus dapat diuji tanpa jaringan (R-07-16), dan
    rekomendasi tidak pernah memanggil AI (R-07-11).

    ``taksonomi`` adalah daftar kata ambigu tambahan; ``None`` berarti memakai
    aturan dari ``core.skills.is_ambiguous``.
    """
    if not teks or not teks.strip():
        raise ValidationError(
            "Tidak ada teks yang dapat dibaca dari CV Anda.",
            code="EMPTY_TEXT",
        )

    cocok = normalize_skills(match_skills(teks))

    # Kandidat ambigu: kata yang tampak seperti skill tetapi tidak ada di kamus.
    # Hanya potongan yang menyerupai istilah teknis yang dipertimbangkan, agar
    # daftar "perlu diputuskan" tidak berisi kata biasa.
    ambigu = _kandidat_ambigu(teks, cocok, taksonomi)

    logger.info(
        "Ekstraksi CV: %d skill dikenali, %d kandidat ambigu.",
        len(cocok),
        len(ambigu),
    )
    return {"skills": cocok, "ambiguous": ambigu}


# Kata yang tidak boleh diusulkan sebagai skill meskipun bentuknya pendek.
# Terukur pada CV uji: tanpa daftar ini, "budi" (nama), "dan", "data", dan "di"
# muncul di daftar "perlu diputuskan" — pengguna dibanjiri pertanyaan tentang
# kata biasa, dan daftar itu kehilangan maknanya.
_NOT_SKILL = frozenset({
    # Indonesia
    "dan", "di", "ke", "dari", "yang", "untuk", "dengan", "pada", "adalah",
    "atau", "juga", "dalam", "ini", "itu", "tidak", "bisa", "dapat", "kami",
    "kita", "anda", "saya", "mereka", "oleh", "agar", "karena", "jika", "bila",
    "saat", "setelah", "sebelum", "serta", "bagi", "tentang", "secara",
    "lebih", "sangat", "harus", "wajib", "mampu", "tahun", "bulan", "hari",
    "data", "proyek", "kerja", "tim", "s1", "s2", "s3", "d3", "sma", "smk",
    # Inggris
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "they", "who", "what", "when", "where", "how",
    "all", "any", "can", "may", "must", "should", "not", "but", "also",
    "more", "than", "into", "about", "job", "work", "role", "team", "years",
    "experience", "education", "skills", "skill", "name", "email", "phone",
})


def _kandidat_ambigu(teks: str, sudah_cocok: list[str], taksonomi=None) -> list[dict]:
    """Kandidat yang perlu diputuskan pengguna (R-07-05).

    Mengikuti acuan PRD §10 ``explain()``: kandidat dikembalikan beserta alasan
    singkat, bukan dikirim diam-diam ke AI. Batas ``MAX_AI_FALLBACK`` berlaku
    pada jumlah yang diusulkan, karena setiap kandidat berpotensi menjadi satu
    panggilan AI.

    Kata fungsi dan kata umum dibuang lebih dulu (``_NOT_SKILL``). Tanpa itu,
    daftar "perlu diputuskan" berisi "dan", "di", dan nama orang — bukan
    pertanyaan yang berguna.
    """
    if taksonomi is None:
        taksonomi = []

    dikenal = set(sudah_cocok)
    hasil: list[dict] = []
    dilihat: set[str] = set()

    for kata in _potongan_teknis(teks):
        if kata in dilihat or kata in dikenal or kata in _NOT_SKILL:
            continue
        if not is_ambiguous(kata):
            continue
        dilihat.add(kata)
        hasil.append(
            {
                "text": kata,
                "reason": "Belum ada di kamus skill; konfirmasi bila ini skill yang Anda pakai.",
            }
        )
        if len(hasil) >= MAX_AI_FALLBACK:
            break

    return hasil


def _potongan_teknis(teks: str) -> list[str]:
    """Potongan pendek yang menyerupai nama teknologi, unik, urut kemunculan.

    **Baris pertama dilewati.** Pada CV, baris itu hampir selalu berisi nama
    orang, dan nama tidak mungkin didaftarkan semuanya. Terukur pada CV uji:
    tanpa aturan ini, "budi" diusulkan sebagai skill yang perlu diputuskan.
    Ini aturan struktural, bukan daftar — ia menangani semua nama sekaligus.
    """
    import re

    baris = [b for b in (teks or "").splitlines() if b.strip()]
    isi = "\n".join(baris[1:]) if len(baris) > 1 else (baris[0] if baris else "")

    kandidat: list[str] = []
    for mentah in re.findall(r"\b[A-Za-z][A-Za-z0-9+#./-]{1,23}\b", isi):
        kata = mentah.strip(".-/").lower()
        if len(kata) < 2 or kata in kandidat:
            continue
        kandidat.append(kata)
    return kandidat


def normalize_suggestions(skills: list[str]) -> list[str]:
    """Rapikan daftar kandidat dari query string, tanpa duplikat.

    Dipakai route ketika menampilkan ulang kandidat hasil ekstraksi: nilai dari
    URL tidak dipercaya apa adanya, tetapi juga tidak boleh hilang bentuknya.
    """
    return normalize_skills([str(s) for s in (skills or []) if str(s).strip()])


def save_confirmed_skills(user_id: int, skills: list[str], source: str = "cv") -> list[dict]:
    """Simpan **hanya** skill yang dikonfirmasi pengguna (R-07-07).

    ``source`` menandai asal skill ("cv" atau "manual") agar halaman profil
    dapat menampilkan dari mana ia berasal.
    """
    bersih = [str(s).strip().lower() for s in (skills or []) if str(s).strip()]
    if not bersih:
        raise ValidationError("Pilih minimal satu skill untuk disimpan.")

    from app.profile import service as profile_service

    return profile_service.confirm_skills(user_id, bersih, source=source)


def _shape(job: dict, sumber: dict, disimpan: set[int]) -> dict:
    """Baris database -> bentuk ``job`` kontrak PRD-F02 §4.1."""
    return {
        "id": job.get("id"),
        "title": job.get("title"),
        "company_name": job.get("company_name"),
        "company_slug": job.get("company_slug"),
        "location": job.get("location"),
        "employment_type": job.get("employment_type"),
        "experience_level": None,
        "description": job.get("description"),
        "skills": job.get("skills") or [],
        "skills_source": job.get("skills_source"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("salary_currency"),
        "salary_period": job.get("salary_period"),
        "source": sumber.get(job.get("source_id")),
        "source_url": job.get("source_url"),
        "posted_at": job.get("posted_at"),
        "is_saved": job.get("id") in disimpan,
        "match": None,
    }


def get_recommendations(user_id: int, limit: int = 10) -> dict:
    """Rekomendasi berbasis skill terkonfirmasi, tanpa AI per permintaan (R-07-09..R-07-11).

    ``cluster_id`` yang dipakai sebagai kategori terkuat adalah **kategori yang
    paling banyak lowongannya cocok** dengan skill pengguna, bukan kategori yang
    dipilih manual — pengguna tidak pernah memilih kategori, dan menebaknya
    dari satu skill acak akan menghasilkan alasan palsu.
    """
    skills = repository.find_confirmed_skills(user_id)
    nama = {s["skill"] for s in skills if s.get("skill")}

    hasil = {
        "skills": skills,
        "recommendations": [],
        "state": "no_skills" if not nama else "ready",
    }
    if not nama:
        return hasil

    kandidat = repository.find_candidate_jobs()
    sumber = {row["id"]: row["name"] for row in repository.find_sources()}
    disimpan = repository.find_saved_job_ids(user_id)

    # Kategori terkuat: cluster dengan jumlah lowongan cocok terbanyak.
    hitung: Counter[int] = Counter()
    for job in kandidat:
        cid = job.get("cluster_id")
        if cid is None:
            continue
        if recommender.skill_overlap(job.get("skills"), nama):
            hitung[cid] += 1
    kategori_terkuat = hitung.most_common(1)[0][0] if hitung else None

    terpilih = recommender.rank(
        kandidat, nama, kategori_terkuat, limit=limit, exclude_ids=disimpan
    )
    hasil["recommendations"] = [_shape(j, sumber, disimpan) | {"match": j["match"]} for j in terpilih]
    hasil["cluster_id"] = kategori_terkuat
    return hasil
