"""Form autentikasi dengan validasi di sisi server (R-01-11).

WTForms + Flask-WTF memberi token CSRF pada ``form.hidden_tag()`` serta pesan
validasi yang dapat ditampilkan di dekat field terkait.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from .service import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class RegisterForm(FlaskForm):
    name = StringField("Nama (opsional)", validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(message="Email wajib diisi."), Email(message="Format email tidak valid."), Length(max=255)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password wajib diisi."),
            Length(
                min=MIN_PASSWORD_LENGTH,
                max=MAX_PASSWORD_LENGTH,
                message=f"Password minimal {MIN_PASSWORD_LENGTH} karakter.",
            ),
        ],
    )
    submit = SubmitField("Buat akun")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(message="Email wajib diisi."), Email(message="Format email tidak valid.")])
    password = PasswordField("Password", validators=[DataRequired(message="Password wajib diisi.")])
    remember = BooleanField("Ingat saya")
    submit = SubmitField("Masuk")


class LogoutForm(FlaskForm):
    """Form kosong untuk logout via POST, agar aksi mengubah sesi terlindungi CSRF."""

    submit = SubmitField("Keluar")
