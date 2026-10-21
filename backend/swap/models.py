"""Tables. The conventions are ADR-0002: plural snake_case, uuid keys, timestamptz."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

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


def asset_check(column: str) -> str:
    """ISO 4217 codes and the stablecoins (ADR-0002). Which ones are allowed is config."""
    return f"{column} ~ '^[A-Z]{{3,5}}$'"


def country_check(column: str) -> str:
    return f"{column} ~ '^[A-Z]{{2}}$'"


# Money is numeric(18,2), and Decimal in Python (ADR-0002).
MONEY = Numeric(18, 2)


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
    # An IANA zone from the device, such as Asia/Tbilisi. Dates in orders and deals are
    # calendar dates in it (Q-B17).
    tz: Mapped[str | None] = mapped_column(Text)
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


class PaymentKind(StrEnum):
    """How money moves, one set for both sides (ADR-0016): an order's payout methods, and
    the kinds of saved payment details (ADR-0010)."""

    CARD = "card"
    # A transfer to a phone number, such as Russia's SBP.
    PHONE = "phone"
    BANK = "bank"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class OrderStatus(StrEnum):
    OPEN = "open"
    # The remainder fell below the smallest deal (Q-B5).
    FULFILLED = "fulfilled"
    # The author closed the remainder (FR-2.5).
    CLOSED = "closed"
    EXPIRED = "expired"


def _kinds_check(column: str) -> str:
    listed = ", ".join(f"'{kind}'" for kind in PaymentKind)
    return f"cardinality({column}) > 0 AND {column} <@ ARRAY[{listed}]::text[]"


class Order(Base):
    """An intent: «I give X here, between these dates, and want Y there» (§5, ADR-0016).

    Who sees it is a query over active links (§3): the author always; anyone else only
    while it is open, through an active link, and when they are on its list, if it has one.
    """

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(asset_check("give_currency"), name="give_currency"),
        CheckConstraint(country_check("give_country"), name="give_country"),
        CheckConstraint("amount_min > 0 AND amount_min <= amount_max", name="amounts"),
        CheckConstraint(
            "amount_remaining >= 0 AND amount_remaining <= amount_max", name="remaining"
        ),
        CheckConstraint("available_from <= available_until", name="window"),
        CheckConstraint(_kinds_check("payout_methods"), name="payout_methods"),
        CheckConstraint("rate_spec->>'type' IN ('fixed', 'reference')", name="rate_spec_type"),
        CheckConstraint(one_of("status", OrderStatus), name="status"),
        # What feeds and the expiry sweep look for (ADR-0002).
        Index("ix_orders_open_until", "available_until", postgresql_where=text("status = 'open'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    give_currency: Mapped[str] = mapped_column(String(8))
    give_country: Mapped[str] = mapped_column(CHAR(2))
    # The smallest single deal, and all there is (Q-B5).
    amount_min: Mapped[Decimal] = mapped_column(MONEY)
    amount_max: Mapped[Decimal] = mapped_column(MONEY)
    # Shrinks when a deal is accepted, and grows back when one is cancelled (FR-2.3).
    amount_remaining: Mapped[Decimal] = mapped_column(MONEY)
    available_from: Mapped[date]
    available_until: Mapped[date]
    payout_methods: Mapped[list[str]] = mapped_column(ARRAY(Text))
    note: Mapped[str | None] = mapped_column(Text)
    # A versioned union, validated by swap/rates.py (ADR-0004).
    rate_spec: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, server_default=OrderStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    wants: Mapped[list["OrderWant"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderWant.position"
    )


class OrderWant(Base):
    """One currency the author would take, and where (ADR-0002: rows, not JSON)."""

    __tablename__ = "order_wants"
    __table_args__ = (
        CheckConstraint(asset_check("currency"), name="currency"),
        CheckConstraint(country_check("country"), name="country"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    currency: Mapped[str] = mapped_column(String(8), primary_key=True)
    country: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    # The author's order of preference: «GEL, or else USD».
    position: Mapped[int] = mapped_column(server_default=text("0"))


class OrderVisibility(Base):
    """Who may see an order that is not for all links. No rows: all active links (§5)."""

    __tablename__ = "order_visibility"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
