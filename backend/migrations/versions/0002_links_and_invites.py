"""Links between users, and the one-time invites that start them (ADR-0002, ADR-0012).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 01:39:16.126553
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_by", sa.Uuid(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_invites_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["used_by"], ["users.id"], name=op.f("fk_invites_used_by_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invites")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invites_token_hash")),
    )
    op.create_index(op.f("ix_invites_created_by"), "invites", ["created_by"], unique=False)
    op.create_index(op.f("ix_invites_used_by"), "invites", ["used_by"], unique=False)
    op.create_table(
        "links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_lo_id", sa.Uuid(), nullable=False),
        sa.Column("user_hi_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'declined', 'removed')", name=op.f("ck_links_status")
        ),
        sa.CheckConstraint(
            "requested_by IN (user_lo_id, user_hi_id)", name=op.f("ck_links_requested_by_pair")
        ),
        sa.CheckConstraint("user_lo_id < user_hi_id", name=op.f("ck_links_ordered_pair")),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_links_requested_by_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_hi_id"], ["users.id"], name=op.f("fk_links_user_hi_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_lo_id"], ["users.id"], name=op.f("fk_links_user_lo_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_links")),
        sa.UniqueConstraint(
            "user_lo_id", "user_hi_id", name=op.f("uq_links_user_lo_id_user_hi_id")
        ),
    )
    op.create_index(op.f("ix_links_requested_by"), "links", ["requested_by"], unique=False)
    op.create_index(op.f("ix_links_user_hi_id"), "links", ["user_hi_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_links_user_hi_id"), table_name="links")
    op.drop_index(op.f("ix_links_requested_by"), table_name="links")
    op.drop_table("links")
    op.drop_index(op.f("ix_invites_used_by"), table_name="invites")
    op.drop_index(op.f("ix_invites_created_by"), table_name="invites")
    op.drop_table("invites")
