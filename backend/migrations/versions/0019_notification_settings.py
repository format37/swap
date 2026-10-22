"""What each person switched off: all messages, kinds of them, someone's new orders
(QUESTIONS K1, FR-7.2).

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-22 21:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = "'orders', 'links', 'proposals', 'transfers', 'cancellations'"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("notifications_off", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "muted_kinds",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_users_muted_kinds"), "users", f"muted_kinds <@ ARRAY[{KINDS}]::text[]"
    )
    op.create_table(
        "mutes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("muted_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["muted_id"], ["users.id"], name=op.f("fk_mutes_muted_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_mutes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "muted_id", name=op.f("pk_mutes")),
    )
    op.create_index(op.f("ix_mutes_muted_id"), "mutes", ["muted_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_mutes_muted_id"), table_name="mutes")
    op.drop_table("mutes")
    op.drop_constraint(op.f("ck_users_muted_kinds"), "users", type_="check")
    op.drop_column("users", "muted_kinds")
    op.drop_column("users", "notifications_off")
