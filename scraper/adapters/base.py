"""Antarmuka adapter: satu-satunya abstraksi yang layak ada di proyek ini.

Ada tiga implementasi nyata dengan kontrak sama (R-02-01); menambah sumber
keempat cukup menambah satu modul. Lihat docs/ARCHITECTURE.md §7.5.

Yang ada di kelas dasar dan TIDAK boleh diduplikasi adapter:
  - ``iter_jobs``: loop halaman, dedup ``source_url``, isolasi kegagalan satu
    halaman, dan konversi ``parse`` yang mengembalikan ``None``.
  - ``is_allowed``: diteruskan ke klien HTTP bersama.
  - ``page_url``: bentuk URL halaman; adapter hanya memberi tahu parameternya.

Yang wajib diisi adapter: ``name``, ``base_url``, ``fetch(page)``, ``parse(item)``,
dan ``page_params`` bila sumber memakai query string.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterator

from ..errors import RobotsDisallowedError, ScrapeError
from ..http import ScraperHTTP

logger = logging.getLogger(__name__)


@dataclass
class RawJob:
    """Hasil parse satu lowongan sebelum normalisasi (R-02-02).

    Field yang tidak tersedia bernilai ``None`` atau list kosong — bukan string
    palsu seperti ``"-"`` atau ``"N/A"``. Nilai palsu akan lolos ke database dan
    tampil di layar sebagai data yang seolah ada.
    """

    title: str
    source_url: str
    company_name: str | None = None
    location: str | None = None
    employment_type: str | None = None
    description: str | None = None
    skills: list[str] = field(default_factory=list)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    source_job_id: str | None = None
    posted_at: str | None = None
    # Nama sumber. Diisi adapter, dipakai runner untuk memetakan ``source_id``.
    source: str = ""

    def as_row(self, source_id: int | None = None) -> dict:
        """Bentuk yang siap disimpan ke ``jobs`` (PRD-03 mengisi ``dedup_hash``).

        ``source_id`` berasal dari tabel ``sources``; wajib diisi agar lowongan
        dapat dilacak ke asalnya. Tanpa itu seluruh baris tersimpan dengan
        ``source_id`` NULL dan relasi ke sumber hilang.
        """
        return {
            "title": self.title,
            "company_name": self.company_name,
            "location": self.location,
            "employment_type": self.employment_type,
            "description": self.description,
            "skills": list(self.skills),
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "salary_period": self.salary_period,
            "source_id": source_id,
            "source_url": self.source_url,
            "source_job_id": self.source_job_id,
            "posted_at": self.posted_at,
        }


class BaseAdapter:
    """Kontrak adapter sumber lowongan."""

    name: str = ""
    base_url: str = ""
    # Nama parameter query untuk halaman berikutnya; None berarti path-based.
    page_param: str | None = "page"
    # Jalur halaman daftar pertama, relatif terhadap base_url.
    listing_path: str = "/"
    # Jarak minimum antar permintaan ke sumber ini (R-02-04).
    min_interval: float = 1.0
    # Batas keras pengambilan halaman detail per eksekusi. Tanpa ini, satu
    # kesalahan konfigurasi (`--pages 10 --detail`) dapat menjadi ratusan
    # permintaan ke situs orang lain.
    max_detail: int = 100

    def __init__(self, http: ScraperHTTP | None = None) -> None:
        """Adapter memakai klien HTTP bersama; test menyuntikkan klien tiruan."""
        if http is None:
            from core.config import Settings

            http = ScraperHTTP(
                Settings.from_env(), self.base_url, min_interval=self.min_interval
            )
        self.http = http

    # --- wajib diisi adapter --------------------------------------------

    def fetch(self, page: int = 1) -> list[dict]:
        """Ambil satu halaman daftar; kembalikan item mentah."""
        raise NotImplementedError

    def parse(self, item: dict) -> RawJob | None:
        """Ubah satu item mentah menjadi ``RawJob``, atau ``None`` bila bukan lowongan."""
        raise NotImplementedError

    # --- opsional: halaman detail ----------------------------------------

    def detail_url(self, job: RawJob) -> str | None:
        """URL halaman detail lowongan ini, atau ``None`` bila sumber tidak punya.

        Dipakai hanya ketika ``with_detail=True``. Mengembalikan ``None`` berarti
        adapter ini tidak mendukung pengambilan detail.
        """
        return None

    def parse_detail(self, job: RawJob, html: str) -> RawJob:
        """Lengkapi ``job`` dari HTML halaman detail.

        Implementasi bawaan mengembalikan ``job`` apa adanya. Adapter yang punya
        detail mengisi deskripsi dan skill di sini.
        """
        return job

    # --- perilaku bersama ------------------------------------------------

    def is_allowed(self) -> bool:
        """True bila robots.txt mengizinkan halaman daftar (R-02-05)."""
        return self.http.is_allowed(self.listing_url(1))

    def listing_url(self, page: int = 1) -> str:
        """URL halaman daftar untuk ``page``."""
        dasar = self.base_url.rstrip("/") + self.listing_path
        if page <= 1 or not self.page_param:
            return dasar
        pemisah = "&" if "?" in dasar else "?"
        return f"{dasar}{pemisah}{self.page_param}={page}"

    def _lengkapi_detail(self, job: RawJob) -> RawJob:
        """Ambil dan terapkan halaman detail; kegagalan tidak membuang lowongan.

        ``source_url`` sengaja tidak diubah menjadi URL detail: ia identitas
        stabil yang dipakai dedup dan pembaruan (R-02-09). URL detail berdiri
        sendiri lewat ``detail_url()``.
        """
        url = self.detail_url(job)
        if not url:
            return job
        try:
            return self.parse_detail(job, self.http.get(url))
        except ScrapeError as exc:
            # Detail adalah pengayaan, bukan syarat kelayakan. Lowongan tetap
            # disimpan dengan field yang sudah terbaca dari daftar.
            logger.warning("%s: detail %s gagal, memakai data daftar: %s", self.name, url, exc)
            return job

    def iter_jobs(self, max_pages: int = 5, with_detail: bool = False) -> Iterator[RawJob]:
        """Iterasi lowongan dari beberapa halaman.

        Aturan yang dijaga di sini, bukan di tiap adapter:
          - ``source_url`` unik dalam satu eksekusi (R-02-09, acceptance §5).
          - Kegagalan satu halaman tidak membuang halaman yang sudah terbaca;
            galat dilempar setelah halaman lain selesai bila tidak ada data.
          - ``RobotsDisallowedError`` langsung dilempar — tidak ada gunanya
            melanjutkan ke halaman berikutnya.
          - ``with_detail`` mengambil halaman detail per lowongan, dibatasi
            ``max_detail``. Dedup dilakukan SEBELUM detail, sehingga lowongan
            duplikat tidak memicu permintaan detail dua kali.
        """
        if not self.is_allowed():
            raise RobotsDisallowedError(
                f"robots.txt {self.name} melarang pengambilan {self.listing_url(1)}."
            )

        dilihat: set[str] = set()
        jumlah = 0
        jumlah_detail = 0
        batas_dilaporkan = False
        galat: ScrapeError | None = None

        for page in range(1, max(1, max_pages) + 1):
            try:
                items = self.fetch(page)
            except RobotsDisallowedError:
                raise
            except ScrapeError as exc:
                galat = exc
                logger.warning("%s: halaman %d gagal: %s", self.name, page, exc)
                break

            if not items:
                # Halaman kosong menandakan daftar sudah habis.
                break

            for item in items:
                job = self.parse(item)
                if job is None or not job.source_url:
                    continue
                if job.source_url in dilihat:
                    continue
                dilihat.add(job.source_url)

                if with_detail:
                    if jumlah_detail < self.max_detail:
                        job = self._lengkapi_detail(job)
                        jumlah_detail += 1
                    elif not batas_dilaporkan:
                        batas_dilaporkan = True
                        logger.warning(
                            "%s: batas %d halaman detail tercapai; sisanya memakai "
                            "data daftar saja.",
                            self.name, self.max_detail,
                        )

                jumlah += 1
                yield job

        if jumlah == 0 and galat is not None:
            raise galat

    def __repr__(self) -> str:  # pragma: no cover - bantuan debug
        return f"<{type(self).__name__} name={self.name!r}>"
