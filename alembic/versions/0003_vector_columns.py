"""Add vector embedding columns and DiskANN indexes to four tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-13

This migration is the foundation for Phase 3 (Vector Database). It adds
F32_BLOB embedding columns to shared_memory, tasks, artifacts, and messages,
plus a DiskANN index on each. On plain SQLite (no Turso), F32_BLOB is parsed
as a BLOB type (libsql custom type names are tolerated by the SQLite parser),
and the libsql_vector_idx index function is unknown so the CREATE INDEX is
caught and logged. On Turso the index is created natively.

Per VEC-01 / D-01 the vector dimension is 384 to match
sentence-transformers/all-MiniLM-L6-v2.
"""
import logging

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


VEC_DIM = 384
TARGET_TABLES = ["shared_memory", "tasks", "artifacts", "messages"]
COLUMNS = [
    ("embedding", f"F32_BLOB({VEC_DIM})"),
    ("embedding_model", "TEXT"),
    ("embedding_status", "TEXT"),
    ("embedding_error", "TEXT"),
    ("embedded_at", "TIMESTAMP"),
]


logger = logging.getLogger("alembic.runtime.migration")


def _safe_execute(sql: str, *, ignore_substrings=()):
    """Run a DDL statement, swallowing errors that match ignore_substrings.

    Used for two distinct cases:
      1. Idempotent ADD COLUMN: tolerate "duplicate column name" on re-runs.
      2. CREATE INDEX with libsql_vector_idx on plain SQLite: tolerate the
         "no such function" error so local development still works.
    """
    try:
        op.execute(sql)
    except sa.exc.OperationalError as exc:
        message = str(exc).lower()
        if any(token in message for token in ignore_substrings):
            logger.warning("vector_migration_skip sql=%s reason=%s", sql, exc)
            return
        raise


def upgrade() -> None:
    # Step 1: add columns. ALTER TABLE ADD COLUMN is idempotent via try/except.
    for table in TARGET_TABLES:
        for column_name, column_type in COLUMNS:
            _safe_execute(
                f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}",
                ignore_substrings=("duplicate column name",),
            )

    # Step 2: create DiskANN indexes. On plain SQLite libsql_vector_idx is
    # unknown, so we log and skip; on Turso this creates the real index.
    for table in TARGET_TABLES:
        _safe_execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_embedding "
            f"ON {table}(libsql_vector_idx(embedding, 'metric=cosine'))",
            ignore_substrings=(
                "no such function",
                "libsql_vector_idx",
                "syntax error",
                "unknown function",
            ),
        )


def downgrade() -> None:
    # SQLite cannot DROP COLUMN reliably before 3.35 - leave columns in place.
    # We do drop the indexes for cleanliness.
    for table in TARGET_TABLES:
        _safe_execute(
            f"DROP INDEX IF EXISTS idx_{table}_embedding",
            ignore_substrings=("no such index",),
        )
