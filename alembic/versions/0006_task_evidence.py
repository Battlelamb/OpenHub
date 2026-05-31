"""Add durable task evidence table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-31

Task evidence is a private/internal persistence surface for logs, commands,
diffs, artifacts, PRs, reviews, and quality-gate outcomes. Public-safe DTOs are
introduced separately so raw labels/metadata/logs do not leak by default.
"""
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS task_evidence (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT DEFAULT '{}',
            artifact_ids TEXT DEFAULT '[]',
            outcome TEXT DEFAULT 'unknown',
            source_agent_id TEXT,
            labels TEXT DEFAULT '{}',
            metadata TEXT DEFAULT '{}',
            occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_task_evidence_task ON task_evidence(task_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_evidence_task_occurred "
        "ON task_evidence(task_id, occurred_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_task_evidence_type ON task_evidence(evidence_type)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_evidence_source "
        "ON task_evidence(source_agent_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_task_evidence_source")
    op.execute("DROP INDEX IF EXISTS idx_task_evidence_type")
    op.execute("DROP INDEX IF EXISTS idx_task_evidence_task_occurred")
    op.execute("DROP INDEX IF EXISTS idx_task_evidence_task")
    op.execute("DROP TABLE IF EXISTS task_evidence")
