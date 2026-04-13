"""Widen vector embedding columns from F32_BLOB(384) to F32_BLOB(768).

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-13

Motivation
----------
Migration 0003 shipped with ``F32_BLOB(384)`` to match
``sentence-transformers/all-MiniLM-L6-v2`` (Plan 03-01 / D-01). During Phase 3
deploy prep the team decided OpenHub content is TR+EN mixed and needs a
multilingual embedding model with stronger recall than all-MiniLM-L6-v2.

Ollama's multilingual embedding models (``paraphrase-multilingual``,
``nomic-embed-text``, ``embeddinggemma``) all emit 768-dim vectors. None of
the 384-dim models in the Ollama catalog are multilingual. Rather than
swap in a weaker monolingual model, widen the column to 768 and point the
runtime at ``paraphrase-multilingual`` via the Ollama-compat OpenAIBackend.

Safety
------
Migration 0003 has not yet run against the production Turso DB at the time
this 0004 is added, so the embedding columns are either absent (on a fresh
install) or present-and-empty (if 0003 runs during the same ``alembic upgrade
head`` call that will also execute 0004). Either way, DROP COLUMN + re-ADD is
safe because there is no embedding data to migrate.

On plain SQLite (local dev / tests), ``F32_BLOB`` is parsed as a generic BLOB
with no width enforcement, so the width change is invisible. On Turso the new
width is enforced and ``vector_distance_cos`` will compare 768-float vectors.
"""
import logging

import sqlalchemy as sa
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


VEC_DIM = 768
TARGET_TABLES = ["shared_memory", "tasks", "artifacts", "messages"]


logger = logging.getLogger("alembic.runtime.migration")


def _safe_execute(sql: str, *, ignore_substrings=()):
    """Run a DDL statement, swallowing errors that match ignore_substrings.

    Mirrors the helper in 0003 so this migration is idempotent and tolerant
    of missing libsql_vector_idx on plain SQLite.
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
    for table in TARGET_TABLES:
        # 1. Drop the DiskANN index from 0003 (no-op on SQLite where
        #    libsql_vector_idx doesn't exist, silently absent).
        _safe_execute(
            f"DROP INDEX IF EXISTS idx_{table}_embedding",
            ignore_substrings=(
                "no such function",
                "no such index",
                "not found",
            ),
        )

        # 2. Drop the 384-dim column. SQLite 3.35+ and libSQL both support
        #    ALTER TABLE DROP COLUMN. The column has no user data at this
        #    point (Phase 3 has not yet emitted any embeddings to prod).
        _safe_execute(
            f"ALTER TABLE {table} DROP COLUMN embedding",
            ignore_substrings=(
                "no such column",
                "no column named embedding",
            ),
        )

        # 3. Re-add the column at the new 768-dim width. On SQLite the width
        #    hint is ignored; on Turso it is enforced by vector32(?) binding.
        _safe_execute(
            f"ALTER TABLE {table} ADD COLUMN embedding F32_BLOB({VEC_DIM})",
            ignore_substrings=("duplicate column name",),
        )

        # 4. Re-create the DiskANN index. Skipped on plain SQLite where
        #    libsql_vector_idx is not available.
        _safe_execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_embedding "
            f"ON {table} (libsql_vector_idx(embedding, 'metric=cosine'))",
            ignore_substrings=("no such function",),
        )


def downgrade() -> None:
    # Not supported: shrinking back to 384-dim would require re-embedding any
    # rows that landed on the 768-dim schema. See 0003 for the same rationale.
    raise NotImplementedError(
        "downgrade from 0004 to 0003 is not supported; recreate DB instead"
    )
