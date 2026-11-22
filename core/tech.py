"""Klasifikasi lowongan IT (pemfokusan produk).

KarirLens dipersempit ke lowongan IT saja. Modul ini menjawab satu pertanyaan
tunggal — "lowongan ini bagian dari IT atau bukan?" — dan sengaja **murni**:
tidak menyentuh database, jaringan, atau konfigurasi.

Bukti dari data yang sudah ada, bukan daftar karangan:

- **Kalibrr** memberi field ``function`` (mis. "IT and Software"). Bila ada dan
  tidak termasuk IT, lowongan langsung ditolak — sinyal ini lebih kuat daripada
  judul, karena berasal dari kategori yang dipilih pemasang iklan.
- **Remotive** memberi kategori di URL-nya (``/remote-jobs/software-development``).
  Kategori non-IT seperti ``writing``, ``sales``, ``customer-service`` juga
  ditolak tanpa membaca teks.
- **Dealls** tidak punya kategori andal (``categoryId`` kosong pada 17 dari 18
  lowongan yang diperiksa), sehingga hanya judul dan skill yang tersedia.

Karena Dealls hanya punya judul, aturan teks dibuat konservatif: satu kata kunci
teknis yang jelas sudah cukup, tetapi kata yang umum dipakai di luar IT
("engineer", "support", "design", "data") tidak berdiri sendiri.
"""

from __future__ import annotations

import re

# Kategori (Remotive) dan fungsi (Kalibrr) yang dianggap IT.
IT_CATEGORIES = frozenset({
    "software-development",
    "information-technology",
    "data",
    "devops",
    "engineering",
    "artificial-intelligence",
    "qa",
    "api",
    "research",
    "high-paying-software-development",
    "high-paying-engineering",
    "high-paying-project-management",
})

# Nama fungsi Kalibrr memakai bentuk berspasi ("IT and Software", "Accounting
# and Finance"). Dipetakan ke himpunan di atas agar satu daftar cukup.
CATEGORY_ALIASES = {
    "it and software": "software-development",
    "it and software development": "software-development",
    "engineering and technical": "engineering",
    "science and technology": "engineering",
    "accounting and finance": "accounting and finance",
    "hospitality and tourism": "hospitality and tourism",
    "media and creatives": "media and creatives",
    "sales and marketing": "sales and marketing",
    "general services": "general services",
    "health and medical": "health and medical",
}

# Kategori/fungsi yang jelas BUKAN IT. Dipakai untuk menolak lebih awal agar
# lowongan seperti "Content Reviewer" atau "Head Chef" tidak pernah masuk.
NON_IT_CATEGORIES = frozenset({
    "writing", "marketing", "sales", "customer-service", "finance", "legal",
    "human-resources", "medical", "education", "travel-and-hospitality",
    "project-management", "product", "design", "operations", "communications",
    "account-management", "business-development", "compliance", "supply-chain",
    "strategy", "all-others", "knowledge-management",
    "accounting and finance", "hospitality and tourism", "media and creatives",
    "sales and marketing", "general services", "health and medical",
    "customer service", "human resources", "education and training",
})

# Peran teknologi yang dikenali dari judul. Dicocokkan sebagai frasa pada judul
# yang sudah dinormalkan (huruf kecil, spasi tunggal).
TECH_TITLE_TERMS = (
    # Rekayasa perangkat lunak
    "software engineer", "software developer", "full stack", "fullstack",
    "frontend", "front end", "backend", "back end", "back-end", "front-end",
    "web developer", "web engineer", "mobile developer", "mobile engineer",
    "android developer", "ios developer", "flutter", "react native",
    "programmer", "developer", "devops", "sre", "site reliability",
    "platform engineer", "cloud engineer", "cloud architect",
    "solution architect", "solutions architect", "software architect",
    "technical lead", "tech lead", "engineering manager", "qa engineer",
    "quality assurance", "test engineer", "automation engineer",
    "security engineer", "security analyst", "penetration tester",
    "infrastructure engineer", "infrastructure architect",
    "it governance", "it risk", "it compliance", "it auditor",
    "it project manager", "it manager", "it consultant", "it analyst",
    "digital transformation", "business intelligence analyst",
    "data engineer", "data analyst", "data scientist", "data architect",
    "machine learning", "ml engineer", "ai engineer", "ai trainer",
    "business intelligence", "bi developer", "database administrator",
    "dba", "system administrator", "sysadmin", "network engineer",
    "network administrator", "it support", "it staff", "it officer",
    "helpdesk", "help desk", "technical support engineer",
    "service desk", "desktop support", "application support",
    "game developer", "game programmer", "embedded engineer",
    "firmware engineer", "hardware engineer", "robotics engineer",
    "computer vision", "nlp engineer", "prompt engineer",
    "staf it", "it support", "teknisi komputer", "administrator jaringan",
    "programmer", "webmaster", "scrum master", "product owner",
)

# Skill teknis yang menandai sebuah lowongan sebagai IT, bahkan bila judulnya
# tidak menyebut peran teknologi. Daftar ini dari kamus skill, bukan tebakan.
_TECH_SKILLS = frozenset({
    "python", "java", "javascript", "typescript", "php", "ruby", "golang",
    "go", "rust", "kotlin", "swift", "dart", "scala", "sql", "nosql",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "react", "next.js", "vue", "angular", "svelte", "node.js", "django",
    "flask", "laravel", "rails", "spring", "docker", "kubernetes", "terraform",
    "aws", "gcp", "azure", "linux", "git", "ci/cd", "microservices",
    "rest api", "graphql", "machine learning", "deep learning", "llm", "nlp",
    "tensorflow", "pytorch", "pandas", "airflow", "snowflake", "bigquery",
    "figma", "tailwind", "css", "html", "flutter", "react native",
    "android", "ios", "unity", "jenkins", "ansible", "devops",
})


def _normalize_title(title: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9+#. ]+", " ", (title or "").lower()).split())


def _category_is_it(category: str | None) -> bool | None:
    """``True``/``False`` bila kategori dikenali, ``None`` bila tidak diketahui."""
    if not category:
        return None
    kunci = category.strip().lower().replace("_", "-")
    # Nama fungsi Kalibrr berbentuk berspasi; dipetakan lebih dulu.
    kunci = CATEGORY_ALIASES.get(" ".join(kunci.replace("-", " ").split()), kunci)
    if kunci in NON_IT_CATEGORIES:
        return False
    if kunci in IT_CATEGORIES:
        return True
    return None


def _phrases() -> tuple[tuple[re.Pattern[str], str], ...]:
    """Pola frasa peran teknis dengan batas kata.

    Batas kata wajib: tanpa itu ``"it staff"`` cocok di dalam **"audit
    staff"**, dan "Tax & Audit Staff" ikut dianggap lowongan IT. Batas yang
    sama mencegah ``"dba"`` cocok di dalam kata lain.
    """
    return tuple(
        (
            re.compile(r"(?<![a-z0-9])" + re.escape(frasa) + r"(?![a-z0-9])"),
            frasa,
        )
        for frasa in TECH_TITLE_TERMS
    )


def is_it_job(
    *,
    title: str | None = None,
    category: str | None = None,
    skills: list | None = None,
    description: str | None = None,
) -> bool:
    """True bila lowongan ini termasuk IT.

    Urutan keputusan, dari bukti terkuat:

    1. **Kategori sumber.** Kalibrr ``function`` dan kategori Remotive adalah
       pernyataan platform, bukan tebakan kita. Kategori non-IT menolak
       lowongan lebih awal.
    2. **Judul.** Frasa peran teknologi ("data engineer", "backend developer").
       Kata tunggal yang terlalu umum ("engineer", "designer") tidak cukup.
    3. **Skill.** Lowongan yang judulnya tidak menyebut peran tetapi
       skill-nya jelas teknis (minimal dua skill teknis, agar satu kata
       kebetulan tidak meloloskan lowongan pemasaran).
    4. **Deskripsi** tidak dipakai: terlalu banyak prosa pemasaran, dan sudah
       dibuktikan menghasilkan salah cocok pada PRD-03.
    """
    kategori = _category_is_it(category)
    if kategori is False:
        return False

    judul = _normalize_title(title)
    if judul:
        for pola, _ in _phrases():
            if pola.search(judul):
                return True

    if kategori is True:
        return True

    teknis = [s for s in (skills or []) if str(s).lower() in _TECH_SKILLS]
    if len(teknis) >= 2:
        return True

    return False


def is_it_from_text(title: str | None, description: str | None = None) -> bool:
    """Varian untuk pemanggil yang hanya punya judul dan deskripsi.

    Skill disimpulkan dari judul/deskripsi seperti pada PRD-03, lalu dipakai
    sebagai bahan keputusan. Dipakai untuk menilai ulang data lama.
    """
    from core.skills import infer_skills

    return is_it_job(
        title=title,
        description=description,
        skills=infer_skills(title, description),
    )
