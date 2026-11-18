"""CLI pipeline data KarirLens (R-02-09, PRD-02 §4.2).

Perintah:
    python -m scraper run --source dealls|kalibrr|remotive|all
    python -m scraper cluster

Orkestrasi berada di ``runner.py`` dan ``cluster.py``. Diisi pada PRD-02 dan
PRD-05.
"""

from __future__ import annotations

import argparse
from typing import Sequence

SOURCES = ("dealls", "kalibrr", "remotive", "all")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scraper",
        description="Pipeline data KarirLens: pengambilan lowongan dan clustering.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Ambil lowongan dari sumber.")
    run_parser.add_argument("--source", choices=SOURCES, default="all")
    run_parser.add_argument("--pages", type=int, default=5, help="Batas halaman per sumber.")
    run_parser.add_argument("--dry-run", action="store_true", help="Ambil tanpa menyimpan.")

    subparsers.add_parser("cluster", help="Jalankan ulang clustering dan insight.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "run":
        from . import runner

        return runner.run(source=args.source, max_pages=args.pages, dry_run=args.dry_run)

    from . import cluster

    return cluster.run()
