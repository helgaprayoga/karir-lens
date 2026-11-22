"""Route asisten AI (PRD-08).

Lapisan HTTP saja: membaca pertanyaan, memanggil service, membungkus hasilnya
sesuai kontrak PRD-F04 §4.1. Tidak ada penyusunan konteks maupun pemanggilan
DeepSeek di sini.
"""

from __future__ import annotations

from flask import current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from core.errors import AppError

from . import bp, service

# Saran pertanyaan untuk pengguna baru. Bukan jawaban, hanya pembuka — dan
# semuanya dapat dijawab dari data yang tersimpan.
SUGGESTIONS = (
    "Skill apa yang paling banyak diminta?",
    "Lowongan data analyst yang tersedia?",
    "Bagaimana sebaran gaji untuk backend engineer?",
    "Kategori lowongan apa saja yang ada?",
)


def klien_atas_permintaan():
    """Klien DeepSeek sesuai konfigurasi, atau ``None`` bila belum diatur.

    Dibangun per permintaan, bukan disimpan di level modul: konfigurasi dapat
    berubah tanpa restart, dan test menyuntikkan tiruan lewat ``app.config``.
    Dipakai bersama oleh route di sini dan ``app/api/routes.py`` agar keduanya
    memakai aturan yang sama.
    """
    from core.external.deepseek import from_settings

    tiruan = current_app.config.get("DEEPSEEK_CLIENT")
    if tiruan is not None:
        return tiruan
    return from_settings(current_app.config["SETTINGS"])


@bp.get("")
@bp.get("/")
@login_required
def index():
    """``/assistant`` — halaman percakapan (R-08-01).

    Riwayat hanya hidup di memori halaman (R-F04-14); tidak ada muatan awal
    selain saran pertanyaan.
    """
    return render_template(
        "assistant/index.html",
        messages=[],
        suggestions=list(SUGGESTIONS),
        error=None,
    )


@bp.post("/ask")
@login_required
def ask():
    """Endpoint cadangan di bawah blueprint ini.

    Endpoint yang dipakai halaman adalah ``POST /api/assistant``
    (``app/api/routes.py``), sesuai kontrak PRD-F04 §4.1. Route ini disediakan
    agar blueprint ``assistant`` tetap dapat diuji dan dipakai sendiri tanpa
    bergantung pada blueprint ``api`` yang sebagian besar diisi PRD-09.
    """
    data = request.get_json(silent=True) or {}
    pertanyaan = data.get("message") if isinstance(data, dict) else None

    if not pertanyaan or not str(pertanyaan).strip():
        return jsonify({"error": {"code": "VALIDATION_ERROR",
                                  "message": "Tulis pertanyaan terlebih dahulu."}}), 400

    batas = int(current_app.config["SETTINGS"].ai_daily_limit or 20)
    try:
        hasil = service.ask(
            str(pertanyaan),
            current_user.id,
            client=klien_atas_permintaan(),
            batas_harian=batas,
        )
    except AppError as error:
        return jsonify({"error": error.to_dict()}), error.status
    except Exception:  # noqa: BLE001 - jangan bocorkan detail internal
        current_app.logger.exception("Asisten gagal menjawab")
        return jsonify({"error": {"code": "ASSISTANT_FAILED",
                                  "message": "Asisten sedang tidak dapat menjawab. Coba lagi."}}), 502

    return jsonify({"data": hasil})
