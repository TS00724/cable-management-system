"""Shared atomic rate-limit windows.

Revision ID: 200000000003
Revises: 200000000002
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "200000000003"
down_revision: str | Sequence[str] | None = "200000000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_windows",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start_epoch", sa.BigInteger(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at_epoch", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("key_hash", "window_start_epoch"),
    )
    op.create_index(
        "ix_rate_limit_window_expires",
        "rate_limit_windows",
        ["expires_at_epoch"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_window_expires", table_name="rate_limit_windows")
    op.drop_table("rate_limit_windows")
