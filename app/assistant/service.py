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

# Kata yang menandakan pengguna memang mencari kerja, bukan bertanya hal umum.
# Tanpa daftar ini, "backend engineer" tertolak hanya karena judul lowongannya
# berbunyi "Software Engineer, Backend" dan pencarian teks tidak menemukannya.
# Sebaliknya "apa itu quantum computing" tetap ditolak — tidak ada satu pun kata
# di sini yang muncul.
_NIAT_KERJA = {
    "loker", "posisi", "jabatan", "karir", "karier", "perusahaan", "rekrut",
    "rekrutmen", "hiring", "magang", "internship", "intern", "remote", "gaji",
    "fulltime", "freelance", "kontrak", "backend", "frontend", "fullstack",
    "devops", "engineer", "developer", "programmer", "analyst", "designer",
    "scientist", "administrator", "tester", "specialist", "staff", "lead",
}


def build_context(question: str, user_id: int) -> dict:
    """Konteks dari lowongan, cluster, statistik gaji, dan skill terkonfirmasi (R-08-02).

    Bentuknya dict yang mudah diformat menjadi teks prompt. Tidak ada isi CV
    di sini: hanya skill yang sudah disetujui pengguna (R-08-04).

    ``match`` menandai seberapa kuat lowongan itu menjawab pertanyaan: ``exact``
    bila kata kunci menemukan sesuatu, ``none`` bila tidak. Lowongan terbaru
    sengaja **tidak** diisi di sini, supaya gerbang klarifikasi dapat membedakan
    "tidak ada yang cocok" dari "tidak ada data". Pengisian cadangan dilakukan
    ``ask()`` setelah gerbang itu lolos, lewat ``_isi_lowongan_terbaru``.
    """
    from app.insights import salary as salary_rules

    sumber = {row["id"]: row["name"] for row in repository.find_sources()}
    kata = _kata_kunci(question)

    jobs = repository.search_jobs(kata, limit=MAX_JOBS_IN_CONTEXT) if kata else []

    gaji = salary_rules.salary_stats(repository.find_jobs_with_salary())

    return {
        "match": "exact" if jobs else "none",
        "jobs": [_ringkas_lowongan(j, sumber) for j in jobs],
        "categories": [
            {"label": c.get("label"), "keywords": (c.get("keywords") or [])[:6]}
            for c in repository.find_clusters()
        ],
        "salary": gaji,
        "skills": repository.find_confirmed_skills(user_id),
    }


def _ringkas_lowongan(j: dict, sumber: dict) -> dict:
    """Satu baris lowongan -> bentuk yang dipakai prompt dan daftar sumber."""
    return {
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
        # Tautan asli selalu ikut; asisten hanya boleh menyebut tautan yang ada
        # di sini (R-08-06).
        "url": j.get("source_url"),
    }


def _format_context(context: dict) -> str:
    """Konteks dict -> teks untuk prompt. Ringkas dan tanpa basa-basi."""
    bagian: list[str] = []

    if context["skills"]:
        bagian.append(
            "SKILL TERKONFIRMASI PENGGUNA: " + ", ".join(context["skills"])
        )

    if context["jobs"]:
        # Lowongan ada, tetapi tidak satu pun cocok dengan kata kunci. Model
        # harus tahu ini pijakan terbaru, bukan jawaban pertanyaan — kalau tidak,
        # ia akan menyebutnya "relevan" dan menyesatkan pengguna.
        judul = "LOWONGAN RELEVAN"
        if context.get("match") == "latest":
            judul = (
                "LOWONGAN TERBARU (tidak ada yang persis cocok dengan pertanyaan; "
                "sebutkan itu sebelum meringkas)"
            )
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
        bagian.append(judul + ":\n" + "\n".join(baris))
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


def _ada_niat_kerja(question: str, kata: list[str]) -> bool:
    """Apakah pertanyaan memang tentang mencari kerja.

    Tiga sinyal, dari yang paling kuat:

    1. Menyebut skill yang ada di kamus ("python", "kubernetes").
    2. Menyebut kata seputar lowongan ("backend", "magang", "gaji").
    3. Menyebut label atau kata kunci kategori hasil clustering.

    Tanpa ini, membuka gerbang klarifikasi akan meloloskan pertanyaan umum
    seperti "apa itu quantum computing" — yang dulu sempat dijawab model dengan
    "Ada lowongan Data Analyst", jawaban yang tidak menjawab pertanyaannya.
    """
    from core.skills import match_skills

    if match_skills(question):
        return True

    semua = {k.lower() for k in kata}
    if semua & _NIAT_KERJA:
        return True

    return bool(semua & set(_META))


def _perlu_klarifikasi(kata: list[str], context: dict, question: str = "") -> bool:
    """Apakah konteks terlalu lemah untuk dijawab dengan jujur (R-08-07).

    Klarifikasi hanya untuk dua keadaan:

    1. Database tidak berisi lowongan maupun kategori sama sekali.
    2. Lowongan ada, tetapi pertanyaan tidak menunjukkan niat mencari kerja
       dan tidak satu pun lowongan cocok. Model hanya akan menjawab dari
       pengetahuan umumnya.

    Syarat lama menolak pertanyaan wajar: "backend engineer" gagal karena judul
    lowongannya berbunyi "Software Engineer, Backend" dan pencarian teks tidak
    menemukannya, padahal jelas yang dicari adalah lowongan.
    """
    if not context["jobs"] and not context["categories"]:
        return True
    if context["jobs"]:
        return False
    return not _ada_niat_kerja(question, kata)


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
    if _perlu_klarifikasi(kata, context, teks):
        return {"reply": _klarifikasi(context), "sources": []}

    # Pertanyaan lolos gerbang tetapi tidak ada lowongan yang persis cocok
    # (mis. "backend engineer" sementara judulnya "Software Engineer, Backend").
    # Isi dengan lowongan terbaru sebagai pijakan, dan tandai agar prompt
    # memerintahkan model menyebut bahwa tidak ada yang persis cocok.
    if not context["jobs"]:
        sumber = {row["id"]: row["name"] for row in repository.find_sources()}
        context["jobs"] = [
            _ringkas_lowongan(j, sumber)
            for j in repository.find_latest_jobs(MAX_JOBS_IN_CONTEXT)
        ]
        if context["jobs"]:
            context["match"] = "latest"

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
