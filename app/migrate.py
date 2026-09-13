"""Initialize or upgrade the database without discarding existing records.

Run with: python -m app.migrate
Stop the application before migrating an existing database.
"""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.config import BASE_DIR, settings
from app.database import Base
from app import models  # Register tables before schema comparison.


def migration_config(url: str) -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "alembic"))
    config.attributes["database_url"] = url
    return config


def migrate(url: str) -> Path | None:
    """Back up existing SQLite data; adopt only an exact unstamped schema."""
    engine = create_engine(url)
    backup_path = None
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            unstamped = bool(tables) and "alembic_version" not in tables
            if unstamped:
                differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
                if differences:
                    raise RuntimeError("Existing schema differs from Phase 1; migration stopped without changes.")
            if engine.dialect.name == "sqlite" and tables:
                if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("Existing database has broken references; migration stopped without changes.")
        if tables and engine.dialect.name == "sqlite" and engine.url.database != ":memory:":
            path = Path(engine.url.database)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = path.with_name(f"{path.stem}.backup-{stamp}.db")
            with closing(sqlite3.connect(path)) as source, closing(sqlite3.connect(backup_path)) as target:
                source.backup(target)
        config = migration_config(url)
        if unstamped:
            command.stamp(config, "001_initial")
        command.upgrade(config, "head")
        return backup_path
    finally:
        engine.dispose()


if __name__ == "__main__":
    backup = migrate(settings.DATABASE_URL)
    print("Database is up to date.")
    if backup:
        print(f"Backup: {backup}")
