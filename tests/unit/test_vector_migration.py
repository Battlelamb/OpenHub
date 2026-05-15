"""Tests for Alembic migration 0003: vector columns + DiskANN index.

Covers VEC-01 (foundation) acceptance: migration adds the embedding columns
to all 4 target tables on local SQLite, is safely idempotent, and skips the
libsql_vector_idx CREATE INDEX gracefully when running against plain SQLite.
"""
import os
import tempfile

import pytest
from alembic import command
from alembic.config import Config


TARGET_TABLES = ["shared_memory", "tasks", "artifacts", "messages", "agents"]
EXPECTED_COLUMNS = [
    "embedding",
    "embedding_model",
    "embedding_status",
    "embedding_error",
    "embedded_at",
]


def _build_alembic_config(db_path: str) -> Config:
    """Build an Alembic Config pointed at a temp SQLite file."""
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    cfg = Config(os.path.join(project_root, "alembic.ini"))
    cfg.set_main_option(
        "script_location", os.path.join(project_root, "alembic")
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


@pytest.fixture()
def temp_sqlite_db(monkeypatch):
    """Create a temp SQLite DB and point app Settings at it.

    alembic/env.py overrides sqlalchemy.url with settings.db_path, so we must
    patch the env var (and reload the cached settings) for the migration to
    target our isolated DB instead of the conftest one.
    """
    fd, path = tempfile.mkstemp(prefix="vec-mig-", suffix=".db")
    os.close(fd)
    monkeypatch.setenv("AGENTHUB_DB_PATH", path)
    monkeypatch.delenv("AGENTHUB_TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTHUB_TURSO_AUTH_TOKEN", raising=False)

    # Reset cached settings so env.py picks up the new path on import-time read.
    from app import config as _config

    _config.settings = _config.Settings()
    try:
        yield path
    finally:
        _config.settings = _config.Settings()
        if os.path.exists(path):
            os.remove(path)


def _table_columns(db_path: str, table: str):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}
    finally:
        conn.close()


def test_upgrade_adds_columns(temp_sqlite_db):
    cfg = _build_alembic_config(temp_sqlite_db)
    command.upgrade(cfg, "head")

    for table in TARGET_TABLES:
        cols = _table_columns(temp_sqlite_db, table)
        for expected in EXPECTED_COLUMNS:
            assert expected in cols, (
                f"Column {expected!r} missing from table {table}: got {sorted(cols)}"
            )


def test_upgrade_idempotent(temp_sqlite_db):
    cfg = _build_alembic_config(temp_sqlite_db)
    command.upgrade(cfg, "head")
    # Running the migration a second time must not raise.
    command.upgrade(cfg, "head")

    for table in TARGET_TABLES:
        cols = _table_columns(temp_sqlite_db, table)
        assert "embedding" in cols


def test_index_skipped_on_sqlite(temp_sqlite_db, caplog):
    """libsql_vector_idx is unknown on plain SQLite, so the CREATE INDEX
    statements should be caught and logged, not raised."""
    cfg = _build_alembic_config(temp_sqlite_db)
    # Should not raise even though libsql_vector_idx() does not exist on SQLite.
    command.upgrade(cfg, "head")
