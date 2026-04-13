"""Add source column to pending_applications.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-09
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pending_applications ADD COLUMN source TEXT DEFAULT 'acn'"
    )


def downgrade() -> None:
    # SQLite does not support DROP COLUMN before 3.35.0;
    # for safety we leave the column in place on downgrade.
    pass
