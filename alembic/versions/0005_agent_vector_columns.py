"""Add vector embedding columns and index to agents.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-15

Agent registry rows are now part of OpenHub's semantic memory surface. This
migration extends the existing vector column set from tasks/memory/artifacts/
messages to agents so ACN agent capability metadata can be embedded and found
through unified search.
"""
import logging

import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

VEC_DIM = 768
TARGET_TABLE = "agents"
COLUMNS = [
    ("embedding", f"F32_BLOB({VEC_DIM})"),
    ("embedding_model", "TEXT"),
    ("embedding_status", "TEXT"),
    ("embedding_error", "TEXT"),
    ("embedded_at", "TIMESTAMP"),
]

logger = logging.getLogger("alembic.runtime.migration")


def _safe_execute(sql: str, *, ignore_substrings=()):
    try:
        op.execute(sql)
    except Exception as exc:
        message = str(exc).lower()
        if any(token in message for token in ignore_substrings):
            logger.warning("agent_vector_migration_skip sql=%s reason=%s", sql, exc)
            return
        raise


def upgrade() -> None:
    for column_name, column_type in COLUMNS:
        _safe_execute(
            f"ALTER TABLE {TARGET_TABLE} ADD COLUMN {column_name} {column_type}",
            ignore_substrings=("duplicate column name",),
        )

    _safe_execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TARGET_TABLE}_embedding "
        f"ON {TARGET_TABLE} (libsql_vector_idx(embedding, 'metric=cosine'))",
        ignore_substrings=(
            "no such function",
            "libsql_vector_idx",
            "syntax error",
            "unknown function",
            "vector index",
            "global metadata",
        ),
    )


def downgrade() -> None:
    _safe_execute(
        f"DROP INDEX IF EXISTS idx_{TARGET_TABLE}_embedding",
        ignore_substrings=("no such index",),
    )
