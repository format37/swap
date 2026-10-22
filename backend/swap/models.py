"""Tables. The conventions are ADR-0002: plural snake_case, uuid keys, timestamptz."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

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
    case,
    false,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column, relationship

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


class NotificationKind(StrEnum):
    """The kinds of messages a person can switch off one by one (QUESTIONS K1)."""

    ORDERS = "orders"
    LINKS = "links"
    PROPOSALS = "proposals"
    TRANSFERS = "transfers"
    CANCELLATIONS = "cancellations"


def _kinds_of_notifications_check(column: str) -> str:
    listed = ", ".join(f"'{kind}'" for kind in NotificationKind)
    return f"{column} <@ ARRAY[{listed}]::text[]"


class User(Base):
    """Someone who has opened the app or pressed /start (Q-B11)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_kinds_of_notifications_check("muted_kinds"), name="muted_kinds"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # None once they deleted their account: the row stays as «Удалённый участник» for the
    # deals others keep, and the same Telegram account starts afresh (Q-B10).
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
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
    # Their Telegram photo, as a link Telegram serves: taken from initData at every
    # sign-in, never copied (QUESTIONS J4, ADR-0027).
    photo_url: Mapped[str | None] = mapped_column(Text)
    # «Все уведомления» switched off: the bot sends them nothing (QUESTIONS K1).
    notifications_off: Mapped[bool] = mapped_column(default=False, server_default=false())
    # The kinds they switched off one by one (NotificationKind).
    muted_kinds: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'::text[]")
    )
    # They deleted their account (QUESTIONS K2): everything about them is scrubbed.
    deleted_at: Mapped[datetime | None]
    # The version of the agreement they accepted, and when (Q-B15, QUESTIONS K3).
    terms_version: Mapped[int | None] = mapped_column(SmallInteger)
    terms_accepted_at: Mapped[datetime | None]
    if TYPE_CHECKING:
        # How many different people they settled a deal with: counted, and mapped below,
        # once deals are (ADR-0029).
        score: Mapped[int]
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


class Mute(Base):
    """`user_id` hears nothing of `muted_id`'s new orders (FR-7.2, QUESTIONS K1)."""

    __tablename__ = "mutes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    muted_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


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
    a deal's legs. Three, as the owner put it: «нал, банк или крипта» (QUESTIONS G3,
    ADR-0021). A card or a phone transfer is «bank»."""

    CASH = "cash"
    BANK = "bank"
    CRYPTO = "crypto"


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

    Who sees it is a query over chains of active links (ADR-0028): the author always;
    anyone else only while it is open, and within its reach.
    """

    __tablename__ = "orders"
    # The number comes from the database: read it back with the INSERT.
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012
    __table_args__ = (
        CheckConstraint(asset_check("give_currency"), name="give_currency"),
        CheckConstraint(country_check("give_country"), name="give_country"),
        CheckConstraint("amount_min >= 0 AND amount_min <= amount_max", name="amounts"),
        CheckConstraint(
            "amount_remaining >= 0 AND amount_remaining <= amount_max", name="remaining"
        ),
        # Holds when there is no last day too: a comparison with NULL passes a CHECK.
        CheckConstraint("available_from <= available_until", name="window"),
        CheckConstraint(_kinds_check("payout_methods"), name="payout_methods"),
        CheckConstraint(_kinds_check("receive_methods"), name="receive_methods"),
        CheckConstraint(one_of("status", OrderStatus), name="status"),
        CheckConstraint("reach IS NULL OR reach BETWEEN 0 AND 3", name="reach"),
        # What feeds and the expiry sweep look for (ADR-0002).
        Index("ix_orders_open_until", "available_until", postgresql_where=text("status = 'open'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # «№ 17», from one sequence for all orders, so people can name one (QUESTIONS K8).
    number: Mapped[int] = mapped_column(
        BigInteger, unique=True, server_default=text("nextval('order_numbers')")
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    give_currency: Mapped[str] = mapped_column(String(8))
    give_country: Mapped[str] = mapped_column(CHAR(2))
    # The smallest single deal, 0 for any amount, and all there is (Q-B5, QUESTIONS F4).
    amount_min: Mapped[Decimal] = mapped_column(MONEY)
    amount_max: Mapped[Decimal] = mapped_column(MONEY)
    # Shrinks when a deal is accepted, and grows back when one is cancelled (FR-2.3).
    amount_remaining: Mapped[Decimal] = mapped_column(MONEY)
    available_from: Mapped[date]
    # None: open until its author closes it (QUESTIONS F3).
    available_until: Mapped[date | None]
    # How the author pays out, and how they can be paid (QUESTIONS F2).
    payout_methods: Mapped[list[str]] = mapped_column(ARRAY(Text))
    receive_methods: Mapped[list[str]] = mapped_column(ARRAY(Text))
    note: Mapped[str | None] = mapped_column(Text)
    # How many handshakes away it is seen (QUESTIONS J2, ADR-0028): 0 for its list alone,
    # 1 for the author's links, 2 and 3 further, None for anyone any chain reaches.
    reach: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(Text, server_default=OrderStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    # Its author deleted it, with all its deals, for themselves (QUESTIONS J3, ADR-0030).
    # Whoever dealt on it keeps it. The row goes once none of its deals remain.
    deleted_at: Mapped[datetime | None]

    wants: Mapped[list["OrderWant"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderWant.position"
    )


class OrderWant(Base):
    """One currency the author would take, where, and at what rate (ADR-0002: rows, not
    JSON; ADR-0026: a rate for each)."""

    __tablename__ = "order_wants"
    __table_args__ = (
        CheckConstraint(asset_check("currency"), name="currency"),
        CheckConstraint(country_check("country"), name="country"),
        CheckConstraint("rate_spec->>'type' IN ('fixed', 'reference')", name="rate_spec_type"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    currency: Mapped[str] = mapped_column(String(8), primary_key=True)
    country: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    # The author's order of preference: «GEL, or else USD».
    position: Mapped[int] = mapped_column(server_default=text("0"))
    # This currency's rate: the author's own, or the market's until a proposal locks it
    # (QUESTIONS J1). A versioned union, validated by swap/rates.py (ADR-0004).
    rate_spec: Mapped[dict[str, Any]] = mapped_column(JSONB)


class OrderVisibility(Base):
    """Who may see an order of reach 0, «Только выбранным»: the author's links they picked
    (ADR-0028). Other orders have no rows."""

    __tablename__ = "order_visibility"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class DealStatus(StrEnum):
    """Three states a deal moves through, and three it ends in. Its two transfers move on
    their own while it is accepted, in any order (QUESTIONS H2, ADR-0024)."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
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
    # Where a market rate came from, and when it said so; None for the author's own
    # (FR-3.5, QUESTIONS G2).
    rate_source: Mapped[str | None] = mapped_column(Text)
    rate_fetched_at: Mapped[datetime | None]
    # A proposal lapses at this moment (FR-4.4).
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    # A pending request to cancel after the first «Отправлено» is a field, not a state (Q-B1).
    cancel_requested_by: Mapped[uuid.UUID | None]
    disputed_by: Mapped[uuid.UUID | None]
    dispute_note: Mapped[str | None] = mapped_column(Text)
    # The proposer's word on the rest, such as which bank (QUESTIONS G3).
    note: Mapped[str | None] = mapped_column(Text)
    # A dispute ends when one side proposes an outcome and the other confirms it (FR-4.6).
    resolution: Mapped[str | None] = mapped_column(Text)
    resolution_by: Mapped[uuid.UUID | None]
    # The event that recorded the latest change; the trigger checks it.
    last_event_id: Mapped[int | None] = mapped_column(BigInteger)
    # Its proposer deleted it for themselves (QUESTIONS J3). The author's deletion is the
    # order's. Once both have, the deal is erased (ADR-0030).
    proposer_deleted_at: Mapped[datetime | None]
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
    # Deals made since QUESTIONS H1 have none: the parties settle when among themselves.
    due_date: Mapped[date | None] = mapped_column(Date)
    sent_at: Mapped[datetime | None]
    received_at: Mapped[datetime | None]


class Event(Base):
    """The deal journal (§5, ADR-0002): append-only, with a total order.

    A trigger refuses UPDATE, and DELETE but for a deal being erased whole (ADR-0030).
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Goes with its deal, the one way a line may go (ADR-0030).
    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), index=True
    )
    # Null for the system: an expiry.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(Text)
    # At least {"from": status, "to": status}, which the deals trigger checks.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# A person's score: how many different people they have a settled deal with (QUESTIONS J5,
# ADR-0029). Counted by the database whenever a user is loaded, never stored, so a deal
# erased by both sides takes its point with it.
_counterpart = case((Deal.proposer_id == User.id, Deal.acceptor_id), else_=Deal.proposer_id)
User.score = column_property(
    select(func.count(func.distinct(_counterpart)))
    .where(
        Deal.status == DealStatus.SETTLED,
        or_(Deal.proposer_id == User.id, Deal.acceptor_id == User.id),
    )
    .correlate_except(Deal)
    .scalar_subquery(),
    # Kept through a flush of the user's own columns: they can't change it, and reading it
    # again would be IO where async allows none.
    expire_on_flush=False,
)
