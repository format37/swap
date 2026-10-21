"""Tables. The conventions are ADR-0002: plural snake_case, uuid keys, timestamptz."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# One naming convention, so autogenerate and hand-written downgrades agree on the
# name of every constraint.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # SQLAlchemy's documented way to map types; it is read once, never mutated.
    type_annotation_map = {datetime: DateTime(timezone=True)}  # noqa: RUF012


def one_of(column: str, values: type[StrEnum]) -> str:
    """The CHECK that keeps a text status column to its enum's values (ADR-0002)."""
    listed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({listed})"


class User(Base):
    """Someone who has opened the app or pressed /start (Q-B11)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(Text)
    # Telegram's interface language, refreshed at every contact.
    language_code: Mapped[str | None] = mapped_column(Text)
    # The language picked in the app. NULL means "follow language_code" (ADR-0009).
    locale: Mapped[str | None] = mapped_column(Text)
    # Whether the bot may write to them: they pressed /start, or initData said so.
    can_message: Mapped[bool] = mapped_column(default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# A username belongs to one account at a time, whatever its case.
Index(
    "ix_users_lower_username",
    func.lower(User.username),
    unique=True,
    postgresql_where=User.username.is_not(None),
)


class AuthSession(Base):
    """One app launch's bearer token, stored as its SHA-256 only (ADR-0011)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(index=True)


class ServiceHeartbeat(Base):
    """A service's last sign of life. api's /healthz reports the worker's (ADR-0005)."""

    __tablename__ = "service_heartbeats"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    beat_at: Mapped[datetime]


class LinkStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DECLINED = "declined"
    REMOVED = "removed"


class Link(Base):
    """One row per pair of users, whatever happened between them (ADR-0002, ADR-0012).

    A request by invite or by @username is `pending`, with `requested_by` the one who
    asked. The pair keeps this row through declines, breaks and new requests.
    """

    __tablename__ = "links"
    __table_args__ = (
        UniqueConstraint("user_lo_id", "user_hi_id"),
        CheckConstraint("user_lo_id < user_hi_id", name="ordered_pair"),
        CheckConstraint("requested_by IN (user_lo_id, user_hi_id)", name="requested_by_pair"),
        CheckConstraint(one_of("status", LinkStatus), name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # The unique pair's index covers user_lo_id.
    user_lo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_hi_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # When the link was established: the date the lists show (FR-1.3).
    accepted_at: Mapped[datetime | None]
    # Starts the requester's 7-day cooldown (FR-1.2, Q-E1).
    declined_at: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Invite(Base):
    """A one-time bot link, t.me/<bot>?start=inv_<token> (ADR-0012).

    Only the token's SHA-256 is kept, so a database read hands out no working invite.
    """

    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class NotificationStatus(StrEnum):
    """Where a message stands with Telegram (ADR-0014)."""

    PENDING = "pending"
    SENT = "sent"
    # Not sent, and never will be: the bot may not write to the recipient.
    SKIPPED = "skipped"
    # Telegram refused it for good, or every attempt failed.
    FAILED = "failed"


class Notification(Base):
    """One message to one person: the Telegram outbox (ADR-0014).

    It holds data, not text. The worker words it in the recipient's language when it
    sends it.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(one_of("tg_status", NotificationStatus), name="tg_status"),
        # What the outbox sweep looks for every few seconds.
        Index(
            "ix_notifications_due",
            "next_attempt_at",
            postgresql_where=text("tg_status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Also the key of its words in swap/i18n.py, such as "link.requested".
    type: Mapped[str] = mapped_column(Text)
    # What the words need: names, amounts as strings. Never payment details.
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # The card «Открыть» opens, such as link_<uuid> (ADR-0013).
    target: Mapped[str | None] = mapped_column(Text)
    tg_status: Mapped[str] = mapped_column(Text, server_default=NotificationStatus.PENDING.value)
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    next_attempt_at: Mapped[datetime] = mapped_column(server_default=func.now())
    tg_message_id: Mapped[int | None] = mapped_column(BigInteger)
    # Why the last attempt failed, for whoever reads the table.
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
