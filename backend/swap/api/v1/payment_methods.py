"""Saved payment details (ADR-0010): their owner lists, adds and deletes them."""

import uuid
from datetime import datetime
from typing import Self

from fastapi import APIRouter, Request
from pydantic import BaseModel

from swap import payment_methods
from swap.api.deps import AppSettings, CurrentUser, Db
from swap.api.errors import Problem
from swap.crypto import Keys
from swap.models import PaymentKind
from swap.models import PaymentMethod as PaymentMethodRow
from swap.payment_methods import NewPaymentMethod

router = APIRouter(
    prefix="/payment-methods", tags=["payment details"], responses={401: {"model": Problem}}
)


class SealedText(BaseModel):
    """Payment details as the api shows them: the mask to all, the text to those Q-B8 allows."""

    masked: str
    full: str | None


class PaymentMethod(BaseModel):
    id: uuid.UUID
    asset: str
    kind: PaymentKind
    title: str
    # Null when there is no text, as for cash.
    details: SealedText | None
    created_at: datetime

    @classmethod
    def of_mine(cls, method: PaymentMethodRow, keys: Keys | None) -> Self:
        """For its owner, who may always read their own (Q-B8)."""
        full = payment_methods.reveal(method, keys)
        details = (
            SealedText(
                masked=str(method.details["mask"]),
                full=full.get_secret_value() if full else None,
            )
            if method.details
            else None
        )
        return cls(
            id=method.id,
            asset=method.asset,
            kind=PaymentKind(method.kind),
            title=method.title,
            details=details,
            created_at=method.created_at,
        )


def _keys(request: Request) -> Keys | None:
    keys: Keys | None = request.app.state.keys
    return keys


@router.get("")
async def list_payment_methods(request: Request, user: CurrentUser, db: Db) -> list[PaymentMethod]:
    keys = _keys(request)
    return [
        PaymentMethod.of_mine(method, keys) for method in await payment_methods.mine(db, user.id)
    ]


@router.post(
    "",
    status_code=201,
    responses={422: {"model": Problem}, 429: {"model": Problem}, 503: {"model": Problem}},
)
async def add_payment_method(
    body: NewPaymentMethod, request: Request, user: CurrentUser, db: Db, settings: AppSettings
) -> PaymentMethod:
    keys = _keys(request)
    method = await payment_methods.add(db, user.id, body, keys, settings.assets)
    await db.commit()
    return PaymentMethod.of_mine(method, keys)


@router.delete("/{method_id}", status_code=204, responses={404: {"model": Problem}})
async def delete_payment_method(method_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    await payment_methods.remove(db, user.id, method_id)
    await db.commit()
