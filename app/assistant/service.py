"""Aturan bisnis asisten AI (PRD-08).

Tempat tinggal: penyusunan konteks dari data aplikasi, larangan memakai isi CV
mentah (R-08-04), penolakan/klarifikasi saat konteks lemah (R-08-07), dan rate
limit per pengguna (R-08-09). Tidak boleh mengimpor ``flask``.

**Grounded, bukan bebas.** Asisten hanya menerima data yang disusun di sini,
dan system prompt melarang mengarang gaji, perusahaan, atau tautan. Model yang
tidak tahu jawabannya harus mengatakan demikian, bukan mengisi kekosongan.
"""

from __future__ import annotations

import logging
import re

from core.errors import RateLimitError
from core.external.deepseek import AssistantError

from . import repository

logger = logging.getLogger(__name__)

# Batas panjang pertanyaan. Pertanyaan panjang tidak membuat jawaban lebih baik,
# dan tanpa batas ini satu permintaan dapat menghabiskan kuota token.
MAX_QUESTION_LENGTH = 500

# Konteks dibatasi agar biaya dan latensi terkendali (§9).
MAX_JOBS_IN_CONTEXT = 8
MAX_TOKENS = 512

SYSTEM_PROMPT = """\
Anda adalah asisten karier KarirLens. Anda menjawab HANYA dari DATA yang
diberikan di bawah ini.

Aturan wajib:
1. Jangan menyebut angka gaji, nama perusahaan, atau tautan yang tidak ada di
   DATA. Bila DATA tidak memuatnya, katakan bahwa datanya belum tersedia.
2. Jangan mengarang lowongan, statistik, atau tautan.
3. Bila DATA tidak cukup untuk menjawab, minta klarifikasi atau sampaikan
   keterbatasan dengan sopan. Jangan menebak.
4. Bila menyebut lowongan, sebutkan judul dan perusahaan persis seperti di DATA.
5. Jawab dalam Bahasa Indonesia, ringkas (maksimal 6 kalimat), tanpa markdown.
6. Jangan meminta atau menyebut isi CV pengguna; yang tersedia hanya skill.
"""


def _kata_kunci(question: str) -> list[str]:
    """Kata bermakna dari pertanyaan, untuk mencari lowongan relevan.

    Stopword dibuang supaya "lowongan apa untuk data analyst" tidak mencari
    kata "apa" dan "untuk" yang muncul di mana-mana.
    """
    dari = {
        "apa", "adalah", "yang", "untuk", "dan", "atau", "di", "ke", "dari",
        "dengan", "pada", "ini", "itu", "saya", "aku", "ingin", "mau", "bisa",
        "ada", "tidak", "gimana", "bagaimana", "berapa", "kak", "tolong",
        "carikan", "berikan", "jelaskan", "sebutkan", "lowongan", "kerja",
        "pekerjaan", "the", "and", "for", "with", "what", "how", "you",
        "saja", "semua", "list", "daftar",
    }
    kata = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{2,}", question or "")
    return [k.lower() for k in kata if k.lower() not in dari][:6]


# Pertanyaan meta: tidak mencari lowongan tertentu, melainkan menanyakan isi
# sistem ("kategori apa saja", "gaji berapa"). Setelah stopword dibuang, kata
# yang tersisa kosong — tanpa daftar ini, pertanyaan seperti itu dianggap tidak
# relevan dan ditolak padahal datanya ada.
_META = ("kategori", "kategorinya", "cluster", "gaji", "salary", "insight",
         "statistik", "skill", "keahlian", "tren", "trennya")


def build_context(question: str, user_id: int) -> dict:
    """Konteks dari lowongan, cluster, statistik gaji, dan skill terkonfirmasi (R-08-02).

    Bentuknya dict yang mudah diformat menjadi teks prompt. Tidak ada isi CV
    di sini: hanya skill yang sudah disetujui pengguna (R-08-04).
    """
    from app.insights import salary as salary_rules

    sumber = {row["id"]: row["name"] for row in repository.find_sources()}
    jobs = repository.search_jobs(_kata_kunci(question), limit=MAX_JOBS_IN_CONTEXT)

    gaji = salary_rules.salary_stats(repository.find_jobs_with_salary())

    return {
        "jobs": [
            {
                "id": j.get("id"),
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("location"),
                "employment_type": j.get("employment_type"),
                "skills": (j.get("skills") or [])[:8],
                "salary_min": j.get("salary_min"),
                "salary_max": j.get("salary_max"),
                "salary_currency": j.get("salary_currency"),
                "salary_period": j.get("salary_period"),
                "source": sumber.get(j.get("source_id")),
                # Tautan asli selalu ikut; asisten hanya boleh menyebut tautan
                # yang ada di sini (R-08-06).
                "url": j.get("source_url"),
            }
            for j in jobs
        ],
        "categories": [
            {"label": c.get("label"), "keywords": (c.get("keywords") or [])[:6]}
            for c in repository.find_clusters()
        ],
        "salary": gaji,
        "skills": repository.find_confirmed_skills(user_id),
    }


def _format_context(context: dict) -> str:
    """Konteks dict -> teks untuk prompt. Ringkas dan tanpa basa-basi."""
    bagian: list[str] = []

    if context["skills"]:
        bagian.append(
            "SKILL TERKONFIRMASI PENGGUNA: " + ", ".join(context["skills"])
        )

    if context["jobs"]:
        baris = []
        for j in context["jobs"]:
            gaji = ""
            if j["salary_min"] or j["salary_max"]:
                low = j["salary_min"]
                high = j["salary_max"]
                rentang = f"{low or '?'}-{high or '?'} {j['salary_currency'] or ''}".strip()
                if j["salary_period"]:
                    rentang += f" per {j['salary_period']}"
                gaji = f" | gaji: {rentang}"
            skill = ", ".join(j["skills"]) if j["skills"] else "-"
            baris.append(
                f"- {j['title']} di {j['company'] or 'perusahaan tidak disebut'}"
                f" ({j['location'] or 'lokasi tidak disebut'}){gaji}"
                f" | skill: {skill} | sumber: {j['url']}"
            )
        bagian.append("LOWONGAN RELEVAN:\n" + "\n".join(baris))
    else:
        bagian.append("LOWONGAN RELEVAN: tidak ada yang cocok dengan pertanyaan.")

    if context["categories"]:
        bagian.append(
            "KATEGORI: "
            + "; ".join(
                f"{c['label']} ({', '.join(c['keywords'])})"
                for c in context["categories"]
            )
        )

    gaji = context["salary"]
    if gaji.get("sample_sufficient"):
        ringkas = "; ".join(
            f"{g['currency'] or 'mata uang tidak disebut'} "
            f"{g['period'] or 'periode tidak disebut'}: median {g['median']}, "
            f"P25 {g['p25']}, P75 {g['p75']}, {g['sample']} sampel"
            for g in gaji["groups"]
        )
        bagian.append("STATISTIK GAJI (faktual): " + ringkas)
    else:
        bagian.append(
            f"STATISTIK GAJI: tidak tersedia (sampel kurang dari "
            f"{gaji.get('minimum_sample', 5)})."
        )

    return "\n\n".join(bagian)


def _klarifikasi(context: dict) -> str:
    """Jawaban saat konteks tidak memuat apa pun untuk dijawab (R-08-07).

    Menolak dengan jujur lebih baik daripada mengarang. Kalimatnya menyebut apa
    yang bisa ditanyakan agar pengguna tidak buntu — termasuk kategori yang
    memang tersedia, karena itu pintu masuk paling mudah.
    """
    contoh = ""
    if context["categories"]:
        label = [c["label"] for c in context["categories"][:3] if c.get("label")]
        if label:
            contoh = " Misalnya: " + ", ".join(label) + "."

    return (
        "Saya belum menemukan lowongan yang cocok dengan pertanyaan itu di "
        "KarirLens. Coba sebutkan posisi, skill, atau nama perusahaan yang Anda "
        "cari — misalnya \"lowongan data analyst\" atau \"perusahaan dengan "
        "skill Python\"." + contoh
    )


def _cek_limit(user_id: int, batas_harian: int) -> str:
    """Periksa batas harian; kembalikan tanggal untuk pencatatan (R-08-09).

    Batas dihitung per pengguna per hari UTC. Melempar ``RateLimitError``
    dengan pesan yang menyebut kapan batasnya kembali — pesan "terlalu banyak"
    tanpa keterangan hanya membuat pengguna mencoba terus.
    """
    tanggal = repository.hari_ini()
    terpakai = repository.hitung_pemakaian(user_id, tanggal)

    if terpakai >= batas_harian:
        raise RateLimitError(
            f"Batas {batas_harian} pertanyaan per hari sudah tercapai. "
            "Coba lagi besok."
        )
    return tanggal


def _relevan_dengan_kategori(kata: list[str], context: dict) -> bool:
    """True bila pertanyaan menyebut kategori yang kita punya.

    Kategori selalu ada (hasil clustering), jadi memakai "kategori kosong"
    sebagai syarat klarifikasi tidak pernah benar: pertanyaan apa pun akan
    lolos. Yang menentukan adalah apakah kata-kata pertanyaan menyentuh label,
    kata kunci kategori, atau merupakan pertanyaan meta tentang isi sistem.
    """
    if any(m in (kata or []) for m in _META):
        # Pertanyaan meta ("kategori apa saja", "gaji berapa") dijawab dari
        # kategori dan statistik yang memang ada di konteks.
        return bool(context["categories"])

    bahan = " ".join(
        f"{c.get('label') or ''} {' '.join(c.get('keywords') or [])}"
        for c in context["categories"]
    ).lower()
    return any(k in bahan for k in kata)


def _perlu_klarifikasi(kata: list[str], context: dict) -> bool:
    """Apakah konteks terlalu lemah untuk dijawab dengan jujur (R-08-07).

    Tiga keadaan dianggap lemah:

    1. Tidak ada lowongan yang cocok **dan** tidak ada kategori yang disebut
       pertanyaan. Model hanya akan menjawab dari pengetahuan umumnya.
    2. Tidak ada lowongan sama sekali (database kosong).

    Bila pertanyaan menyebut kategori yang ada — "kategori apa saja?", "gaji
    backend?" — konteks masih memuat jawaban, jadi model tetap dipanggil.
    """
    if not context["jobs"] and not context["categories"]:
        return True
    if not context["jobs"] and not _relevan_dengan_kategori(kata, context):
        return True
    return False


def ask(
    question: str,
    user_id: int,
    *,
    client=None,
    batas_harian: int = 20,
) -> dict:
    """Jawaban asisten yang hanya merujuk data aplikasi (R-08-03..R-08-07).

    ``client`` diinjeksi agar test memakai tiruan tanpa jaringan (R-08-13).
    Bila ``client`` None dan konfigurasi tidak punya API key, jawabannya adalah
    pemberitahuan bahwa asisten belum dikonfigurasi — bukan error 500.

    Kembalian memenuhi kontrak PRD-F04 §4.1: ``{"reply": str, "sources": [...]}``
    di dalam kunci ``data`` yang dibungkus route.
    """
    teks = (question or "").strip()
    if not teks:
        raise ValueError("Pertanyaan tidak boleh kosong.")
    if len(teks) > MAX_QUESTION_LENGTH:
        teks = teks[:MAX_QUESTION_LENGTH]

    # **Cek kuota sebelum apa pun**, tetapi hanya hentikan bila memang habis.
    # Pemeriksaan ini sengaja lebih dulu supaya pengguna yang kehabisan kuota
    # tidak membuat sistem menyusun konteks (beberapa query database) untuk
    # pertanyaan yang toh akan ditolak.
    tanggal = _cek_limit(user_id, batas_harian)

    kata = _kata_kunci(teks)
    context = build_context(teks, user_id)

    # **Klarifikasi sebelum memanggil model.** Bila konteks tidak memuat
    # jawaban, model hanya akan mengarang dari pengetahuan umumnya. Lebih jujur
    # dan lebih murah berhenti di sini.
    #
    # Kuota TIDAK dipotong: pengguna tidak menerima jawaban, dan pertanyaan
    # yang tidak terjawab tidak seharusnya menghabiskan jatahnya.
    if _perlu_klarifikasi(kata, context):
        return {"reply": _klarifikasi(context), "sources": []}

    if client is None:
        return {
            "reply": (
                "Asisten AI belum dikonfigurasi di lingkungan ini. "
                "Data lowongan, insight, dan rekomendasi tetap dapat Anda pakai."
            ),
            "sources": [],
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"DATA:\n{_format_context(context)}\n\nPERTANYAAN:\n{teks}",
        },
    ]

    try:
        hasil = client.chat(messages, max_tokens=MAX_TOKENS)
    except AssistantError as error:
        # Jangan catat pemakaian: pengguna tidak mendapat jawaban.
        logger.warning("Asisten gagal menjawab: %s", type(error).__name__)
        raise

    repository.catat_pemakaian(user_id, tanggal)

    return {
        "reply": str(hasil.get("reply") or "").strip(),
        # Sumber SELALU dari data, bukan dari yang disebut model: model dapat
        # mengarang URL, dan tautan karangan lebih berbahaya daripada tidak ada
        # tautan (R-08-06).
        "sources": [
            {
                "label": f"{j['title']} — {j['company'] or 'perusahaan tidak disebut'}",
                "url": j["url"],
            }
            for j in context["jobs"][:3]
            if j.get("url")
        ],
    }
