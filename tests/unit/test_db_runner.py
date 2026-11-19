"""Runner migrasi: idempotensi, deteksi perubahan berkas, dan rollback.

Tidak menyentuh database. Koneksi diganti tiruan agar alur ``cmd_migrate``
dapat diuji deterministik: migrasi yang sudah diterapkan dilewati, yang belum
dijalankan, dan kegagalan membatalkan transaksi.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "db" / "__main__.py"


@pytest.fixture(scope="module")
def runner():
    spec = importlib.util.spec_from_file_location("db_runner", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Cursor:
    def __init__(self, connection: "_Connection") -> None:
        self._connection = connection
        self._rows: list[tuple] = []

    def execute(self, sql: str, params=None):
        self._connection.executed.append((" ".join(sql.split()), params))

        if "select version, checksum" in sql:
            self._rows = list(self._connection.applied.items())
        elif "insert into schema_migrations" in sql:
            version, digest = params
            self._connection.applied[version] = digest
        elif "create table if not exists schema_migrations" in sql:
            pass
        else:
            if self._connection.fail_on and self._connection.fail_on in sql:
                raise RuntimeError("boom")
        return self

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Connection:
    def __init__(self, applied=None, fail_on=None) -> None:
        self.applied = dict(applied or {})
        self.fail_on = fail_on
        self.executed: list[tuple] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.fixture
def migrations(tmp_path, runner, monkeypatch):
    """Dua berkas migrasi tiruan, dan direktori diarahkan ke tmp_path."""
    (tmp_path / "001_first.sql").write_text("create table a (id int);", encoding="utf-8")
    (tmp_path / "002_second.sql").write_text("create table b (id int);", encoding="utf-8")
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def wire(runner, monkeypatch):
    """Sambungkan runner ke koneksi tiruan tanpa menyentuh database.

    Mengembalikan fungsi ``use(applied=..., fail_on=...)`` yang mengembalikan
    koneksi tiruan tersebut agar dapat diperiksa setelah dijalankan.
    """
    class _StubConfig:
        def describe(self) -> str:
            return "stub@host:5432/postgres (sslmode=require)"

    monkeypatch.setattr(
        runner.db_direct.DatabaseConfig,
        "from_env",
        classmethod(lambda cls: _StubConfig()),
    )

    def use(applied=None, fail_on=None):
        connection = _Connection(applied=applied, fail_on=fail_on)
        monkeypatch.setattr(runner.db_direct, "connect", lambda config=None: connection)
        return connection

    return use


# --- metadata --------------------------------------------------------------

def test_migration_files_sorted(runner, migrations) -> None:
    paths = runner.migration_files()
    assert [path.stem for path in paths] == ["001_first", "002_second"]


def test_checksum_changes_with_content(runner, migrations) -> None:
    first = migrations / "001_first.sql"
    before = runner.checksum(first)
    first.write_text("create table a (id bigint);", encoding="utf-8")
    assert runner.checksum(first) != before


def test_real_migration_is_present(runner) -> None:
    """Berkas migrasi sebenarnya harus ada agar runner tidak jalan kosong."""
    names = [path.stem for path in runner.migration_files()]
    assert "001_initial_schema" in names


# --- alur migrate ----------------------------------------------------------

def _migration_statements(connection) -> list[str]:
    """Hanya pernyataan dari berkas migrasi, bukan tabel pelacak."""
    return [
        sql
        for sql, _ in connection.executed
        if sql.startswith("create table") and "schema_migrations" not in sql
    ]


def test_applies_only_pending(runner, migrations, wire) -> None:
    connection = wire(applied={"001_first": runner.checksum(migrations / "001_first.sql")})

    code = runner.cmd_migrate()

    assert code == 0
    statements = _migration_statements(connection)
    assert any("create table b" in sql for sql in statements)
    assert not any("create table a" in sql for sql in statements)
    assert connection.applied["002_second"] == runner.checksum(migrations / "002_second.sql")


def test_second_run_skips_everything(runner, migrations, wire) -> None:
    connection = wire(applied={})

    assert runner.cmd_migrate() == 0
    assert len(connection.applied) == 2

    connection.executed.clear()
    assert runner.cmd_migrate() == 0
    assert _migration_statements(connection) == []


def test_dry_run_does_not_write(runner, migrations, wire) -> None:
    connection = wire(applied={})

    assert runner.cmd_migrate(dry_run=True) == 0
    assert _migration_statements(connection) == []
    assert connection.applied == {}


def test_failure_rolls_back(runner, migrations, wire) -> None:
    """Transaksi dibatalkan; migrasi yang gagal tidak dicatat."""
    connection = wire(applied={}, fail_on="create table b")

    code = runner.cmd_migrate()

    assert code == 1
    assert connection.rollbacks >= 1
    assert "002_second" not in connection.applied


def test_connection_always_closed(runner, migrations, wire) -> None:
    connection = wire(applied={})

    runner.cmd_migrate()

    assert connection.closed is True


# --- status ----------------------------------------------------------------

def test_status_reports_pending(runner, migrations, wire, capsys) -> None:
    wire(applied={"001_first": runner.checksum(migrations / "001_first.sql")})

    assert runner.cmd_status() == 0
    out = capsys.readouterr().out
    assert "OK     001_first" in out
    assert "BELUM  002_second" in out


def test_status_flags_modified_file(runner, migrations, wire, capsys) -> None:
    """Berkas yang berubah setelah diterapkan harus terlihat, bukan diam-diam lolos."""
    wire(applied={"001_first": "checksum-lama", "002_second": runner.checksum(migrations / "002_second.sql")})

    runner.cmd_status()
    assert "UBAH   001_first" in capsys.readouterr().out


# --- konfigurasi -----------------------------------------------------------

def test_config_requires_credentials(monkeypatch) -> None:
    from core import db_direct

    for name in ("SUPABASE_DB_HOST", "SUPABASE_DB_USER", "SUPABASE_DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError) as caught:
        db_direct.DatabaseConfig.from_env()

    assert "SUPABASE_DB_HOST" in str(caught.value)


def test_config_never_exposes_password(monkeypatch) -> None:
    from core import db_direct

    monkeypatch.setenv("SUPABASE_DB_HOST", "aws-0-ap-southeast-1.pooler.supabase.com")
    monkeypatch.setenv("SUPABASE_DB_USER", "postgres.abcdefghij")
    monkeypatch.setenv("SUPABASE_DB_PASSWORD", "rahasia-sekali")

    config = db_direct.DatabaseConfig.from_env()

    assert "rahasia-sekali" not in config.describe()
    assert config.describe().startswith("postgres.abcdefghij@aws-0-")


def test_dsn_escapes_special_password(monkeypatch) -> None:
    """Password bertanda kutip atau spasi tidak boleh merusak DSN."""
    from core import db_direct

    monkeypatch.setenv("SUPABASE_DB_HOST", "host")
    monkeypatch.setenv("SUPABASE_DB_USER", "user")
    monkeypatch.setenv("SUPABASE_DB_PASSWORD", "p@ss word'x")

    dsn = db_direct.DatabaseConfig.from_env().dsn()

    assert "p@ss" in dsn
    assert dsn.count("password=") == 1


def test_config_defaults(monkeypatch) -> None:
    from core import db_direct

    monkeypatch.setenv("SUPABASE_DB_HOST", "host")
    monkeypatch.setenv("SUPABASE_DB_USER", "user")
    monkeypatch.setenv("SUPABASE_DB_PASSWORD", "pw")
    for name in ("SUPABASE_DB_PORT", "SUPABASE_DB_NAME", "SUPABASE_DB_SSLMODE"):
        monkeypatch.delenv(name, raising=False)

    config = db_direct.DatabaseConfig.from_env()

    assert config.port == 5432
    assert config.database == "postgres"
    assert config.sslmode == "require"
