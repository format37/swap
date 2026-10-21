"""The Telegram outbox: one row per message to one person (ADR-0002, ADR-0014).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22 02:06:15.669538
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("tg_status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tg_message_id", sa.BigInteger(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tg_status IN ('pending', 'sent', 'skipped', 'failed')",
            name=op.f("ck_notifications_tg_status"),
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["users.id"],
            name=op.f("fk_notifications_recipient_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        "ix_notifications_due",
        "notifications",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("tg_status = 'pending'"),
    )
    op.create_index(
        op.f("ix_notifications_recipient_id"), "notifications", ["recipient_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_recipient_id"), table_name="notifications")
    op.drop_index(
        "ix_notifications_due",
        table_name="notifications",
        postgresql_where=sa.text("tg_status = 'pending'"),
    )
    op.drop_table("notifications")
