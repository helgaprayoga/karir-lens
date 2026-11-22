"""CLI pipeline data KarirLens (R-02-09, PRD-02 §4.2).

Perintah:
    python -m scraper run --source dealls|kalibrr|remotive|all
    python -m scraper cluster

Orkestrasi berada di ``runner.py`` dan ``cluster.py``. Diisi pada PRD-02 dan
PRD-05.
"""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from core import config as core_config

SOURCES = ("dealls", "kalibrr", "remotive", "all")

# Pipeline berjalan di luar Flask; .env harus dimuat eksplisit.
core_config.load_env()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scraper",
        description="Pipeline data KarirLens: pengambilan lowongan dan clustering.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Ambil lowongan dari sumber.")
    run_parser.add_argument("--source", choices=SOURCES, default="all")
    run_parser.add_argument(
        "--pages",
        type=int,
        default=0,
        help="Batas halaman per sumber. 0 (bawaan) berarti ambil sampai daftar habis.",
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Ambil tanpa menyimpan.")
    run_parser.add_argument(
        "--detail",
        action="store_true",
        help="Ambil halaman detail tiap lowongan untuk deskripsi dan skill. "
             "Menambah satu permintaan per lowongan; bawaannya mati.",
    )
    run_parser.add_argument(
        "--all-jobs",
        action="store_true",
        help="Jangan saring lowongan IT (untuk memeriksa klasifikasi).",
    )
    run_parser.add_argument(
        "--replace",
        action="store_true",
        help="Ganti isi tabel jobs dengan hasil pengambilan ini: data lama dihapus "
             "hanya setelah pengambilan berhasil. Menjalankan tanpa flag ini "
             "menambahkan/memperbarui seperti biasa.",
    )

    subparsers.add_parser("cluster", help="Jalankan ulang clustering dan insight.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Pipeline berjalan di luar Flask, jadi `configure_logging` milik aplikasi
    # web tidak terpasang. Tanpa ini seluruh ringkasan ingestion tidak tampil.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s %(name)s: %(message)s",
        )

    if args.command == "run":
        from . import runner

        return runner.run(
            source=args.source,
            max_pages=args.pages,
            dry_run=args.dry_run,
            with_detail=args.detail,
            tech_only=not args.all_jobs,
            replace=args.replace,
        )

    from . import cluster

    return cluster.run()
