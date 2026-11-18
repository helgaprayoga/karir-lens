"""Bentuk respons JSON yang seragam (R-09-12, R-09-13).

``{"data": ..., "meta": ...}`` untuk daftar dan ``{"error": {"code","message"}}``
untuk kesalahan. Satu tempat agar web dan API tidak menyimpang.
"""

from __future__ import annotations

from flask import jsonify

from core.errors import AppError


def ok(data, meta: dict | None = None, status: int = 200):
    payload: dict[str, object] = {"data": data}
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status


def error(app_error: AppError):
    return jsonify({"error": app_error.to_dict()}), app_error.status
