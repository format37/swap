"""Tables. The conventions are ADR-0002: plural snake_case, uuid keys, timestamptz."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    Text,
    false,
    func,
)
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
