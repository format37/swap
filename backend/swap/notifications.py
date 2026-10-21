"""Notifications: written with the change they report, worded and sent by the worker (ADR-0014)."""

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from swap.models import Notification

# Each type is also the key of its words in swap/i18n.py.
type NotificationType = Literal[
    "link.requested",
    "link.established",
    "order.opened",
    "deal.proposed",
    "deal.accepted",
    "deal.declined",
    "deal.withdrawn",
    "deal.expired",
    "deal.cancelled",
    "deal.proposal_closed",
    "deal.sent",
    "deal.received",
    "deal.settled",
]


def notify(
    db: AsyncSession,
    recipient: uuid.UUID,
    type_: NotificationType,
    *,
    target: str | None = None,
    **params: str,
) -> None:
    """Queue a message in the caller's transaction, so it goes out only if the change commits.

    A value whose name holds `amount` is a decimal string, which the worker formats in the
    recipient's language.
    """
    db.add(
        Notification(
            id=uuid.uuid4(), recipient_id=recipient, type=type_, params=params, target=target
        )
    )
