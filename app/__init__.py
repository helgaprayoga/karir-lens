"""Application factory KarirLens (R-01-02).

Membuat instance Flask, memuat konfigurasi, meregistrasi seluruh blueprint,
memasang security header, dan memetakan ``AppError`` ke respons yang tepat.

Ini satu-satunya berkas yang boleh meregistrasi blueprint
(docs/ARCHITECTURE.md §4, aturan 6).
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from core import config as core_config
from core import db as core_db
from core.errors import AppError

# Harus dimuat SEBELUM ``.config`` diimpor: kelas konfigurasi mengevaluasi
# Settings.from_env() saat modul dimuat, bukan saat create_app() dipanggil.
# ``wsgi.py`` juga memuatnya, tetapi test, skrip, dan `flask --app app`
# tidak melewati wsgi.py.
core_config.load_env(core_config.PROJECT_ROOT / ".env")

from .config import CONFIG_MAP  # noqa: E402  (setelah .env dimuat)
from .extensions import csrf, login_manager  # noqa: E402
from .logging_config import configure_logging  # noqa: E402

__all__ = ["create_app"]

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def _register_blueprints(app: Flask) -> None:
    from .admin import bp as admin_bp
    from .api import bp as api_bp
    from .assistant import bp as assistant_bp
    from .auth import bp as auth_bp
    from .cv import bp as cv_bp
    from .insights import bp as insights_bp
    from .jobs import bp as jobs_bp
    from .main import bp as main_bp
    from .profile import bp as profile_bp

    for blueprint in (
        main_bp,
        auth_bp,
        jobs_bp,
        insights_bp,
        profile_bp,
        cv_bp,
        assistant_bp,
        admin_bp,
        api_bp,
    ):
        app.register_blueprint(blueprint)

    # Blueprint preview hanya ada ketika PREVIEW_UI=true (R-F01-09). Bila flag
    # mati, endpoint-nya tidak terdaftar sama sekali sehingga /styleguide 404
    # secara alami, bukan lewat pemeriksaan di dalam route.
    if app.config.get("PREVIEW_UI"):
        from .preview import bp as preview_bp

        app.register_blueprint(preview_bp)


def _register_error_handlers(app: Flask) -> None:
    def _wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        app.logger.warning("AppError %s pada %s: %s", error.code, request.path, error.message)
        if _wants_json():
            return jsonify({"error": error.to_dict()}), error.status
        return render_template("errors/error.html", error=error), error.status

    @app.errorhandler(404)
    def handle_not_found(_error):
        if _wants_json():
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Data yang dicari tidak ditemukan."}}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        app.logger.error("Kesalahan server pada %s: %s", request.path, type(error).__name__)
        if _wants_json():
            return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Terjadi kesalahan pada server."}}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def handle_too_large(_error):
        message = "Berkas yang diunggah terlalu besar."
        if _wants_json():
            return jsonify({"error": {"code": "PAYLOAD_TOO_LARGE", "message": message}}), 413
        return render_template("errors/error.html", error=AppError(message, code="PAYLOAD_TOO_LARGE", status=413)), 413


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


def _register_context(app: Flask) -> None:
    """Variabel template yang dipakai semua halaman (pola context processor)."""
    from .navigation import header_hrefs, nav_links
    from .templating import install as install_templating
    from .template_filters import FILTERS

    app.jinja_env.filters.update(FILTERS)

    # Template katalog menautkan endpoint pratinjau; di produksi endpoint itu
    # tidak terdaftar. Penerjemah ini membuat template yang sama bekerja di dua
    # track tanpa mengubah template (R-04-11).
    install_templating(app)

    # ``preview_ui`` ditentukan dari endpoint yang benar-benar terdaftar, bukan
    # dari flag konfigurasi. Alasannya sama dengan navigation.py: memanggil
    # url_for untuk endpoint yang tidak ada akan melempar BuildError. Dengan
    # cara ini template selalu aman meskipun config diubah setelah create_app.
    @app.context_processor
    def inject_navigation():
        return {
            "nav_links": nav_links(),
            "preview_ui": "preview.styleguide" in app.view_functions,
            **header_hrefs(),
        }


def create_app(config_name: str = "development") -> Flask:
    # Template dan static berada di akar repo, bukan di dalam paket ``app``.
    project_root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
        instance_relative_config=False,
    )

    # ``.env`` sudah dimuat di tingkat modul (lihat atas berkas) supaya kelas
    # konfigurasi membaca nilai yang benar saat diimpor.
    app.config.from_object(CONFIG_MAP[config_name])

    settings = app.config["SETTINGS"]
    core_config.validate_settings(settings, require_credentials=app.config["REQUIRE_CREDENTIALS"])
    core_db.configure(settings.supabase_url, settings.supabase_key)

    configure_logging(app.config["LOG_LEVEL"])

    csrf.init_app(app)
    login_manager.init_app(app)

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_context(app)

    return app
