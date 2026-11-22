"""PRD-05 §7.1: clustering TF-IDF/PCA/KMeans.

Data uji sengaja dibuat dengan tiga kelompok yang jelas berbeda, sehingga hasil
clustering dapat diperiksa tanpa menebak. Tanpa database dan tanpa jaringan.
"""

from __future__ import annotations

import pytest

from scraper import cluster

BACKEND = [
    {"id": 1, "title": "Backend Engineer Python",
     "description": "Membangun API dengan python dan sql, mengelola database.",
     "skills": ["python", "sql", "api"]},
    {"id": 2, "title": "Backend Developer Python",
     "description": "Mengembangkan service python, query sql, desain API.",
     "skills": ["python", "sql", "api"]},
    {"id": 3, "title": "Python Backend Engineer",
     "description": "API python, database sql, service backend.",
     "skills": ["python", "sql", "api"]},
    {"id": 4, "title": "Backend Python API",
     "description": "Python dan sql untuk API backend dan database.",
     "skills": ["python", "sql", "api"]},
]

FRONTEND = [
    {"id": 5, "title": "Frontend React Developer",
     "description": "Membangun antarmuka dengan react, css, dan javascript.",
     "skills": ["react", "css", "javascript"]},
    {"id": 6, "title": "Frontend Engineer React",
     "description": "Antarmuka react dengan css dan javascript modern.",
     "skills": ["react", "css", "javascript"]},
    {"id": 7, "title": "React Frontend Developer",
     "description": "CSS dan javascript untuk antarmuka react.",
     "skills": ["react", "css", "javascript"]},
    {"id": 8, "title": "Frontend React CSS",
     "description": "React, css, javascript, antarmuka pengguna.",
     "skills": ["react", "css", "javascript"]},
]

DEVOPS = [
    {"id": 9, "title": "DevOps Engineer Kubernetes",
     "description": "Mengelola kubernetes, docker, dan pipeline deploy.",
     "skills": ["kubernetes", "docker", "terraform"]},
    {"id": 10, "title": "DevOps Docker Terraform",
     "description": "Docker dan kubernetes untuk infrastruktur terraform.",
     "skills": ["kubernetes", "docker", "terraform"]},
    {"id": 11, "title": "Kubernetes DevOps",
     "description": "Terraform, docker, kubernetes, infrastruktur awan.",
     "skills": ["kubernetes", "docker", "terraform"]},
    {"id": 12, "title": "Infrastructure DevOps Docker",
     "description": "Kubernetes dan docker dengan terraform.",
     "skills": ["kubernetes", "docker", "terraform"]},
]

SEMUA = BACKEND + FRONTEND + DEVOPS


# --- R-05-01: vektorisasi ------------------------------------------------

def test_tfidf_vectorization() -> None:
    """Vektor TF-IDF terbentuk dari gabungan judul, skill, dan deskripsi."""
    matrix, vectorizer, dipakai = cluster.build_matrix(SEMUA)

    assert matrix is not None
    assert matrix.shape[0] == len(SEMUA), "satu baris per lowongan"
    assert matrix.shape[1] > 0
    assert len(dipakai) == len(SEMUA)

    istilah = set(vectorizer.get_feature_names_out())
    # Skill dipakai sebagai fitur, dan bigram ikut terbentuk.
    assert "python" in istilah
    assert any(" " in t for t in istilah), "bigram harus ada"


def test_empty_text_yields_empty_matrix() -> None:
    """Lowongan tanpa teks tidak menghasilkan matriks palsu."""
    matrix, vectorizer, dipakai = cluster.build_matrix(
        [{"id": 1, "title": "", "description": None, "skills": []}]
    )
    assert matrix is None
    assert dipakai == []


def test_stopwords_removed_from_features() -> None:
    """Stopword Indonesia tidak menjadi fitur."""
    matrix, vectorizer, _ = cluster.build_matrix(SEMUA)
    istilah = set(vectorizer.get_feature_names_out())

    for kata in ("yang", "dan", "untuk", "dengan"):
        assert kata not in istilah, f"stopword {kata!r} lolos"


# --- R-05-02: PCA sebelum KMeans ----------------------------------------

def test_pca_applied_before_kmeans() -> None:
    """PCA mengurangi dimensi menjadi `n_components`."""
    matrix, _, _ = cluster.build_matrix(SEMUA)
    hasil = cluster.reduce_dimensions(matrix, n_components=2)

    assert hasil.shape[0] == matrix.shape[0]
    assert hasil.shape[1] == 2


def test_pca_skipped_for_tiny_feature_set() -> None:
    """PCA dilewati bila fitur lebih sedikit daripada komponen.

    Memaksakan PCA pada matriks kecil melempar error dan menggagalkan seluruh
    proses untuk data yang sebenarnya masih dapat dikelompokkan.
    """
    matrix, _, _ = cluster.build_matrix(BACKEND[:2])
    if matrix.shape[1] <= 2:
        assert cluster.reduce_dimensions(matrix, 2) is matrix


# --- R-05-03: label dan kata kunci --------------------------------------

def test_clustering_labels_generated() -> None:
    """Setiap cluster memiliki label dan keywords tidak kosong."""
    _, ringkasan = cluster.cluster_jobs(SEMUA, n_clusters=3)

    assert len(ringkasan["clusters"]) == 3
    for c in ringkasan["clusters"]:
        assert c["label"], "label tidak boleh kosong"
        assert c["keywords"], f"cluster {c['label']} tanpa kata kunci"
        assert c["job_count"] > 0


def test_keywords_are_distinctive() -> None:
    """Kata kunci membedakan cluster, bukan kata yang muncul di mana-mana.

    Menggunakan selisih rata-rata vektor cluster terhadap cluster lain, seperti
    acuan PRD §10.1. Tanpa itu semua cluster menampilkan kata yang sama.
    """
    _, ringkasan = cluster.cluster_jobs(SEMUA, n_clusters=3)

    himpunan = [set(c["keywords"]) for c in ringkasan["clusters"]]
    # Tiap cluster harus punya setidaknya satu kata yang tidak dipakai cluster lain.
    for i, kata in enumerate(himpunan):
        lain = set().union(*[h for j, h in enumerate(himpunan) if j != i])
        assert kata - lain, f"cluster {i} tidak punya kata pembeda"


def test_clusters_separate_the_synthetic_groups() -> None:
    """Kelompok yang jelas berbeda jatuh ke cluster berbeda.

    Bukan uji kualitas clustering pada data nyata, melainkan pemeriksaan bahwa
    alurnya benar: tiga kelompok teks yang tidak beririsan tidak boleh menyatu
    menjadi satu cluster.
    """
    berlabel, _ = cluster.cluster_jobs(SEMUA, n_clusters=3)

    kelompok = {}
    for job in berlabel:
        asal = "backend" if job["id"] in {1, 2, 3, 4} else (
            "frontend" if job["id"] in {5, 6, 7, 8} else "devops"
        )
        kelompok.setdefault(asal, set()).add(job["cluster_index"])

    for asal, cluster_ids in kelompok.items():
        assert len(cluster_ids) == 1, f"{asal} terpecah ke {cluster_ids}"

    semua_id = set().union(*kelompok.values())
    assert len(semua_id) == 3, "ketiga kelompok harus di cluster berbeda"


# --- R-05-04: satu cluster per lowongan ---------------------------------

def test_single_cluster_per_job() -> None:
    """Setiap lowongan punya tepat satu `cluster_index`."""
    berlabel, _ = cluster.cluster_jobs(SEMUA, n_clusters=3)

    for job in berlabel:
        assert isinstance(job["cluster_index"], int)
    assert len(berlabel) == len(SEMUA)


def test_job_count_sums_to_total() -> None:
    """Jumlah `job_count` sama dengan jumlah lowongan yang diproses."""
    berlabel, ringkasan = cluster.cluster_jobs(SEMUA, n_clusters=3)
    total = sum(c["job_count"] for c in ringkasan["clusters"])

    assert total == len(berlabel) == len(SEMUA)


# --- R-05-05: idempoten -------------------------------------------------

def test_clustering_idempotent() -> None:
    """Menjalankan ulang menghasilkan jumlah cluster dan pembagian sama.

    KMeans memakai `random_state=42`, sehingga hasilnya deterministik. Tanpa
    itu, setiap eksekusi bisa menghasilkan cluster berbeda dan sulit diperiksa.
    """
    _, pertama = cluster.cluster_jobs(SEMUA, n_clusters=3)
    _, kedua = cluster.cluster_jobs(SEMUA, n_clusters=3)

    assert len(pertama["clusters"]) == len(kedua["clusters"])
    label1 = sorted(c["label"] for c in pertama["clusters"])
    label2 = sorted(c["label"] for c in kedua["clusters"])
    assert label1 == label2


# --- Kasus tepi ---------------------------------------------------------

def test_fewer_jobs_than_clusters() -> None:
    """Jumlah cluster diturunkan bila lowongan lebih sedikit.

    KMeans melempar error bila diminta lebih banyak cluster daripada sampel;
    data 3 lowongan bukan alasan menggagalkan proses.
    """
    berlabel, ringkasan = cluster.cluster_jobs(SEMUA[:3], n_clusters=6)

    assert len(ringkasan["clusters"]) <= 3
    assert len(berlabel) == 3


def test_empty_input() -> None:
    """Tanpa lowongan, hasilnya kosong dan tidak melempar."""
    berlabel, ringkasan = cluster.cluster_jobs([], n_clusters=3)

    assert berlabel == []
    assert ringkasan["clusters"] == []
    assert ringkasan["jobs"] == 0
