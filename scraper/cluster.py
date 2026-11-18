"""Job batch clustering dan insight (PRD-05).

Dijalankan sebagai proses terpisah, tidak pernah dari request web. Diisi pada
PRD-05.
"""

from __future__ import annotations


def run() -> int:
    """TF-IDF -> PCA -> KMeans, simpan ke ``clusters`` dan ``jobs.cluster_id``."""
    raise NotImplementedError("Diisi pada PRD-05 (clustering).")
