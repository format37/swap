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
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
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


class PaymentMethod(Base):
    """Someone's saved payment details for one asset (ADR-0010).

    The kind and title stay in the clear, for lists and bot messages. The text is a sealed
    envelope with its mask (ADR-0004). Deleting one is a real delete: a deal keeps its own
    copy of what it used.
    """

    __tablename__ = "payment_methods"
    __table_args__ = (
        CheckConstraint(asset_check("asset"), name="asset"),
        CheckConstraint(one_of("kind", PaymentKind), name="kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    asset: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    # The sealed text; null when there is none, as for cash.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DealStatus(StrEnum):
    """Q-B1: six states a deal moves through, and three it ends in."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    LEG1_SENT = "leg1_sent"
    LEG1_RECEIVED = "leg1_received"
    LEG2_SENT = "leg2_sent"
    DISPUTED = "disputed"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Deal(Base):
    """Two counter-transfers agreed between an order's author and someone it was open to.

    Its status changes only through swap/deals.py, and every change points at the
    `events` row that records it. A trigger refuses any other change (ADR-0002, ADR-0018).
    """

    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("proposer_id <> acceptor_id", name="two_people"),
        CheckConstraint(one_of("status", DealStatus), name="status"),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('settled', 'cancelled')", name="resolution"
        ),
        # Each names one of the deal's two people: stronger than a foreign key, no index.
        *(
            CheckConstraint(
                f"{column} IS NULL OR {column} IN (proposer_id, acceptor_id)", name=column
            )
            for column in ("cancel_requested_by", "disputed_by", "resolution_by")
        ),
        # What the proposal-expiry sweep looks for (ADR-0002, ADR-0005).
        Index(
            "ix_deals_proposed_until", "expires_at", postgresql_where=text("status = 'proposed'")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    proposer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    # The order's author, who accepts or declines.
    acceptor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(Text, server_default=DealStatus.PROPOSED.value)
    # The order's rate as it was at the proposal, and the quote used: a deal never follows
    # a later change of its order (FR-3.5). Both kinds lock at the proposal in the MVP (Q-B3).
    rate_spec: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rate_base: Mapped[str] = mapped_column(String(8))
    rate_quote: Mapped[str] = mapped_column(String(8))
    rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    rate_locked_at: Mapped[datetime]
    # The counter-amount was rounded to whole units (Q-B4).
    whole: Mapped[bool] = mapped_column(server_default=false())
    # A proposal lapses at this moment (FR-4.4).
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    # A pending request to cancel after the first «Отправлено» is a field, not a state (Q-B1).
    cancel_requested_by: Mapped[uuid.UUID | None]
    disputed_by: Mapped[uuid.UUID | None]
    dispute_note: Mapped[str | None] = mapped_column(Text)
    # A dispute ends when one side proposes an outcome and the other confirms it (FR-4.6).
    resolution: Mapped[str | None] = mapped_column(Text)
    resolution_by: Mapped[uuid.UUID | None]
    # The event that recorded the latest change; the trigger checks it.
    last_event_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    legs: Mapped[list["DealLeg"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="DealLeg.seq"
    )


class DealLeg(Base):
    """One transfer of a deal. Leg 1 is whoever sends first (§5)."""

    __tablename__ = "deal_legs"
    __table_args__ = (
        UniqueConstraint("deal_id", "seq"),
        CheckConstraint("seq IN (1, 2)", name="seq"),
        CheckConstraint("payer_id <> payee_id", name="two_people"),
        CheckConstraint("amount > 0", name="amount"),
        CheckConstraint(asset_check("currency"), name="currency"),
        CheckConstraint(country_check("country"), name="country"),
        CheckConstraint(one_of("method", PaymentKind), name="method"),
        CheckConstraint("received_at IS NULL OR sent_at IS NOT NULL", name="sent_first"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # The unique (deal_id, seq) index covers deal_id.
    deal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(SmallInteger)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    payee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(8))
    country: Mapped[str] = mapped_column(CHAR(2))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    # How the payer pays: an order's payout way for its own currency, the proposer's
    # word for the other.
    method: Mapped[str] = mapped_column(Text)
    # A copy of the payee's chosen payment details, sealed for this row (ADR-0004,
    # ADR-0010). The title stays in the clear, for lists and bot messages.
    recipient_title: Mapped[str | None] = mapped_column(Text)
    recipient_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    due_date: Mapped[date] = mapped_column(Date)
    sent_at: Mapped[datetime | None]
    received_at: Mapped[datetime | None]


class Event(Base):
    """The deal journal (§5, ADR-0002): append-only, with a total order.

    A trigger refuses UPDATE and DELETE.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    deal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deals.id"), index=True)
    # Null for the system: an expiry.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(Text)
    # At least {"from": status, "to": status}, which the deals trigger checks.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
