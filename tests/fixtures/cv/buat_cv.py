"""Membuat fixture CV sintetis (PDF dan DOCX) untuk pengujian PRD-07.

Berkas dibuat ulang setiap kali test berjalan, bukan disimpan di repo: isinya
sengaja buatan, dan menyimpannya sebagai biner hanya menambah berat repository
tanpa memberi jaminan apa pun.
"""

from __future__ import annotations

from pathlib import Path

TEKS_CV = """\
Budi Santoso
Backend Engineer

Pengalaman
- 3 tahun membangun layanan dengan Python dan Django.
- Mengelola basis data PostgreSQL dan Redis.
- Menulis pipeline data memakai SQL dan Airflow.
- Deployment dengan Docker dan Kubernetes di AWS.

Pendidikan
S1 Teknik Informatika
"""


def buat_pdf(path: Path, teks: str = TEKS_CV) -> Path:
    """PDF sederhana berisi ``teks``, dibuat tanpa pustaka tambahan.

    PDF minimal ditulis langsung: satu halaman, satu font Helvetica, teks
    per baris. Ini cukup untuk memastikan ``pypdf`` menemukan lapisan teks —
    yang diuji adalah ekstraksi kita, bukan kemampuan membuat PDF.
    """
    baris = teks.splitlines() or [""]
    isi = ["BT", "/F1 11 Tf", "14 TL", "40 780 Td"]
    for b in baris:
        aman = b.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        isi.append(f"({aman}) Tj")
        isi.append("T*")
    isi.append("ET")
    aliran = "\n".join(isi).encode("latin-1", "replace")

    objek = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(aliran)).encode() + b" >>\nstream\n" + aliran + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    keluar = bytearray(b"%PDF-1.4\n")
    offset = []
    for i, isi_obj in enumerate(objek, start=1):
        offset.append(len(keluar))
        keluar += f"{i} 0 obj\n".encode() + isi_obj + b"\nendobj\n"

    xref = len(keluar)
    keluar += f"xref\n0 {len(objek) + 1}\n".encode()
    keluar += b"0000000000 65535 f \n"
    for pos in offset:
        keluar += f"{pos:010d} 00000 n \n".encode()
    keluar += (
        f"trailer\n<< /Size {len(objek) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()

    path.write_bytes(bytes(keluar))
    return path


def buat_docx(path: Path, teks: str = TEKS_CV) -> Path:
    """DOCX berisi paragraf dan satu tabel, seperti CV pada umumnya."""
    import docx

    dokumen = docx.Document()
    for b in teks.splitlines():
        if b.strip():
            dokumen.add_paragraph(b)

    # Tabel dipakai CV untuk kolom pengalaman; isinya bukan paragraf, jadi
    # ekstraksi harus membacanya terpisah.
    tabel = dokumen.add_table(rows=1, cols=2)
    tabel.rows[0].cells[0].text = "Skill"
    tabel.rows[0].cells[1].text = "Terraform"

    dokumen.save(str(path))
    return path
