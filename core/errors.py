"""Error domain yang dipetakan ke respons HTTP oleh satu handler global.

Dilempar dari ``service.py`` dan diterjemahkan di ``app/__init__.py``, sehingga
``service.py`` tidak perlu mengenal Flask (docs/ARCHITECTURE.md §8.3).
"""

from __future__ import annotations


class AppError(Exception):
    """Kesalahan aplikasi yang aman ditampilkan ke pengguna."""

    status = 500
    code = "INTERNAL_ERROR"
    message = "Terjadi kesalahan pada server."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        self.message = message or type(self).message
        self.code = (code or type(self).code).upper()
        self.status = status or type(self).status
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ValidationError(AppError):
    status = 400
    code = "VALIDATION_ERROR"
    message = "Data yang dikirim tidak valid."


class UnauthorizedError(AppError):
    status = 401
    code = "UNAUTHORIZED"
    message = "Anda perlu masuk terlebih dahulu."


class ForbiddenError(AppError):
    status = 403
    code = "FORBIDDEN"
    message = "Anda tidak memiliki akses ke halaman ini."


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"
    message = "Data yang dicari tidak ditemukan."


class RateLimitError(AppError):
    status = 429
    code = "RATE_LIMITED"
    message = "Terlalu banyak permintaan. Coba lagi nanti."


class ExternalServiceError(AppError):
    status = 502
    code = "EXTERNAL_SERVICE_ERROR"
    message = "Layanan pendukung sedang tidak dapat diakses."
