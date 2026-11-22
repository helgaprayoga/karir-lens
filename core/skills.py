"""Kamus skill dan pencocokan berbasis aturan.

PRD-03 memakai ``preprocess``/``match_skills`` untuk menormalkan skill lowongan;
PRD-07 memakai fungsi yang sama untuk skill dari CV (R-07-04). AI hanya menjadi
fallback untuk skill ambigu, sehingga pencocokan utama tetap deterministik.

Kenapa berbasis aturan, bukan LLM: R-03-14 melarang normalisasi memanggil
layanan eksternal. Pencocokan kamus juga dapat diuji tanpa jaringan dan
memberi hasil yang sama setiap kali.
"""

from __future__ import annotations

import html as html_module
import json
import re
from functools import lru_cache
from pathlib import Path

DICTIONARY_PATH = Path(__file__).parent / "data" / "skills.json"
AMBIGUITY_THRESHOLD = 0.6

# Skill di bawah panjang ini dibuang: satu-dua huruf terlalu mudah salah cocok.
MIN_SKILL_LENGTH = 2

# Penanda bagian yang BUKAN syarat lowongan. Deskripsi Remotive memuat daftar
# kategori platform di bawah "NOT YOUR TECH STACK?"; tanpa dipangkas, pencocokan
# menghasilkan 26 skill padahal hanya 5 yang benar (diukur pada fixture asli,
# lihat docs/tasks/TEMUAN-sumber-skill.md).
SECTION_CUTS = (
    "not your tech stack",
    "how it works",
    "about us",
    "about the company",
    "benefits",
    "perks",
    "why join",
    "apply now",
    "ready? apply",
)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def load_dictionary() -> dict[str, object]:
    """Muat dan validasi kamus skill sekali per proses."""
    with DICTIONARY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not data.get("skills"):
        raise ValueError("Kamus skill tidak valid: field 'skills' wajib ada.")
    return data


def canonical_skills() -> list[str]:
    """Daftar skill baku yang dikenal kamus."""
    return list(load_dictionary()["skills"])


def _aliases() -> dict[str, str]:
    """Alias -> bentuk baku, tanpa entri yang tidak menunjuk skill dikenal."""
    data = load_dictionary()
    baku = set(data["skills"])
    return {
        alias.lower(): target
        for alias, target in (data.get("aliases") or {}).items()
        if isinstance(target, str) and target in baku
    }


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Pasangan (regex, bentuk baku) untuk semua skill dan alias.

    Batas kata ``(?<![\\w+#.])``/``(?![\\w+#])`` penting: tanpa itu ``go`` cocok
    di dalam "Golang" dan "Django", dan ``c`` cocok di dalam "React".

    Entri yang lebih panjang didahulukan agar "react native" menang atas
    "react"; pemenang pertama menandai bentang teksnya, dan bentang itu tidak
    boleh dipakai entri lain. Tanpa aturan ini, satu frasa menghasilkan dua
    skill sekaligus.
    """
    entri: dict[str, str] = {skill: skill for skill in load_dictionary()["skills"]}
    entri.update(_aliases())
    # 'c' satu huruf: terlalu mudah cocok walau dengan batas kata ("Development
    # in C, or Python" memang C, tetapi "QC" dan "C-level" bukan). Dibuang.
    entri.pop("c", None)

    hasil = []
    for teks in sorted(entri, key=len, reverse=True):
        pola = r"(?<![\w+#.])" + re.escape(teks).replace(r"\ ", r"\s+") + r"(?![\w+#])"
        hasil.append((re.compile(pola, re.IGNORECASE), entri[teks]))
    return tuple(hasil)


def strip_html(text: str | None) -> str:
    """Buang tag HTML dan rapikan spasi. Entitas di-decode."""
    if not text:
        return ""
    tanpa_tag = _TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", html_module.unescape(tanpa_tag)).strip()


def trim_sections(text: str | None) -> str:
    """Potong teks pada penanda bagian non-syarat (lihat ``SECTION_CUTS``).

    Dipakai untuk deskripsi yang memuat bagian promosi/kategori di bawahnya.
    Tanpa ini, skill yang dikenali bukan syarat lowongan.
    """
    if not text:
        return ""
    rendah = text.lower()
    akhir = len(text)
    for tanda in SECTION_CUTS:
        posisi = rendah.find(tanda)
        if posisi != -1:
            akhir = min(akhir, posisi)
    return text[:akhir].strip()


def preprocess(text: str | None) -> str:
    """Teks siap-cocok: HTML dibuang, entitas di-decode, bagian promosi dipotong."""
    return trim_sections(strip_html(text))


def _normalize_skill(nama: str) -> str | None:
    """Turunkan bentuk baku dari satu nama skill mentah.

    Menerima nama yang sudah dikenal kamus, alias, atau nama bebas yang
    mengandung salah satunya ("Quality Control (QC)" -> ``sql``? tidak:
    dikembalikan apa adanya bila tidak dikenal, karena skill deklaratif datang
    dari platform dan soft skill seperti "Leadership" tidak ada di kamus
    teknis). Yang dibuang hanya nama kosong dan yang terlalu pendek.
    """
    nama = _SPACE_RE.sub(" ", (nama or "").strip()).strip()
    if len(nama) < MIN_SKILL_LENGTH:
        return None

    kunci = nama.lower()
    alias = _aliases().get(kunci)
    if alias:
        return alias
    if kunci in set(load_dictionary()["skills"]):
        return kunci
    # Skill deklaratif dari platform: soft skill dan istilah yang belum ada di
    # kamus tetap disimpan, karena ia pernyataan sumber, bukan tebakan kita.
    return kunci


def normalize_skills(skills: list) -> list[str]:
    """Normalisasi daftar skill deklaratif: bentuk baku bila dikenal, dedup, urut.

    Dipakai untuk skill dari `candidatePreference.skills` Dealls, yang berupa
    nama bersih tetapi bercampur soft skill ("Leadership", "Public Speaking").
    Semua dipertahankan karena sumbernya menyatakannya; hanya diturunkan ke
    huruf kecil dan diurutkan.
    """
    hasil = set()
    for item in skills or []:
        nama = item.get("name") if isinstance(item, dict) else item
        baku = _normalize_skill(str(nama or ""))
        if baku:
            hasil.add(baku)
    return sorted(hasil)


def match_skills(*texts: str | None) -> list[str]:
    """Skill baku yang ditemukan pada satu atau beberapa teks.

    Semua argumen digabung sebelum dicocokkan, sehingga
    ``match_skills(judul, kualifikasi, deskripsi)`` mencari di ketiganya
    sekaligus tanpa mengulang skill yang sama.

    Bentang teks yang sudah dipakai entri lebih panjang tidak boleh dipakai
    entri lain: tanpa itu, "React Native" menghasilkan ``react`` dan
    ``react native`` sekaligus, dan "Node.js" menghasilkan ``node.js`` + ``js``.
    """
    gabungan = " ".join(preprocess(teks) for teks in texts if teks)
    if not gabungan:
        return []

    ditemukan: set[str] = set()
    terpakai: list[tuple[int, int]] = []

    for pola, baku in _patterns():
        for m in pola.finditer(gabungan):
            awal, akhir = m.span()
            bertumpuk = any(awal < b_akhir and akhir > b_awal for b_awal, b_akhir in terpakai)
            if bertumpuk:
                continue
            terpakai.append((awal, akhir))
            ditemukan.add(baku)
            break

    return sorted(ditemukan)


# Heading yang menandai awal bagian syarat. Ditulis sebagai pola terhadap baris
# pendek tanpa titik akhir, karena deskripsi sumber berupa teks berbaris — bukan
# HTML — sehingga `</h2>` tidak bisa dijadikan penanda.
HEADING_REQUIREMENT = re.compile(
    r"^(requirements?|qualifications?|kualifikasi|"
    r"what you(?:'ll|’ll| will)? bring|"
    r"what we(?:'re|’re| are) looking for|who we(?:'re|’re| are) looking for|"
    r"who you are|must[- ]have|required (?:skills?|qualifications?)|"
    r"the ideal candidate|what you need|your profile|"
    r"skills?(?: and| &)? (?:experience|qualifications?)|"
    r"nice to have|preferred qualifications?|about you)\b",
    re.IGNORECASE,
)

# Heading yang menandai bagian NON-syarat; menghentikan pemotongan.
HEADING_NON_REQUIREMENT = re.compile(
    r"^(about us|about the company|about \w+|why join|why work|benefits?|perks?|"
    r"compensation|salary|how to get started|how to apply|apply now|working at|"
    r"our (?:team|values|culture|mission)|service rates?|pay|"
    r"independent contractor|qualification path|what you get|what we offer)\b",
    re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
    """Baris judul bagian: pendek dan tidak diakhiri tanda akhir kalimat."""
    return len(line) <= 70 and not line.rstrip().endswith((".", "!", "?", ";"))


def requirement_section(description: str | None) -> str | None:
    """Teks di bawah heading syarat pertama, atau ``None`` bila tidak ada.

    Dipotong pada heading non-syarat berikutnya, supaya bagian "Benefits" atau
    "About us" tidak ikut dicocokkan.
    """
    if not description:
        return None

    baris = [b.strip() for b in description.splitlines() if b.strip()]
    mulai = None
    for i, b in enumerate(baris):
        if _is_heading(b) and HEADING_REQUIREMENT.match(b):
            mulai = i + 1
            break
    if mulai is None:
        return None

    hasil: list[str] = []
    for b in baris[mulai:]:
        if _is_heading(b) and (
            HEADING_NON_REQUIREMENT.match(b) or HEADING_REQUIREMENT.match(b)
        ):
            break
        hasil.append(b)
    return " ".join(hasil) if hasil else None


def infer_skills(title: str | None, description: str | None) -> list[str]:
    """Skill yang **disimpulkan** dari teks, untuk sumber tanpa field skill.

    Kalibrr dan Remotive tidak menyediakan daftar skill; keduanya hanya punya
    prosa. Mengambil seluruh deskripsi apa adanya menghasilkan salah cocok yang
    parah, terukur pada data nyata:

    - "Senior Data Engineer" (Lemon.io) -> ``react``, karena *boilerplate*
      perekrut menyebut "Senior React Full-stack Engineers come in all the time"
      di bagian promosi, di atas syarat sebenarnya.
    - "Content Reviewer" -> ``android``/``ios``, karena syarat perangkat keras
      menyebut "smartphone (Android 5.0, iOS 14 or higher)".
    - "Freelance Writer" -> ``rest api``, karena prosa memuat "the rest of our
      content team".

    Tiga tingkat, dari paling presisi:

    1. **Judul.** Sinyal terkuat dan paling sedikit salah, tetapi hanya memberi
       satu-dua skill.
    2. **Bagian syarat** di bawah heading ("Requirements", "What you'll bring").
       Remotive memakai gaya ini, dan boilerplate promosinya berada di atas
       heading sehingga ikut terbuang.
    3. **Kalimat ber-penanda syarat** ("proficient in", "experience with").
       Kalibrr menulis syarat sebagai daftar butir tanpa heading, sehingga
       tingkat 2 tidak menemukan apa pun di sana.

    Bila ketiganya kosong, hasilnya kosong — bukan tebakan.
    """
    judul = title or ""

    bagian = requirement_section(description)
    if bagian:
        hasil = match_skills(judul, _drop_device_sentences(bagian))
        if hasil:
            return hasil

    sinyal = requirement_sentences(description)
    if sinyal:
        hasil = match_skills(judul, _drop_device_sentences(sinyal))
        if hasil:
            return hasil

    return match_skills(judul)


# Syarat perangkat, bukan kemampuan. "Content Reviewer" menulis "a reliable
# computer and a smartphone (Android 5.0, iOS 14 or higher)"; tanpa penyaring
# ini lowongan menulis konten mendapat skill ``android`` dan ``ios``.
DEVICE_WORDS = re.compile(
    r"\b(smartphone|phone|tablet|laptop|computer|device|equipment|headset|"
    r"webcam|monitor|hardware|internet connection|broadband|bandwidth)\b",
    re.IGNORECASE,
)


def _drop_device_sentences(text: str) -> str:
    """Buang kalimat yang membicarakan perangkat, bukan kemampuan.

    Pencocokan tetap dilakukan pada bagian syarat; yang dibuang hanya kalimat
    yang jelas menyebut perangkat. "Linux server experience" tetap lolos karena
    tidak memuat kata perangkat.
    """
    if not text:
        return ""
    kalimat = re.split(r"(?<=[.!?])\s+", text)
    tersisa = [k for k in kalimat if not DEVICE_WORDS.search(k)]
    return " ".join(tersisa)


# Kalimat yang menyatakan syarat secara eksplisit. Dipakai hanya bila deskripsi
# tidak punya heading syarat (lihat `requirement_section`).
REQUIREMENT_CUE = re.compile(
    r"\b(experience (?:with|in|using)|proficien\w* in|knowledge of|"
    r"familiar\w* with|skilled (?:in|with)|expertise in|hands-on|"
    r"must have|required|requirements?|"
    r"strong (?:understanding|knowledge) of|ability to use|comfortable with|"
    r"working knowledge of|background in|you have|you know)\b",
    re.IGNORECASE,
)


def requirement_sentences(description: str | None) -> str | None:
    """Kalimat yang memuat penanda syarat, atau ``None`` bila tidak ada.

    Dipakai untuk sumber yang menulis syarat sebagai butir tanpa heading —
    Kalibrr menyajikan "Proficient in at least one programming language such as
    Golang, C++, C, or Python" tanpa judul bagian di atasnya.
    """
    if not description:
        return None

    teks = " ".join(description.split())
    terpilih = [
        kalimat
        for kalimat in re.split(r"(?<=[.!?])\s+", teks)
        if REQUIREMENT_CUE.search(kalimat)
    ]
    return " ".join(terpilih) if terpilih else None


# Singkatan yang bisa berarti beberapa hal, walau kebetulan ada di kamus.
# "REST" bisa berarti REST API atau istirahat; "QC" bisa Quality Control atau
# Quick Check. Yang ambigu dikirim ke AI fallback hanya di PRD-07.
# "sql" dan "api" TIDAK termasuk: keduanya istilah yang jelas di iklan kerja.
AMBIGUOUS_ABBREVIATIONS = frozenset({
    "rest", "rpc", "qc", "qa", "ml", "ai", "ux", "ui", "db", "os", "cd", "ci",
    "sdk", "ide", "cms", "crm", "erp",
})


def is_ambiguous(candidate: str) -> bool:
    """True bila kandidat skill terlalu lemah dan layak dikirim ke AI fallback.

    Kandidat dianggap ambigu bila tidak dikenal kamus, bila berupa singkatan
    pendek yang bisa berarti beberapa hal ("RPC", "REST"), atau bila terdaftar
    di ``AMBIGUOUS_ABBREVIATIONS``. PRD-07 memakai ini untuk memutuskan apakah
    AI perlu dipanggil — bukan PRD-03, yang tidak boleh memanggil layanan
    eksternal sama sekali (R-03-14).
    """
    kunci = (candidate or "").strip().lower()
    if not kunci:
        return True
    if kunci in AMBIGUOUS_ABBREVIATIONS:
        return True
    if kunci in set(load_dictionary()["skills"]) or kunci in _aliases():
        return False
    # Singkatan pendek tanpa padanan kamus: hampir pasti ambigu.
    if len(kunci) <= 4 and kunci.isalpha():
        return True
    return False


FILTERS = {
    "skill_list": normalize_skills,
}
