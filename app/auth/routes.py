"""Route autentikasi.

Lapisan HTTP saja: membaca form, memanggil service, mengatur sesi, memilih
template. Aturan validasi dan hashing tinggal di ``service``.
"""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from core.errors import AppError

from . import bp, service
from .forms import LoginForm, RegisterForm


def _safe_next(target: str | None) -> str:
    """Hanya izinkan redirect internal agar tidak menjadi open redirect."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("main.index")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user_data = service.register(form.email.data, form.password.data, form.name.data)
        except AppError as error:
            flash(error.message, "error")
        else:
            login_user(service.User(user_data))
            flash("Akun berhasil dibuat. Selamat datang di KarirLens.", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/register.html", form=form), 200 if request.method == "GET" else 400


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = service.authenticate(form.email.data, form.password.data)
        if user is None:
            # Pesan seragam agar tidak membocorkan email mana yang terdaftar.
            flash("Email atau password salah.", "error")
            return render_template("auth/login.html", form=form), 401

        login_user(user, remember=bool(form.remember.data))
        flash("Berhasil masuk.", "success")
        return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/login.html", form=form), 200 if request.method == "GET" else 400


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("main.index"))
