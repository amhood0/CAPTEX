"""Verify fresh installs and non-destructive adoption of the original database."""
from contextlib import closing
import sqlite3
import subprocess
import sys
import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from app.database import Base
from app.migrate import migrate, migration_config


def test_fresh_migration_and_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    assert migrate(url) is None
    engine = create_engine(url)
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    command.check(migration_config(url))
    command.downgrade(migration_config(url), "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.upgrade(migration_config(url), "head")
    engine.dispose()


def test_adopt_preserves_data_and_backs_up(tmp_path):
    path = tmp_path / "legacy.db"
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(Base.metadata.tables["capabilities"].insert().values(name="Keep me", category="Test"))
    engine.dispose()
    backup = migrate(url)
    assert backup and backup.exists()
    for database in [path, backup]:
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT name FROM capabilities").fetchone()[0] == "Keep me"
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "001_initial"


def test_unknown_schema_is_not_stamped(tmp_path):
    path = tmp_path / "unknown.db"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE valuable_data (value TEXT)")
    with pytest.raises(RuntimeError, match="differs"):
        migrate(f"sqlite:///{path}")
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("valuable_data",)]


def test_import_does_not_create_database(tmp_path):
    path = tmp_path / "must-not-exist.db"
    environment = dict(os.environ, DATABASE_URL=f"sqlite:///{path}")
    subprocess.run([sys.executable, "-c", "import app.main"], env=environment, check=True)
    assert not path.exists()
