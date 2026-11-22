"""Clustering lowongan: TF-IDF -> PCA -> KMeans (PRD-05).

Dijalankan sebagai proses terpisah (``python -m scraper cluster``), tidak
pernah dari request web (R-05-13). Alurnya mengikuti acuan di PRD §10.1
(``tabs/tab_clustering.py`` pada proyek PLN), dengan tiga penyesuaian yang
dijelaskan di masing-masing fungsi.

Fungsi di sini dapat diuji tanpa database: ``build_matrix`` dan ``cluster_jobs``
menerima daftar dict biasa. Hanya ``run()`` yang menyentuh Supabase.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Stopword Bahasa Indonesia + Inggris. Kata informal ikut dibuang karena judul
# lowongan Indonesia banyak memuatnya ("yang", "untuk", "kami"), dan kata itu
# muncul di semua cluster sehingga tidak membedakan apa pun.
STOPWORDS = frozenset({
    # Kata fungsi Inggris dua-tiga huruf. Sempat terlewat seluruhnya: hanya
    # "at" yang masuk, sehingga "or" menjadi kata kunci cluster pertama.
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does",
    "for", "from", "had", "has", "have", "he", "her", "his", "how", "if",
    "in", "into", "is", "it", "its", "me", "my", "no", "nor", "not", "of",
    "on", "or", "our", "out", "over", "she", "so", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "to", "too",
    "up", "us", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "would", "you", "your",
    # Indonesia
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "adalah",
    "akan", "atau", "juga", "dalam", "ini", "itu", "tidak", "bisa", "dapat",
    "kami", "kita", "anda", "saya", "mereka", "dia", "para", "sebagai", "oleh",
    "agar", "supaya", "karena", "jika", "bila", "saat", "setelah", "sebelum",
    "serta", "maupun", "serta", "bagi", "tentang", "secara", "lebih", "sangat",
    "harus", "wajib", "mampu", "memiliki", "mempunyai", "melakukan", "membuat",
    "kerja", "pekerjaan", "lowongan", "perusahaan", "kandidat", "posisi",
    "tanggung", "jawab", "kualifikasi", "persyaratan", "deskripsi", "benefit",
    "gaji", "lokasi", "full", "time", "part", "kontrak", "magang", "remote",
    # Inggris
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "has", "this", "that", "from", "they", "their", "them", "who", "what",
    "when", "where", "how", "why", "all", "any", "can", "may", "must", "should",
    "would", "could", "not", "but", "also", "more", "than", "into", "about",
    "job", "work", "working", "role", "team", "company", "candidate", "apply",
    "position", "responsibilities", "requirements", "qualifications", "benefits",
    "experience", "years", "year", "including", "other", "such", "well",
    # Informal
    "yg", "aja", "banget", "dgn", "utk", "tdk", "sdh", "blm", "gak", "ga",
    "dll", "dsb", "tsb", "krn", "krna", "jd", "jg", "gitu", "gini",
    # Kata kerja/imbuhan yang muncul di hampir semua deskripsi berbahasa
    # Indonesia. Dibiarkan, ia menjadi kata kunci cluster yang tidak berarti
    # apa pun — terukur: satu cluster sempat berlabel "Sistem & Memastikan & Tim".
    "sistem", "memastikan", "tim", "pengalaman", "bidang", "terkait", "sesuai",
    "meliputi", "termasuk", "merupakan", "menggunakan", "dapat", "baik",
    "lain", "lainnya", "setiap", "sesuai", "terhadap", "antara", "melalui",
    "sehingga", "namun", "tetapi", "serta", "salah", "satu", "dua", "tiga",
    "kemampuan", "menguasai", "mengerti", "memahami", "diharapkan", "dimiliki",
    "dibutuhkan", "diperlukan", "dilakukan", "dilaksanakan", "bertanggung",
    "bertanggungjawab", "bersedia", "ditempatkan", "penempatan", "bergerak",
    "membangun", "mengembangkan", "mengelola", "mengatur", "membantu",
    # Sisa kata Inggris umum dan istilah proyek yang muncul di semua cluster.
    "needs", "need", "required", "require", "strong", "good", "ability",
    "skills", "skill", "knowledge", "understanding", "responsible", "ensure",
    "develop", "build", "manage", "support", "provide", "using", "used",
    "least", "at", "one", "new", "related", "various", "based", "across",
    "per", "etc", "eg", "ie", "also", "both", "each", "every", "within",
    # Indonesia: istilah proyek dan administrasi.
    "kebutuhan", "proyek", "projek", "teknis", "pengembangan", "pekerja",
    "perusahaan", "kantor", "divisi", "departemen", "laporan", "laporan",
    "koordinasi", "koordinir", "pelaksanaan", "kegiatan", "proses", "hasil",
    "target", "waktu", "tempat", "daerah", "lokal", "nasional", "minimal",
    "maksimal", "maksimal", "mampu", "sudah", "belum", "akan", "sedang",
    # Kata kerja dan kata ganti prosa. Terukur dari data: "on your own",
    # "to own our roadmap", "ticket ownership" membuat satu cluster berlabel
    # "Developer & Person & Own" — label yang tidak menyebut satu teknologi pun.
    "own", "person", "people", "youll", "youre", "were", "well", "dont",
    "take", "takes", "make", "makes", "made", "get", "gets", "keep",
    "want", "wants", "like", "look", "looking", "join", "joining", "help",
    "helping", "bring", "brings", "come", "comes", "give", "gives", "put",
    "think", "know", "understand", "learn", "grow", "growing", "thrive",
    "love", "enjoy", "share", "shares", "shape", "shaping", "drive",
    "driving", "owning", "ownership", "yourself", "ourselves", "themselves",
})


def _teks_job(job: dict) -> str:
    """Gabungan teks yang dipakai clustering (R-05-01).

    Judul, deskripsi, dan skill digabung. Skill diulang dua kali karena ia
    sinyal paling padat: deskripsi lowongan banyak berisi prosa pemasaran,
    sedangkan daftar skill langsung menyebut teknologinya.
    """
    from core.skills import preprocess

    judul = job.get("title") or ""
    deskripsi = job.get("description") or ""
    skills = " ".join(str(s) for s in (job.get("skills") or []))
    return preprocess(f"{judul} {judul} {skills} {skills} {deskripsi}")


def build_matrix(jobs: list[dict]):
    """TF-IDF atas teks gabungan. Mengembalikan ``(matrix, vectorizer, dipakai)``.

    ``min_df=2`` membuang kata yang hanya muncul sekali — dengan ratusan
    lowongan, kata sekali-muncul hampir selalu nama perusahaan atau salah
    ketik. ``max_df=0.6`` membuang kata yang muncul di lebih dari 60% lowongan,
    karena kata seperti "developer" ada di semua cluster dan tidak membedakan
    apa pun.

    **Keduanya disesuaikan dengan jumlah dokumen.** Scikit-learn melempar
    ``max_df corresponds to < documents than min_df`` bila `min_df` (2) lebih
    besar daripada `max_df` dalam jumlah dokumen. Pada 3 dokumen, 60% berarti
    1,8 — lebih kecil dari 2. Tanpa penyesuaian, clustering gagal total justru
    saat datanya sedikit, yaitu saat admin paling butuh melihat hasilnya.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    teks = []
    dipakai = []
    for job in jobs:
        isi = _teks_job(job)
        if isi:
            teks.append(isi)
            dipakai.append(job)

    if not teks:
        return None, None, []

    jumlah = len(teks)
    # min_df tidak boleh melebihi jumlah dokumen, dan max_df (dalam dokumen)
    # harus tetap di atas min_df.
    min_df = 2 if jumlah >= 5 else 1
    max_df = max(min_df + 1, int(jumlah * 0.6)) if jumlah > 3 else jumlah

    vectorizer = TfidfVectorizer(
        stop_words=sorted(STOPWORDS),
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
        # Kata tunggal + bigram: "machine learning" dan "data engineer" adalah
        # satu konsep, dan memecahnya menjadi dua kata menghilangkan maknanya.
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#.]{1,}\b",
    )
    matrix = vectorizer.fit_transform(teks)
    return matrix, vectorizer, dipakai


def reduce_dimensions(matrix, n_components: int = 2):
    """PCA sebelum KMeans (R-05-02).

    Kurangi dimensi bila fiturnya lebih banyak daripada komponen. Bila fitur
    lebih sedikit dari ``n_components`` (dataset sangat kecil), PCA dilewati —
    memaksakannya akan melempar error dan menggagalkan seluruh proses untuk
    data yang sebenarnya masih dapat dikelompokkan.
    """
    from sklearn.decomposition import PCA

    if matrix.shape[1] <= n_components:
        return matrix
    return PCA(n_components=n_components, random_state=42).fit_transform(
        matrix.toarray()
    )


def _top_terms_per_cluster(matrix, labels, vectorizer, n_terms: int = 6) -> dict[int, list[str]]:
    """Kata paling khas per cluster, bukan kata paling umum.

    Mengikuti acuan PRD §10.1: selisih rata-rata vektor cluster terhadap
    cluster lain (``np.clip(center - others, 0, None)``). Tanpa pengurangan
    itu, setiap cluster akan menampilkan kata yang sama — kata yang muncul di
    mana-mana — dan labelnya tidak membedakan apa pun.
    """
    import numpy as np

    matrix = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    fitur = vectorizer.get_feature_names_out()
    unik = sorted(set(labels))

    pusat = {}
    for label in unik:
        anggota = matrix[np.array(labels) == label]
        if len(anggota) == 0:
            continue
        pusat[label] = anggota.mean(axis=0)

    hasil: dict[int, list[str]] = {}
    for label, center in pusat.items():
        lain = [c for l, c in pusat.items() if l != label]
        selisih = center - (np.mean(lain, axis=0) if lain else 0)
        selisih = np.clip(selisih, 0, None)
        if not selisih.any():
            # Tidak ada kata pembeda: kembalikan kata terkuat apa adanya
            # ketimbang cluster tanpa label sama sekali.
            selisih = center
        urutan = np.argsort(selisih)[::-1][:n_terms]
        hasil[label] = [str(fitur[i]) for i in urutan if selisih[i] > 0]
    return hasil


def _label(keywords: list[str], nomor: int) -> str:
    """Label yang dapat dibaca manusia dari kata kuncinya (R-05-03).

    Tiga kata teratas digabung, tetapi kata yang sudah terkandung di kata lain
    dibuang lebih dulu: daftar ["project", "project manager", "information"]
    menghasilkan "Project & Information", bukan "Project & Project Manager".

    Ini bukan nama sempurna, tetapi selalu terisi — label masuk akal lebih
    penting daripada label sempurna yang harus diketik manual setiap kali
    clustering dijalankan ulang.
    """
    if not keywords:
        return f"Kategori {nomor + 1}"

    terpilih: list[str] = []
    for kata in keywords:
        if any(kata in sudah or sudah in kata for sudah in terpilih):
            continue
        terpilih.append(kata)
        if len(terpilih) == 3:
            break

    judul = " & ".join(k.title() for k in terpilih)
    return judul[:70]


def cluster_jobs(
    jobs: list[dict], n_clusters: int = 6, pca_components: int = 2
) -> tuple[list[dict], dict]:
    """Kelompokkan lowongan. Kembalikan ``(jobs_berlabel, ringkasan)``.

    ``jobs_berlabel`` adalah salinan setiap job ditambah ``cluster_index``
    (indeks 0..n-1, bukan id database). Pemetaan ke id database dilakukan
    ``run()``, sehingga fungsi ini tetap dapat diuji tanpa Supabase.

    Jumlah cluster diturunkan bila lowongan lebih sedikit daripada
    ``n_clusters``: KMeans melempar error bila diminta lebih banyak cluster
    daripada sampel, dan data 5 lowongan bukan alasan menggagalkan proses.
    """
    from sklearn.cluster import KMeans

    matrix, vectorizer, dipakai = build_matrix(jobs)
    if matrix is None or not dipakai:
        return [], {"clusters": [], "jobs": 0}

    jumlah = max(1, min(n_clusters, len(dipakai)))
    if jumlah < 2:
        # Satu cluster berarti semua lowongan sama; labelnya tetap dibuat agar
        # admin melihat kategori tunggal alih-alih daftar kosong.
        labels = [0] * len(dipakai)
    else:
        kmeans = KMeans(n_clusters=jumlah, random_state=42, n_init=10)
        labels = kmeans.fit_predict(matrix).tolist()

    kata = _top_terms_per_cluster(matrix, labels, vectorizer)

    # Ringkasan per cluster, diurutkan menurut jumlah lowongan menurun agar
    # kategori terbesar tampil lebih dulu.
    ringkasan = []
    for nomor in sorted(set(labels)):
        anggota = [i for i, l in enumerate(labels) if l == nomor]
        keywords = kata.get(nomor, [])
        ringkasan.append(
            {
                "cluster_index": nomor,
                "label": _label(keywords, nomor),
                "keywords": keywords,
                "job_count": len(anggota),
            }
        )
    ringkasan.sort(key=lambda c: (-c["job_count"], c["cluster_index"]))

    berlabel = []
    for i, job in enumerate(dipakai):
        berlabel.append({**job, "cluster_index": labels[i]})

    return berlabel, {"clusters": ringkasan, "jobs": len(dipakai)}


def run() -> int:
    """Jalankan clustering pada seluruh lowongan, simpan idempoten (R-05-05).

    Langkahnya: baca lowongan -> cluster -> tulis ulang tabel ``clusters`` ->
    perbarui ``jobs.cluster_id``. Menjalankan dua kali menghasilkan jumlah
    cluster yang sama, bukan dua kali lipat, karena tabel ``clusters``
    dikosongkan lebih dulu dalam satu transaksi logis dan id-nya dibuat baru.
    """
    from core import config as core_config
    from core import db as core_db

    from .pipeline import persist

    core_config.load_env()
    settings = core_config.Settings.from_env()
    core_db.configure(settings.supabase_url, settings.supabase_key)
    klien = core_db.get_db()

    baris = klien.table("jobs").select("id,title,description,skills").execute().data or []
    if not baris:
        logger.warning("Tidak ada lowongan untuk di-cluster.")
        return 1

    berlabel, ringkasan = cluster_jobs(
        baris,
        n_clusters=settings.cluster_n_clusters,
        pca_components=settings.cluster_pca_components,
    )
    if not berlabel:
        logger.warning("Clustering tidak menghasilkan apa pun: teks lowongan kosong.")
        return 1

    diterapkan = persist.simpan_clusters(ringkasan["clusters"], berlabel)

    logger.info(
        "Clustering selesai: %d lowongan -> %d cluster (%d baris diperbarui).",
        ringkasan["jobs"],
        len(ringkasan["clusters"]),
        diterapkan,
    )
    for c in ringkasan["clusters"]:
        logger.info(
            "  %-40s %3d lowongan  [%s]",
            c["label"], c["job_count"], ", ".join(c["keywords"][:4]),
        )
    return 0
