"""Ekstraksi teks CV secara lokal memakai ``pypdf`` dan ``python-docx`` (PRD-07).

**Batas privasi.** Isi CV tidak boleh ditulis ke log, pesan error, atau
exception (R-07-08). Karena itu modul ini hanya mengembalikan teks dan
melempar ``ExtractionError`` dengan pesan yang menyebut **jenis kegagalan**,
bukan isi berkas. Teks tetap berada di memori; berkas sementara dihapus oleh
``service`` di blok ``finally``.

Tidak ada jaringan di sini: PDF dan DOCX dibaca dari disk.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Batas wajar teks yang dipakai. CV yang mengekstrak jutaan karakter (mis.
# PDF hasil pindai yang salah baca) tidak berguna untuk pencocokan skill, dan
# menahannya di memori hanya membuang sumber daya.
MAX_TEXT_LENGTH = 200_000

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExtractionError(Exception):
    """Kegagalan ekstraksi dengan pesan yang aman ditampilkan ke pengguna.

    Pesannya sengaja tidak menyertakan isi berkas maupun pesan asli pustaka:
    pesan pustaka dapat memuat potongan teks CV, dan itu akan berakhir di layar
    atau log (R-07-08).
    """


def _dari_pdf(path: str) -> str:
    from pypdf import PdfReader

    try:
        pembaca = PdfReader(path)
        halaman = [h.extract_text() or "" for h in pembaca.pages]
    except Exception as exc:  # noqa: BLE001 - pustaka melempar tipe berbeda-beda
        # Jenis galat dicatat, isinya tidak.
        logger.warning("Ekstraksi PDF gagal (%s).", type(exc).__name__)
        raise ExtractionError("Berkas PDF tidak dapat dibaca.") from None
    return "\n".join(halaman)


def _dari_docx(path: str) -> str:
    import docx

    try:
        dokumen = docx.Document(path)
        bagian = [p.text for p in dokumen.paragraphs]
        # Tabel sering dipakai CV untuk kolom pengalaman; isinya bukan
        # paragraf, jadi harus dibaca terpisah atau seluruh riwayat kerja hilang.
        for tabel in dokumen.tables:
            for baris in tabel.rows:
                for sel in baris.cells:
                    if sel.text:
                        bagian.append(sel.text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ekstraksi DOCX gagal (%s).", type(exc).__name__)
        raise ExtractionError("Berkas DOCX tidak dapat dibaca.") from None
    return "\n".join(bagian)


def extract_text(path: str, content_type: str) -> str:
    """Teks dari berkas PDF atau DOCX (R-07-03).

    ``content_type`` menentukan pembaca. Tipe lain ditolak lebih awal oleh
    ``service`` sebelum berkas ditulis, jadi di sini hanya dua jenis itu yang
    ditangani — tetapi pemeriksaan tetap ada agar fungsi ini aman dipakai
    langsung.
    """
    if content_type == "application/pdf":
        teks = _dari_pdf(path)
    elif content_type == DOCX_MIME:
        teks = _dari_docx(path)
    else:
        raise ExtractionError("Format berkas tidak didukung. Gunakan PDF atau DOCX.")

    teks = (teks or "").strip()
    if not teks:
        # PDF hasil pindai tidak punya lapisan teks. Pesannya harus menjelaskan
        # itu, bukan menyalahkan berkas pengguna.
        raise ExtractionError(
            "Tidak ada teks yang dapat dibaca dari berkas ini. "
            "Bila CV Anda hasil pindai, simpan ulang sebagai PDF dengan teks "
            "atau unggah versi DOCX."
        )

    return teks[:MAX_TEXT_LENGTH]
