"""Saved payment details (ADR-0010): free text per asset, sealed before it is stored, and
seen in full by its owner only (Q-B8). A deal copies what it uses (ADR-0004)."""

import uuid
from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swap.crypto import Keys, payment_method_aad
from swap.errors import DomainError
from swap.models import PaymentKind, PaymentMethod
from swap.money import Asset

# A sanity cap: nobody pays into thirty accounts.
MAX_SAVED = 30
MAX_TEXT = 500
# Whoever pays needs somewhere to send it; cash can do with a note or nothing.
TEXT_REQUIRED = frozenset({PaymentKind.BANK, PaymentKind.CRYPTO})


class NewPaymentMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: Asset
    kind: PaymentKind
    # In the clear, for lists and bot messages: «TBC», «Сбер · СБП», «USDT · TRC20».
    title: str = Field(min_length=1, max_length=60)
    # IBAN or card, holder, bank, network and address, memo: whatever the payer needs.
    text: SecretStr = SecretStr("")

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a title is needed")
        return value.strip()

    @field_validator("text")
    @classmethod
    def short_enough(cls, value: SecretStr) -> SecretStr:
        text = value.get_secret_value().strip()
        if len(text) > MAX_TEXT:
            raise ValueError(f"at most {MAX_TEXT} characters")
        return SecretStr(text)


async def mine(db: AsyncSession, owner: uuid.UUID) -> list[PaymentMethod]:
    return list(
        await db.scalars(
            select(PaymentMethod)
            .where(PaymentMethod.user_id == owner)
            .order_by(PaymentMethod.asset, PaymentMethod.created_at)
        )
    )


async def add(
    db: AsyncSession,
    owner: uuid.UUID,
    new: NewPaymentMethod,
    keys: Keys | None,
    assets: Collection[str],
) -> PaymentMethod:
    if keys is None:
        raise DomainError(503, "payment.unavailable")
    if new.asset not in assets:
        raise DomainError(422, "payment.unknown_asset")
    text = new.text.get_secret_value()
    if not text and new.kind in TEXT_REQUIRED:
        raise DomainError(422, "payment.text_required")
    saved = await db.scalar(
        select(func.count()).select_from(PaymentMethod).where(PaymentMethod.user_id == owner)
    )
    if (saved or 0) >= MAX_SAVED:
        raise DomainError(429, "payment.limit")
    method = PaymentMethod(
        id=uuid.uuid4(), user_id=owner, asset=new.asset, kind=new.kind, title=new.title
    )
    if text:
        method.details = keys.seal(new.text, payment_method_aad(method.id))
    db.add(method)
    await db.flush()
    return method


async def remove(db: AsyncSession, owner: uuid.UUID, method_id: uuid.UUID) -> None:
    """A real delete: deals keep their own copies (ADR-0010)."""
    method = await db.scalar(
        select(PaymentMethod).where(PaymentMethod.id == method_id, PaymentMethod.user_id == owner)
    )
    if method is None:
        raise DomainError(404, "payment.not_found")
    await db.delete(method)


def reveal(method: PaymentMethod, keys: Keys | None) -> SecretStr | None:
    """The text in full, for its owner. None without text, or without the keys to open it."""
    if method.details is None or keys is None:
        return None
    return keys.unseal(method.details, payment_method_aad(method.id))
